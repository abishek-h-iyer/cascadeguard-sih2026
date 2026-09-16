// Real values from data/processed/zone_susceptibility_final.csv and
// data/processed/zone_coordinates.csv (RF terrain model + surveyed centroids).
// Kept separate from live sensor state so the static ML layer and the live
// risk engine never get confused with each other in the UI.

export const ZONE_IDS = [
  'MEL_Z01', 'MEL_Z02', 'MEL_Z03', 'MEL_Z04',
  'MEL_Z05', 'MEL_Z06', 'MEL_Z07', 'MEL_Z08',
  'MEL_Z09', 'MEL_Z10', 'MEL_Z11', 'MEL_Z12',
]

export const ZONE_STATIC = {
  MEL_Z01: { lat: 28.132351193743787, lon: 85.51843192666857, susceptibilityScore: 0.4735345317661916, susceptibilityClass: 'MODERATE' },
  MEL_Z02: { lat: 28.112657140938634, lon: 85.54336576900093, susceptibilityScore: 0.7810883086337909, susceptibilityClass: 'HIGH' },
  MEL_Z03: { lat: 28.08716141197509, lon: 85.52839290494447, susceptibilityScore: 0.7259657052146276, susceptibilityClass: 'HIGH' },
  MEL_Z04: { lat: 28.05669857600072, lon: 85.52428556002697, susceptibilityScore: 0.4334585382237969, susceptibilityClass: 'MODERATE' },
  MEL_Z05: { lat: 28.023892948333362, lon: 85.52985010003086, susceptibilityScore: 0.1865387174157016, susceptibilityClass: 'LOW' },
  MEL_Z06: { lat: 27.993656694502086, lon: 85.53233101629563, susceptibilityScore: 0.16164147871888515, susceptibilityClass: 'LOW' },
  MEL_Z07: { lat: 27.961530582566, lon: 85.52211261843321, susceptibilityScore: 0.11985578320794182, susceptibilityClass: 'LOW' },
  MEL_Z08: { lat: 27.944274340771234, lon: 85.56412711720044, susceptibilityScore: 0.12271355973869116, susceptibilityClass: 'LOW' },
  MEL_Z09: { lat: 27.91319188836543, lon: 85.53708443105411, susceptibilityScore: 0.116721490109103, susceptibilityClass: 'LOW' },
  MEL_Z10: { lat: 27.8808493075097, lon: 85.52752717044814, susceptibilityScore: 0.1386610096895661, susceptibilityClass: 'LOW' },
  MEL_Z11: { lat: 27.84809178042635, lon: 85.5337489430202, susceptibilityScore: 0.077568848102506, susceptibilityClass: 'LOW' },
  MEL_Z12: { lat: 27.836291692701643, lon: 85.56610251341645, susceptibilityScore: 0.17828565253761428, susceptibilityClass: 'LOW' },
}

export function zoneNumber(zoneId) {
  return Number(zoneId.split('Z')[1])
}

export function downstreamZones(zoneId, count = 4) {
  const n = zoneNumber(zoneId)
  const zones = []
  for (let v = n + 1; v <= Math.min(n + count, 12); v++) {
    zones.push(`MEL_Z${String(v).padStart(2, '0')}`)
  }
  return zones
}
