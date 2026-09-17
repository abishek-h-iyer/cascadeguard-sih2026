// Client-side store backed by the real CascadeGuard API instead of an
// in-browser simulation. Keeps the same subscribe/getSnapshot shape the old
// mockStore had so App.jsx and useDashboardStore don't need to change their
// interaction pattern â€” only where the data comes from changes.
import {
  getHealth,
  getZones,
  getEvents,
  resetDemo,
  setZoneOverride,
  clearZoneOverride,
} from './api'
import { predict, updateFromObservation } from '../utils/etaEngine'
import { zoneNumber } from '../data/zoneStaticData'

const STATUS_RANK = { SAFE: 0, WATCH: 1, CRITICAL: 2 }
const OVERRIDE_DEBOUNCE_MS = 150
const DOWNSTREAM_SURGE_THRESHOLD = 0.6
const LOCAL_EVENTS_CAP = 60
const MERGED_EVENTS_CAP = 100
const EARLY_WARNING_REACH = 3

// The backend gateway (packet_gateway.py) already produces `eta` /
// `eta_observation` when hardware packets flow through /ingest, but the
// dashboard's live simulation loop (backend/main.py) evaluates the risk
// engine directly and never calls the ETA engine â€” so nothing reaches this
// dashboard today. Rather than touch backend files, we watch for the exact
// same two triggers the real gateway uses and run the same physics (ported
// in utils/etaEngine.js) client-side. This is a mock in the sense that the
// computation runs in the browser, but the math, thresholds and inputs are
// identical to the backend's â€” swapping to a real `/eta` endpoint later just
// means replacing this derivation with the response's `eta`/`eta_observation`
// fields instead of computing them here.

let localEventSeq = 0
function makeLocalEvent(message, timestampMs) {
  localEventSeq += 1
  return { id: `eta-${Math.trunc(timestampMs)}-${localEventSeq}`, timestamp: timestampMs, message }
}

function mergeEvents(backendEvents, localEvents) {
  return [...backendEvents, ...localEvents]
    .sort((a, b) => b.timestamp - a.timestamp)
    .slice(0, MERGED_EVENTS_CAP)
}

// Mirrors PacketGateway.find_active_source: the nearest active upstream
// surge event that hasn't already observed this zone. Only real SURGE
// events get recalibrated by a sensor observation â€” a WATCH-triggered
// preliminary estimate has nothing confirmed to calibrate against.
function findActiveSource(etaEvents, observedZoneId) {
  const observedNumber = zoneNumber(observedZoneId)
  let best = null
  for (const event of Object.values(etaEvents)) {
    if (event.kind !== 'SURGE') continue
    const sourceNumber = zoneNumber(event.sourceZone)
    if (sourceNumber < observedNumber && !event.observations[observedZoneId]) {
      if (!best || sourceNumber > zoneNumber(best)) best = event.sourceZone
    }
  }
  return best
}

// Detects the same two triggers backend/packet_gateway.py acts on
// (cascade.possible_surge turning true, and a downstream_rise reading
// crossing the surge threshold) and advances the local ETA event state.
function advanceEta(prevZonesById, nextZonesById, prevEtaEvents, nowMs) {
  // On the very first snapshot there's nothing to diff against yet, so a
  // missing previous reading reads as "was safe/not watch" and every zone
  // already in a non-safe state (e.g. MEL_Z03's demo seed, which starts
  // mid-blockage on purpose) looks like it "just transitioned" right now.
  // That's fine, even desirable, for the SURGE and WATCH loops below â€” a
  // freshly connected dashboard treating current conditions as its starting
  // point is reasonable, and it's what makes a fresh reset immediately
  // demoable instead of requiring a throwaway Normal->Blockage cycle first.
  // It's only dangerous for the observation loop further down: if a source
  // zone AND an already-past-threshold downstream zone both "transition" on
  // this same first tick, their timestamps collide and
  // updateFromObservation throws (observed time must be after source time).
  // So only that loop gets skipped on the first snapshot.
  const isFirstSnapshot = Object.keys(prevZonesById).length === 0

  let etaEvents = prevEtaEvents
  const newLocalEvents = []

  for (const zoneId of Object.keys(nextZonesById)) {
    const zone = nextZonesById[zoneId]
    const wasSurging = prevZonesById[zoneId]?.cascade?.possible_surge
    const isSurging = zone.cascade.possible_surge

    if (isSurging && !wasSurging) {
      // A fresh false->true edge always starts a new event, overwriting any
      // stale one for this source zone â€” e.g. the zone was cycled back to
      // Normal and surged again in the same browser tab. Without this, a
      // second surge on the same zone would silently reuse (and never
      // update) whatever event fired the first time.
      const predictions = predict(zoneId, nowMs, 4)
      etaEvents = {
        ...etaEvents,
        [zoneId]: { kind: 'SURGE', sourceZone: zoneId, sourceTimeMs: nowMs, predictions, observations: {} },
      }
      newLocalEvents.push(makeLocalEvent(`Surge detected at ${zoneId} â€” ETA engine activated`, nowMs))
      if (predictions.length) {
        const first = predictions[0]
        newLocalEvents.push(makeLocalEvent(
          `Initial ETA generated: ${first.zone_id} in ${first.travel_time_min_minutes}â€“${first.travel_time_max_minutes} min (physics-informed)`,
          nowMs,
        ))
      }
    } else if (!isSurging && wasSurging && etaEvents[zoneId]?.kind === 'SURGE') {
      // The condition that started this event is no longer active (e.g. the
      // zone was dialed back to Normal) â€” retract the in-flight forecast
      // rather than leaving a stale arrival window on screen forever.
      const { [zoneId]: _removed, ...rest } = etaEvents
      etaEvents = rest
      newLocalEvents.push(makeLocalEvent(`ETA forecast cleared for ${zoneId} â€” surge conditions resolved`, nowMs))
    }
  }

  for (const zoneId of Object.keys(nextZonesById)) {
    if (isFirstSnapshot) break

    const rise = nextZonesById[zoneId].sensors.downstream_rise_m_10m
    const prevRise = prevZonesById[zoneId]?.sensors?.downstream_rise_m_10m ?? 0
    const crossedThreshold = rise >= DOWNSTREAM_SURGE_THRESHOLD && prevRise < DOWNSTREAM_SURGE_THRESHOLD
    if (!crossedThreshold) continue

    const sourceZone = findActiveSource(etaEvents, zoneId)
    if (!sourceZone) continue

    const event = etaEvents[sourceZone]

    let observation
    let predictions
    try {
      ;({ observation, predictions } = updateFromObservation(sourceZone, zoneId, event.sourceTimeMs, nowMs, 4))
    } catch (error) {
      // Physically impossible observation (e.g. clock skew) â€” skip this
      // zone rather than aborting the whole poll cycle.
      console.error(`ETA observation skipped for ${zoneId}:`, error.message)
      continue
    }

    etaEvents = {
      ...etaEvents,
      [sourceZone]: {
        ...event,
        predictions,
        observations: { ...event.observations, [zoneId]: { observedTimeMs: nowMs, observation } },
      },
    }

    newLocalEvents.push(makeLocalEvent(
      `Wave observed at ${zoneId} â€” ETA recalibrated (observed ${observation.observed_celerity_m_s} m/s)`,
      nowMs,
    ))
  }

  return { etaEvents, newLocalEvents }
}

function pickHighestRiskZone(zones) {
  let best = null
  for (const zone of Object.values(zones)) {
    if (!best || STATUS_RANK[zone.operational_status] > STATUS_RANK[best.operational_status]) {
      best = zone
    }
  }
  return best ? best.zone_id : null
}

function zonesById(zoneList) {
  const zones = {}
  for (const zone of zoneList) zones[zone.zone_id] = zone
  return zones
}

function createStore() {
  let state = {
    zones: {},
    events: [],
    backendEvents: [],
    etaEvents: {},
    localEvents: [],
    connection: { systemOnline: false, gatewayConnected: false, lastSensorUpdate: Date.now() },
    riskViewMode: 'LIVE',
    selectedZoneId: null,
  }

  const listeners = new Set()
  const overrideTimers = {}

  function notify() {
    for (const fn of listeners) fn()
  }

  // The single funnel every zone mutation goes through (poll refresh, an
  // optimistic slider drag, or a confirmed override) so advanceEta always
  // diffs against the state that actually existed a moment ago. Applying
  // partial zone updates straight into `state.zones` without going through
  // here would let a threshold crossing (e.g. downstream_rise_m_10m jumping
  // past 0.6 in one optimistic update) happen "between" comparisons and
  // never get detected.
  function applyZoneUpdates(partialZonesById, nowMs) {
    const prevZonesById = state.zones
    const nextZonesById = { ...prevZonesById, ...partialZonesById }

    const { etaEvents, newLocalEvents } = advanceEta(prevZonesById, nextZonesById, state.etaEvents, nowMs)
    const localEvents = newLocalEvents.length
      ? [...newLocalEvents, ...state.localEvents].slice(0, LOCAL_EVENTS_CAP)
      : state.localEvents

    state = {
      ...state,
      zones: nextZonesById,
      etaEvents,
      localEvents,
      events: mergeEvents(state.backendEvents, localEvents),
    }
  }

  async function refresh() {
    try {
      const [health, zoneList, backendEvents] = await Promise.all([getHealth(), getZones(), getEvents()])
      const nowMs = Date.now()

      state = { ...state, backendEvents }
      applyZoneUpdates(zonesById(zoneList), nowMs)
      state = {
        ...state,
        connection: health,
        selectedZoneId: state.selectedZoneId || pickHighestRiskZone(state.zones),
      }
    } catch (error) {
      state = {
        ...state,
        connection: { ...state.connection, systemOnline: false, gatewayConnected: false },
      }
      console.error('CascadeGuard API unreachable:', error.message)
    }
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

    setSensorOverride(zoneId, partial) {
      // Merge optimistically so sliders feel responsive while the debounced
      // request is in flight. Goes through applyZoneUpdates (not a direct
      // state.zones write) so a slider drag that jumps a sensor straight
      // past an ETA threshold is still detected.
      const current = state.zones[zoneId]
      if (current) {
        const optimisticZone = { ...current, sensors: { ...current.sensors, ...partial }, overridden: true }
        applyZoneUpdates({ [zoneId]: optimisticZone }, Date.now())
        notify()
      }

      clearTimeout(overrideTimers[zoneId])
      overrideTimers[zoneId] = setTimeout(async () => {
        try {
          const { zone } = await setZoneOverride(zoneId, partial)
          applyZoneUpdates({ [zoneId]: zone }, Date.now())
          notify()
        } catch (error) {
          console.error(`Failed to override ${zoneId}:`, error.message)
        }
      }, OVERRIDE_DEBOUNCE_MS)
    },

    async clearOverride(zoneId) {
      try {
        const { zone } = await clearZoneOverride(zoneId)
        applyZoneUpdates({ [zoneId]: zone }, Date.now())
        notify()
      } catch (error) {
        console.error(`Failed to clear override for ${zoneId}:`, error.message)
      }
    },

    async reset() {
      await resetDemo().catch((error) => console.error('Failed to reset demo:', error.message))
      state = { ...state, selectedZoneId: null, etaEvents: {}, localEvents: [] }
      await refresh()
    },

    startTicking(intervalMs = 3500) {
      refresh()
      const id = setInterval(refresh, intervalMs)
      return () => clearInterval(id)
    },
  }
}

export const dashboardStore = createStore()

