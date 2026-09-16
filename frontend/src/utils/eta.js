// Pure selectors/formatters over dashboardStore's `etaEvents` state, kept
// separate from the store the same way riskMapping.js/stats.js are kept
// separate from dashboardStore — components read through here instead of
// reaching into event internals directly.

export const FORECAST_BASIS = {
  PHYSICS_INITIAL: {
    badge: 'INITIAL ETA',
    sub: 'Physics-Informed',
    basisLine: 'GIS + Hydraulic Model',
  },
  SENSOR_CALIBRATED: {
    badge: 'UPDATED ETA',
    sub: 'Sensor-Calibrated',
    basisLine: 'Observed Sensor + Hydraulic Model',
  },
}

/**
 * Resolve what (if anything) an individual zone should show for ETA:
 * - ARRIVED: a sensor already observed the wave at this zone
 * - FORECAST: this zone has a live upstream-derived arrival window
 * - SOURCE: this zone is where an active surge event originated
 * - null: no active ETA event touches this zone
 */
export function getZoneEtaInfo(etaEvents, zoneId) {
  const asSource = etaEvents[zoneId]
  if (asSource) {
    return { type: 'SOURCE', sourceZone: zoneId, sourceTimeMs: asSource.sourceTimeMs }
  }

  for (const event of Object.values(etaEvents)) {
    const observation = event.observations[zoneId]
    if (observation) {
      return {
        type: 'ARRIVED',
        sourceZone: event.sourceZone,
        sourceTimeMs: event.sourceTimeMs,
        observedTimeMs: observation.observedTimeMs,
        observation: observation.observation,
      }
    }
  }

  for (const event of Object.values(etaEvents)) {
    const prediction = event.predictions.find((p) => p.zone_id === zoneId)
    if (prediction) {
      return {
        type: 'FORECAST',
        sourceZone: event.sourceZone,
        sourceTimeMs: event.sourceTimeMs,
        prediction,
      }
    }
  }

  return null
}

/** Soonest still-pending arrival across every active event, for a top-level summary tile. */
export function getNextArrival(etaEvents, nowMs) {
  let best = null
  for (const event of Object.values(etaEvents)) {
    for (const prediction of event.predictions) {
      if (event.observations[prediction.zone_id]) continue
      if (prediction.eta_max_ms < nowMs) continue
      if (!best || prediction.eta_min_ms < best.prediction.eta_min_ms) {
        best = { sourceZone: event.sourceZone, prediction }
      }
    }
  }
  return best
}

/** Minutes remaining, clamped at zero — never shows a negative countdown. */
export function countdownMinutes(etaMinMs, etaMaxMs, nowMs) {
  const minLeft = Math.max(0, Math.ceil((etaMinMs - nowMs) / 60000))
  const maxLeft = Math.max(0, Math.ceil((etaMaxMs - nowMs) / 60000))
  return { minLeft, maxLeft, arrivingNow: maxLeft === 0 }
}
