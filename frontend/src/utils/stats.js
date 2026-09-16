const RANK = { SAFE: 0, WATCH: 1, CRITICAL: 2 }

export function computeStats(zones) {
  const list = Object.values(zones)
  let highest = list[0]
  let critical = 0
  let watch = 0

  for (const zone of list) {
    if (zone.operational_status === 'CRITICAL') critical += 1
    if (zone.operational_status === 'WATCH') watch += 1
    if (RANK[zone.operational_status] > RANK[highest.operational_status]) highest = zone
  }

  return { highest, critical, watch }
}
