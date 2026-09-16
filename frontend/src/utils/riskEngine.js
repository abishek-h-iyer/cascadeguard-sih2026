// Faithful JS port of backend/risk_engine.py thresholds and cascade logic.
// Kept in lockstep with the Python engine so the frontend's demo/simulation
// mode produces exactly the same alert_level/cascade flags the real FastAPI
// backend will return once it is wired in.
import { ZONE_STATIC, downstreamZones } from '../data/zoneStaticData'

export function rainfallState(rainfall) {
  if (rainfall >= 50) return 'SEVERE'
  if (rainfall >= 25) return 'HIGH'
  if (rainfall >= 10) return 'MODERATE'
  return 'LOW'
}

export function soilState(soil) {
  if (soil >= 0.80) return 'SATURATED'
  if (soil >= 0.65) return 'HIGH'
  if (soil >= 0.45) return 'ELEVATED'
  return 'NORMAL'
}

export function tiltState(tilt) {
  if (tilt >= 1.0) return 'ABNORMAL'
  if (tilt >= 0.4) return 'WATCH'
  return 'NORMAL'
}

export function upstreamState(rise) {
  if (rise >= 0.50) return 'RAPID_RISE'
  if (rise >= 0.20) return 'RISING'
  return 'STABLE'
}

export function downstreamState(rise) {
  if (rise >= 0.60) return 'SURGE'
  if (rise >= 0.20) return 'RISING'
  return 'STABLE'
}

const LEVELS = ['LOW', 'MODERATE', 'HIGH', 'CRITICAL']

// alert_level -> operational_status, per the SIH task spec (not in the
// Python engine yet): LOW->SAFE, MODERATE->WATCH, HIGH->WATCH, CRITICAL->CRITICAL
export function operationalStatus(alertLevel) {
  if (alertLevel === 'CRITICAL') return 'CRITICAL'
  if (alertLevel === 'LOW') return 'SAFE'
  return 'WATCH'
}

/**
 * Evaluate one zone's sensor reading against terrain susceptibility and
 * cascade rules. `previousBlockage` is whether this zone has ever tripped
 * blockage_possible before (blockage memory is "sticky" per zone, exactly
 * like RiskEngine.blockage_memory in the Python engine).
 */
export function evaluateZone(zoneId, sensors, previousBlockage) {
  const { rainfall_mm_h: rainfall, soil_moisture: soil, tilt_change_deg: tilt,
    upstream_rise_m_10m: upstreamRise, downstream_rise_m_10m: downstreamRise } = sensors

  const susceptibility = ZONE_STATIC[zoneId]

  const rainState = rainfallState(rainfall)
  const soilSt = soilState(soil)
  const tiltSt = tiltState(tilt)
  const upSt = upstreamState(upstreamRise)
  const downSt = downstreamState(downstreamRise)

  const landslidePossible =
    (tilt >= 1.0 && soil >= 0.65) ||
    (tilt >= 0.70 && rainfall >= 25 && soil >= 0.75)

  const blockagePossible =
    upstreamRise >= 0.50 &&
    downstreamRise <= 0.10 &&
    (landslidePossible || tilt >= 0.70)

  const surgePossible = downstreamRise >= 0.60 && previousBlockage

  let severity = 0
  const reasons = []

  if (rainfall >= 10) { severity = Math.max(severity, 1); reasons.push('Elevated rainfall') }
  if (soil >= 0.65) { severity = Math.max(severity, 1); reasons.push('High soil moisture') }
  if (rainfall >= 25 && soil >= 0.65) { severity = Math.max(severity, 2); reasons.push('Heavy rainfall with wet soil') }
  if (tilt >= 1.0) { severity = Math.max(severity, 2); reasons.push('Abnormal slope movement') }
  if (upstreamRise >= 0.50 && downstreamRise <= 0.10) { severity = Math.max(severity, 2); reasons.push('Upstream-downstream flow anomaly') }
  if (landslidePossible) { severity = Math.max(severity, 2); reasons.push('Possible landslide signature') }

  if (susceptibility.susceptibilityClass === 'HIGH' && severity === 1) {
    severity = 2
    reasons.push('High terrain susceptibility')
  } else if (susceptibility.susceptibilityClass === 'HIGH' && severity >= 2) {
    reasons.push('High terrain susceptibility')
  }

  if (susceptibility.susceptibilityClass === 'MODERATE' && severity >= 1) {
    reasons.push('Moderate terrain susceptibility')
  }

  if (blockagePossible) { severity = 3; reasons.push('Possible river blockage') }
  if (surgePossible) { severity = 3; reasons.push('Possible sudden downstream surge') }

  const alertLevel = LEVELS[severity]

  const downstreamWarnings = []

  if (blockagePossible) {
    for (const zone of downstreamZones(zoneId, 3)) {
      downstreamWarnings.push({ zone_id: zone, warning: 'WATCH', reason: 'Potential downstream surge if blockage releases' })
    }
  }

  if (surgePossible) {
    const warningLevels = ['CRITICAL', 'HIGH', 'HIGH', 'MODERATE']
    downstreamZones(zoneId, 4).forEach((zone, i) => {
      downstreamWarnings.push({ zone_id: zone, warning: warningLevels[i], reason: 'Possible downstream surge propagation' })
    })
  }

  return {
    zone_id: zoneId,
    terrain: {
      susceptibility_score: Number(susceptibility.susceptibilityScore.toFixed(3)),
      susceptibility_class: susceptibility.susceptibilityClass,
    },
    sensors: {
      rainfall_mm_h: rainfall,
      soil_moisture: soil,
      tilt_change_deg: tilt,
      upstream_rise_m_10m: upstreamRise,
      downstream_rise_m_10m: downstreamRise,
    },
    sensor_states: {
      rainfall: rainState,
      soil: soilSt,
      tilt: tiltSt,
      upstream: upSt,
      downstream: downSt,
    },
    cascade: {
      possible_landslide: landslidePossible,
      possible_blockage: blockagePossible,
      possible_surge: surgePossible,
    },
    alert_level: alertLevel,
    operational_status: operationalStatus(alertLevel),
    reasons,
    downstream_warnings: downstreamWarnings,
  }
}

// The 4 documented demo scenarios for MEL_Z03 (task spec section 11),
// reproduced here verbatim so the simulator can offer them as presets while
// still letting the judge free-drag every value.
export const DEMO_SCENARIOS = {
  NORMAL: { rainfall_mm_h: 3, soil_moisture: 0.38, tilt_change_deg: 0.10, upstream_rise_m_10m: 0.05, downstream_rise_m_10m: 0.04 },
  HEAVY_RAIN: { rainfall_mm_h: 32, soil_moisture: 0.73, tilt_change_deg: 0.20, upstream_rise_m_10m: 0.25, downstream_rise_m_10m: 0.22 },
  BLOCKAGE: { rainfall_mm_h: 46, soil_moisture: 0.84, tilt_change_deg: 1.60, upstream_rise_m_10m: 0.82, downstream_rise_m_10m: 0.04 },
  SURGE: { rainfall_mm_h: 28, soil_moisture: 0.82, tilt_change_deg: 0.60, upstream_rise_m_10m: 0.18, downstream_rise_m_10m: 1.05 },
}
