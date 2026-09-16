import { CircleMarker, Tooltip } from 'react-leaflet'
import { ZONE_STATIC } from '../data/zoneStaticData'
import { statusColor, susceptibilityColor, STATUS_LABEL } from '../utils/riskMapping'

const STATUS_RANK = { SAFE: 0, WATCH: 1, CRITICAL: 2 }
const SUSCEPTIBILITY_RANK = { LOW: 0, MODERATE: 1, HIGH: 2 }

// Rendered as CircleMarkers at real surveyed centroids until the backend
// team supplies zone polygon GeoJSON. Swapping to real polygons later means
// replacing this loop with a single <GeoJSON data={...} style={styleFor}>
// layer — styleFor() below is written so it can be reused as-is.
export default function ZoneMarkers({ zones, riskViewMode, selectedZoneId, onSelectZone }) {
  const isLiveMode = riskViewMode === 'LIVE'

  // Zones can sit close enough together to visually overlap at this scale.
  // Draw lower-severity zones first so a WATCH/CRITICAL marker is never
  // hidden underneath a SAFE one drawn on top of it.
  const ordered = [...Object.values(zones)].sort((a, b) => {
    const rankA = isLiveMode ? STATUS_RANK[a.operational_status] : SUSCEPTIBILITY_RANK[a.terrain.susceptibility_class]
    const rankB = isLiveMode ? STATUS_RANK[b.operational_status] : SUSCEPTIBILITY_RANK[b.terrain.susceptibility_class]
    return rankA - rankB
  })

  return (
    <>
      {ordered.map((zone) => {
        const coords = ZONE_STATIC[zone.zone_id]
        const isLive = riskViewMode === 'LIVE'
        const color = isLive
          ? statusColor(zone.operational_status)
          : susceptibilityColor(zone.terrain.susceptibility_class)
        const isSelected = zone.zone_id === selectedZoneId
        const isCritical = isLive && zone.operational_status === 'CRITICAL'

        return (
          <CircleMarker
            key={zone.zone_id}
            center={[coords.lat, coords.lon]}
            radius={isSelected ? 14 : isCritical ? 12 : 9}
            pathOptions={{
              color: isSelected ? '#1b2430' : color,
              weight: isSelected ? 3 : isCritical ? 3 : 2,
              fillColor: color,
              fillOpacity: 0.85,
            }}
            eventHandlers={{ click: () => onSelectZone(zone.zone_id) }}
          >
            <Tooltip direction="top" offset={[0, -8]}>
              <strong>{zone.zone_id}</strong>
              <br />
              {isLive
                ? STATUS_LABEL[zone.operational_status]
                : `${zone.terrain.susceptibility_class} susceptibility`}
            </Tooltip>
          </CircleMarker>
        )
      })}
    </>
  )
}
