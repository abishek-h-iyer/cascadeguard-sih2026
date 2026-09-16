// Faithful JS port of backend/eta_engine.py (ETAEngine.predict /
// update_from_observation), same spirit as riskEngine.js's port of
// risk_engine.py: kept in lockstep with the Python physics so the frontend
// produces the same numbers the real FastAPI/gateway ETA endpoints will once
// they're wired up. Timestamps are kept as epoch-ms numbers (not the
// HH:MM:SS strings the backend returns) so the UI can do live countdown math;
// format with utils/format.js's clockTime() for display.
import { ETA_REACHES } from '../data/etaReachData'
import { ZONE_IDS, zoneNumber } from '../data/zoneStaticData'

const MANNING_N_FAST = 0.035
const MANNING_N_SLOW = 0.05
const HYDRAULIC_RADIUS_FAST = 0.6
const HYDRAULIC_RADIUS_SLOW = 0.3

const MANNING_N_NOMINAL = 0.0425
const HYDRAULIC_RADIUS_NOMINAL = 0.45

const CELERITY_FACTOR = 5 / 3

function velocity(slope, manningN, hydraulicRadius) {
  if (slope <= 0) return 0
  return (1 / manningN) * hydraulicRadius ** (2 / 3) * slope ** 0.5
}

function celerity(slope, manningN, hydraulicRadius) {
  return CELERITY_FACTOR * velocity(slope, manningN, hydraulicRadius)
}

function downstreamReaches(sourceZoneId, count) {
  const sourceNumber = zoneNumber(sourceZoneId)
  return ZONE_IDS
    .filter((zoneId) => zoneNumber(zoneId) > sourceNumber)
    .sort((a, b) => zoneNumber(a) - zoneNumber(b))
    .slice(0, count)
    .map((zoneId) => ({ zone_id: zoneId, ...ETA_REACHES[zoneId] }))
}

/** Physics-informed initial forecast from a surge source zone. */
export function predict(sourceZone, eventTimeMs, zoneCount = 4) {
  const reaches = downstreamReaches(sourceZone, zoneCount)

  let cumulativeMinSeconds = 0
  let cumulativeMaxSeconds = 0

  return reaches.map((reach) => {
    const { reach_length_m: length, reach_slope: slope } = reach

    const fastCelerity = celerity(slope, MANNING_N_FAST, HYDRAULIC_RADIUS_FAST)
    const slowCelerity = celerity(slope, MANNING_N_SLOW, HYDRAULIC_RADIUS_SLOW)

    cumulativeMinSeconds += length / fastCelerity
    cumulativeMaxSeconds += length / slowCelerity

    return {
      zone_id: reach.zone_id,
      reach_length_km: Number((length / 1000).toFixed(2)),
      reach_slope: Number(slope.toFixed(4)),
      celerity_min_m_s: Number(slowCelerity.toFixed(2)),
      celerity_max_m_s: Number(fastCelerity.toFixed(2)),
      travel_time_min_minutes: Number((cumulativeMinSeconds / 60).toFixed(1)),
      travel_time_max_minutes: Number((cumulativeMaxSeconds / 60).toFixed(1)),
      eta_min_ms: eventTimeMs + cumulativeMinSeconds * 1000,
      eta_max_ms: eventTimeMs + cumulativeMaxSeconds * 1000,
      forecast_type: 'PHYSICS_INITIAL',
    }
  })
}

/** Recalibrate downstream forecast from a real sensor-observed wave arrival. */
export function updateFromObservation(sourceZone, observedZone, sourceTimeMs, observedTimeMs, zoneCount = 4, uncertaintyFraction = 0.2) {
  const sourceNumber = zoneNumber(sourceZone)
  const observedNumber = zoneNumber(observedZone)

  if (observedNumber <= sourceNumber) {
    throw new Error('Observed zone must be downstream.')
  }

  const observedReaches = ZONE_IDS
    .filter((zoneId) => zoneNumber(zoneId) > sourceNumber && zoneNumber(zoneId) <= observedNumber)
    .sort((a, b) => zoneNumber(a) - zoneNumber(b))
    .map((zoneId) => ({ zone_id: zoneId, ...ETA_REACHES[zoneId] }))

  const actualTravelSeconds = (observedTimeMs - sourceTimeMs) / 1000
  if (actualTravelSeconds <= 0) {
    throw new Error('Observed time must be after source time.')
  }

  const totalDistance = observedReaches.reduce((sum, r) => sum + r.reach_length_m, 0)
  const observedAverageSpeed = totalDistance / actualTravelSeconds

  let nominalTravelSeconds = 0
  for (const reach of observedReaches) {
    const nominalCelerity = celerity(reach.reach_slope, MANNING_N_NOMINAL, HYDRAULIC_RADIUS_NOMINAL)
    nominalTravelSeconds += reach.reach_length_m / nominalCelerity
  }

  const calibrationFactor = nominalTravelSeconds / actualTravelSeconds

  const downstream = downstreamReaches(observedZone, zoneCount)

  let cumulativeMinSeconds = 0
  let cumulativeMaxSeconds = 0

  const predictions = downstream.map((reach) => {
    const { reach_length_m: length, reach_slope: slope } = reach

    const nominalCelerity = celerity(slope, MANNING_N_NOMINAL, HYDRAULIC_RADIUS_NOMINAL)
    const correctedCelerity = nominalCelerity * calibrationFactor

    const slowCelerity = correctedCelerity * (1 - uncertaintyFraction)
    const fastCelerity = correctedCelerity * (1 + uncertaintyFraction)

    cumulativeMinSeconds += length / fastCelerity
    cumulativeMaxSeconds += length / slowCelerity

    return {
      zone_id: reach.zone_id,
      nominal_celerity_m_s: Number(nominalCelerity.toFixed(2)),
      corrected_celerity_m_s: Number(correctedCelerity.toFixed(2)),
      travel_time_min_minutes: Number((cumulativeMinSeconds / 60).toFixed(1)),
      travel_time_max_minutes: Number((cumulativeMaxSeconds / 60).toFixed(1)),
      eta_min_ms: observedTimeMs + cumulativeMinSeconds * 1000,
      eta_max_ms: observedTimeMs + cumulativeMaxSeconds * 1000,
      forecast_type: 'SENSOR_CALIBRATED',
    }
  })

  return {
    observation: {
      distance_m: Number(totalDistance.toFixed(2)),
      travel_seconds: Number(actualTravelSeconds.toFixed(2)),
      observed_celerity_m_s: Number(observedAverageSpeed.toFixed(3)),
      nominal_travel_minutes: Number((nominalTravelSeconds / 60).toFixed(2)),
      calibration_factor: Number(calibrationFactor.toFixed(3)),
    },
    predictions,
  }
}
