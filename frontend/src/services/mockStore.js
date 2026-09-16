// In-memory mock "backend" for the dashboard. Mirrors the shape a real
// FastAPI service (wrapping backend/risk_engine.py + gateway/packet_gateway.py)
// would produce, so src/services/api.js can later swap this out for real
// fetch calls without any component needing to change.
import { ZONE_IDS, ZONE_STATIC } from '../data/zoneStaticData'
import { evaluateZone, DEMO_SCENARIOS } from '../utils/riskEngine'

const STATUS_RANK = { SAFE: 0, WATCH: 1, CRITICAL: 2 }
const maxStatus = (a, b) => (STATUS_RANK[b] > STATUS_RANK[a] ? b : a)
const warningToStatus = (warning) => (warning === 'CRITICAL' ? 'CRITICAL' : 'WATCH')

function jitter(range) {
  return (Math.random() - 0.5) * range
}

function baselineSensors(susceptibilityClass) {
  const base = susceptibilityClass === 'HIGH'
    ? { rainfall_mm_h: 4, soil_moisture: 0.42, tilt_change_deg: 0.15, upstream_rise_m_10m: 0.08, downstream_rise_m_10m: 0.05 }
    : susceptibilityClass === 'MODERATE'
      ? { rainfall_mm_h: 3, soil_moisture: 0.35, tilt_change_deg: 0.10, upstream_rise_m_10m: 0.06, downstream_rise_m_10m: 0.04 }
      : { rainfall_mm_h: 2, soil_moisture: 0.30, tilt_change_deg: 0.08, upstream_rise_m_10m: 0.04, downstream_rise_m_10m: 0.03 }
  return {
    rainfall_mm_h: Math.max(0, round2(base.rainfall_mm_h + jitter(1.5))),
    soil_moisture: clamp(round2(base.soil_moisture + jitter(0.04)), 0, 1),
    tilt_change_deg: Math.max(0, round2(base.tilt_change_deg + jitter(0.04))),
    upstream_rise_m_10m: Math.max(0, round2(base.upstream_rise_m_10m + jitter(0.02))),
    downstream_rise_m_10m: Math.max(0, round2(base.downstream_rise_m_10m + jitter(0.02))),
  }
}

function round2(n) { return Math.round(n * 100) / 100 }
function clamp(n, lo, hi) { return Math.min(hi, Math.max(lo, n)) }

function jitterExisting(sensors) {
  return {
    rainfall_mm_h: Math.max(0, round2(sensors.rainfall_mm_h + jitter(0.6))),
    soil_moisture: clamp(round2(sensors.soil_moisture + jitter(0.01)), 0, 1),
    tilt_change_deg: Math.max(0, round2(sensors.tilt_change_deg + jitter(0.02))),
    upstream_rise_m_10m: Math.max(0, round2(sensors.upstream_rise_m_10m + jitter(0.01))),
    downstream_rise_m_10m: Math.max(0, round2(sensors.downstream_rise_m_10m + jitter(0.01))),
  }
}

const SENSOR_NODES = [
  { node: 'RAIN', field: 'rainfall_mm_h', unit: 'mm/h' },
  { node: 'SOIL', field: 'soil_moisture', unit: '' },
  { node: 'TILT', field: 'tilt_change_deg', unit: '°' },
  { node: 'UP_RISE', field: 'upstream_rise_m_10m', unit: 'm/10min' },
  { node: 'DOWN_RISE', field: 'downstream_rise_m_10m', unit: 'm/10min' },
]

function seedEvents(now) {
  const offsets = [-95, -80, -62, -48, -31, -18]
  const messages = [
    'MEL_Z03 rainfall entered HIGH range',
    'Soil saturation detected at MEL_Z03',
    'Abnormal slope movement detected at MEL_Z03',
    'Possible landslide detected at MEL_Z03',
    'Possible river blockage detected at MEL_Z03',
    'MEL_Z04–Z06 placed on WATCH',
  ]
  return messages.map((message, i) => ({
    id: `seed-${i}`,
    timestamp: now + offsets[i] * 1000,
    message,
  }))
}

function createStore() {
  const now = Date.now()

  const raw = {}
  const previousBlockage = {}
  const overridden = {}
  const sequences = {}

  for (const zoneId of ZONE_IDS) {
    raw[zoneId] = zoneId === 'MEL_Z03'
      ? { ...DEMO_SCENARIOS.BLOCKAGE }
      : baselineSensors(ZONE_STATIC[zoneId].susceptibilityClass)
    previousBlockage[zoneId] = false
    overridden[zoneId] = false
    sequences[zoneId] = 0
  }

  let state = {
    zones: {},
    events: seedEvents(now),
    connection: { systemOnline: true, gatewayConnected: true, lastSensorUpdate: now },
    riskViewMode: 'LIVE',
    selectedZoneId: null,
  }

  const listeners = new Set()

  function notify() {
    for (const fn of listeners) fn()
  }

  function pushEvent(message, timestamp) {
    state.events = [{ id: `${timestamp}-${Math.random().toString(36).slice(2, 8)}`, timestamp, message }, ...state.events].slice(0, 80)
  }

  function computeAll(timestamp) {
    const results = {}
    for (const zoneId of ZONE_IDS) {
      const result = evaluateZone(zoneId, raw[zoneId], previousBlockage[zoneId])
      if (result.cascade.possible_blockage) previousBlockage[zoneId] = true
      results[zoneId] = result
    }

    const incoming = {}
    for (const zoneId of ZONE_IDS) {
      for (const warning of results[zoneId].downstream_warnings) {
        const status = warningToStatus(warning.warning)
        const existing = incoming[warning.zone_id]
        if (!existing || STATUS_RANK[status] > STATUS_RANK[existing.status]) {
          incoming[warning.zone_id] = { status, reason: warning.reason, fromZone: zoneId, warningLevel: warning.warning }
        }
      }
    }

    const previousZones = state.zones
    const nextZones = {}

    for (const zoneId of ZONE_IDS) {
      const result = results[zoneId]
      const incomingWarning = incoming[zoneId] || null
      const finalStatus = maxStatus(result.operational_status, incomingWarning ? incomingWarning.status : 'SAFE')

      const sensorNodes = SENSOR_NODES.map(({ node, field, unit }) => ({
        node: `${node}_${zoneId.slice(-2)}`,
        type: node,
        value: raw[zoneId][field],
        unit,
        online: true,
        sequence: sequences[zoneId],
        crcValid: true,
      }))

      nextZones[zoneId] = {
        ...result,
        operational_status: finalStatus,
        incoming_warning: incomingWarning,
        overridden: overridden[zoneId],
        sensor_nodes: sensorNodes,
        last_updated: timestamp,
      }

      const prev = previousZones[zoneId]
      if (prev) {
        if (prev.operational_status !== finalStatus) {
          pushEvent(`${zoneId} status changed to ${finalStatus}`, timestamp)
        }
        if (!prev.cascade.possible_landslide && result.cascade.possible_landslide) {
          pushEvent(`Possible landslide detected at ${zoneId}`, timestamp)
        }
        if (!prev.cascade.possible_blockage && result.cascade.possible_blockage) {
          pushEvent(`Possible river blockage detected at ${zoneId}`, timestamp)
        }
        if (!prev.cascade.possible_surge && result.cascade.possible_surge) {
          pushEvent(`Downstream surge detected — propagating from ${zoneId}`, timestamp)
        }
        if (!prev.incoming_warning && incomingWarning) {
          pushEvent(`${zoneId} placed on ${incomingWarning.status} (${incomingWarning.reason})`, timestamp)
        }
      }
    }

    // Replace `state` with a new object (never mutate the previous one in
    // place) so useSyncExternalStore's Object.is check sees a change and
    // React actually re-renders.
    state = {
      ...state,
      zones: nextZones,
      connection: { ...state.connection, lastSensorUpdate: timestamp },
      selectedZoneId: state.selectedZoneId || pickHighestRiskZone(nextZones),
    }
  }

  function pickHighestRiskZone(zones) {
    let best = ZONE_IDS[0]
    for (const zoneId of ZONE_IDS) {
      if (STATUS_RANK[zones[zoneId].operational_status] > STATUS_RANK[zones[best].operational_status]) {
        best = zoneId
      }
    }
    return best
  }

  computeAll(now)

  function tick() {
    const timestamp = Date.now()
    for (const zoneId of ZONE_IDS) {
      if (!overridden[zoneId]) {
        raw[zoneId] = jitterExisting(raw[zoneId])
        sequences[zoneId] = (sequences[zoneId] + 1) % 256
      }
    }
    computeAll(timestamp)
    notify()
  }

  return {
    subscribe(fn) {
      listeners.add(fn)
      return () => listeners.delete(fn)
    },
    getSnapshot() {
      return state
    },
    selectZone(zoneId) {
      state = { ...state, selectedZoneId: zoneId }
      notify()
    },
    setRiskViewMode(mode) {
      state = { ...state, riskViewMode: mode }
      notify()
    },
    setSensorOverride(zoneId, sensors) {
      overridden[zoneId] = true
      raw[zoneId] = { ...raw[zoneId], ...sensors }
      sequences[zoneId] = (sequences[zoneId] + 1) % 256
      computeAll(Date.now())
      notify()
    },
    clearOverride(zoneId) {
      overridden[zoneId] = false
      computeAll(Date.now())
      notify()
    },
    isOverridden(zoneId) {
      return overridden[zoneId]
    },
    getRawSensors(zoneId) {
      return raw[zoneId]
    },
    startTicking(intervalMs = 3500) {
      const id = setInterval(tick, intervalMs)
      return () => clearInterval(id)
    },
    reset() {
      for (const zoneId of ZONE_IDS) {
        raw[zoneId] = zoneId === 'MEL_Z03'
          ? { ...DEMO_SCENARIOS.BLOCKAGE }
          : baselineSensors(ZONE_STATIC[zoneId].susceptibilityClass)
        previousBlockage[zoneId] = false
        overridden[zoneId] = false
      }
      state = {
        zones: {},
        events: seedEvents(Date.now()),
        connection: { systemOnline: true, gatewayConnected: true, lastSensorUpdate: Date.now() },
        riskViewMode: 'LIVE',
        selectedZoneId: null,
      }
      computeAll(Date.now())
      notify()
    },
  }
}

export const mockStore = createStore()
