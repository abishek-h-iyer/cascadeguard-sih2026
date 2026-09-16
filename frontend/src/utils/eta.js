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
  // Fires on a broader, earlier signal (an upstream zone merely turning
  // WATCH, not a confirmed surge) so it's deliberately labeled as less
  // certain than the other two — same physics, no confirmed release yet.
  EARLY_WARNING: {
    badge: 'EARLY WARNING',
    sub: 'Preliminary',
    basisLine: 'GIS + Hydraulic Model (upstream zone on watch, not yet confirmed)',
  },
}

/**
 * Resolve what (if anything) an individual zone should show for ETA.
 * `etaEvents` holds two independent kinds keyed by their source zone:
 * SURGE (a confirmed surge — can reach ARRIVED via sensor observation) and
 * WATCH (a zone merely on watch, giving its next few downstream zones a
 * preliminary heads-up). A SURGE match always wins over a WATCH one for the
 * same zone, since it's the more specific, confirmed signal.
 * - ARRIVED: a sensor already observed the wave at this zone
 * - FORECAST: this zone has a live upstream-derived arrival window
 * - SOURCE: this zone is where an active *surge* originated (WATCH-kind
 *   events never render as SOURCE for their own zone — it would misreport
 *   "surge detected" for a zone that's merely on watch)
 * - null: no active ETA event touches this zone
 */
export function getZoneEtaInfo(etaEvents, zoneId) {
  // 1. This zone is the origin of a confirmed surge — the most specific,
  // authoritative thing it could show about itself.
  const asSource = etaEvents[zoneId]
  if (asSource?.kind === 'SURGE') {
    return { type: 'SOURCE', sourceZone: zoneId, sourceTimeMs: asSource.sourceTimeMs }
  }

  // 2. A sensor already observed the wave here, under some confirmed event.
  for (const event of Object.values(etaEvents)) {
    if (event.kind !== 'SURGE') continue
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

  // 3. Downstream of a confirmed surge's prediction list.
  for (const event of Object.values(etaEvents)) {
    if (event.kind !== 'SURGE') continue
    const prediction = event.predictions.find((p) => p.zone_id === zoneId)
    if (prediction) {
      return { type: 'FORECAST', sourceZone: event.sourceZone, sourceTimeMs: event.sourceTimeMs, prediction }
    }
  }

  // 4. This zone is itself the WATCH-triggered source of the preliminary
  // estimates its own downstream neighbors are seeing — not a confirmed
  // surge, so it gets its own (differently worded) self-referential state.
  if (asSource?.kind === 'WATCH') {
    return {
      type: 'WATCH_SOURCE',
      sourceZone: zoneId,
      sourceTimeMs: asSource.sourceTimeMs,
      warnedZones: asSource.predictions.map((p) => p.zone_id),
    }
  }

  // 5. Downstream of some other zone's WATCH-triggered preliminary estimate.
  for (const event of Object.values(etaEvents)) {
    if (event.kind !== 'WATCH') continue
    const prediction = event.predictions.find((p) => p.zone_id === zoneId)
    if (prediction) {
      return { type: 'FORECAST', sourceZone: event.sourceZone, sourceTimeMs: event.sourceTimeMs, prediction }
    }
  }

  return null
}

/**
 * Soonest still-pending arrival across every active event, for a top-level
 * summary tile. A confirmed SURGE prediction always wins over a WATCH-kind
 * preliminary one, even if the preliminary window happens to be sooner —
 * the confirmed forecast is the more useful thing to surface first.
 */
export function getNextArrival(etaEvents, nowMs) {
  for (const kind of ['SURGE', 'WATCH']) {
    let best = null
    for (const event of Object.values(etaEvents)) {
      if (event.kind !== kind) continue
      for (const prediction of event.predictions) {
        if (event.observations[prediction.zone_id]) continue
        if (prediction.eta_max_ms < nowMs) continue
        if (!best || prediction.eta_min_ms < best.prediction.eta_min_ms) {
          best = { sourceZone: event.sourceZone, prediction }
        }
      }
    }
    if (best) return best
  }
  return null
}

/** Minutes remaining, clamped at zero — never shows a negative countdown. */
export function countdownMinutes(etaMinMs, etaMaxMs, nowMs) {
  const minLeft = Math.max(0, Math.ceil((etaMinMs - nowMs) / 60000))
  const maxLeft = Math.max(0, Math.ceil((etaMaxMs - nowMs) / 60000))
  return { minLeft, maxLeft, arrivingNow: maxLeft === 0 }
}
