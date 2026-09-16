import { useEffect } from 'react'
import { MapContainer, TileLayer, Polyline, useMap } from 'react-leaflet'
import L from 'leaflet'
import 'leaflet/dist/leaflet.css'
import ZoneMarkers from './ZoneMarkers'
import RiskToggle from './RiskToggle'
import { ZONE_IDS, ZONE_STATIC } from '../data/zoneStaticData'
import { statusColor } from '../utils/riskMapping'
import './MapPanel.css'

const CENTER = [27.99, 85.535]

const ZONE_BOUNDS = L.latLngBounds(ZONE_IDS.map((id) => [ZONE_STATIC[id].lat, ZONE_STATIC[id].lon]))

function FitZonesOnLoad() {
  const map = useMap()
  useEffect(() => {
    map.fitBounds(ZONE_BOUNDS, { padding: [40, 40] })
  }, [map])
  return null
}

function riverSegments(zones) {
  const segments = []
  for (let i = 0; i < ZONE_IDS.length - 1; i++) {
    const from = ZONE_IDS[i]
    const to = ZONE_IDS[i + 1]
    const toZone = zones[to]
    const isPropagating = toZone.incoming_warning != null
    segments.push({
      key: `${from}-${to}`,
      positions: [
        [ZONE_STATIC[from].lat, ZONE_STATIC[from].lon],
        [ZONE_STATIC[to].lat, ZONE_STATIC[to].lon],
      ],
      color: isPropagating ? statusColor(toZone.incoming_warning.status) : '#9aa7b5',
      weight: isPropagating ? 4 : 2,
      dashArray: isPropagating ? null : '4 6',
    })
  }
  return segments
}

export default function MapPanel({ zones, riskViewMode, onRiskViewModeChange, selectedZoneId, onSelectZone, etaEvents = {} }) {
  return (
    <div className="map-panel panel">
      <MapContainer center={CENTER} zoom={10} className="map-panel-map" scrollWheelZoom>
        <TileLayer
          attribution='&copy; OpenStreetMap contributors'
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        />
        <FitZonesOnLoad />
        {riverSegments(zones).map((seg) => (
          <Polyline
            key={seg.key}
            positions={seg.positions}
            pathOptions={{ color: seg.color, weight: seg.weight, dashArray: seg.dashArray }}
          />
        ))}
        <ZoneMarkers
          zones={zones}
          riskViewMode={riskViewMode}
          selectedZoneId={selectedZoneId}
          onSelectZone={onSelectZone}
          etaEvents={etaEvents}
        />
      </MapContainer>

      <div className="map-panel-toggle">
        <RiskToggle mode={riskViewMode} onChange={onRiskViewModeChange} />
      </div>

      <div className="map-panel-legend">
        {riskViewMode === 'LIVE' ? (
          <>
            <LegendItem colorVar="--color-safe" label="Safe" />
            <LegendItem colorVar="--color-watch" label="Watch" />
            <LegendItem colorVar="--color-critical" label="Critical" />
          </>
        ) : (
          <>
            <LegendItem colorVar="--susceptibility-low" label="Low" />
            <LegendItem colorVar="--susceptibility-moderate" label="Moderate" />
            <LegendItem colorVar="--susceptibility-high" label="High" />
          </>
        )}
      </div>
    </div>
  )
}

function LegendItem({ colorVar, label }) {
  return (
    <span className="map-panel-legend-item">
      <span className="map-panel-legend-swatch" style={{ background: `var(${colorVar})` }} />
      {label}
    </span>
  )
}
