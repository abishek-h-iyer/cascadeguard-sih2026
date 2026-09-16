import './LiveSensorCards.css'

const FIELDS = [
  { key: 'rainfall_mm_h', label: 'Rainfall', unit: 'mm/h', decimals: 0 },
  { key: 'soil_moisture', label: 'Soil Moisture', unit: '', decimals: 2 },
  { key: 'tilt_change_deg', label: 'Tilt Change', unit: '°', decimals: 2 },
  { key: 'upstream_rise_m_10m', label: 'Upstream Rise', unit: 'm / 10 min', decimals: 2 },
  { key: 'downstream_rise_m_10m', label: 'Downstream Rise', unit: 'm / 10 min', decimals: 2 },
]

export default function LiveSensorCards({ sensors }) {
  return (
    <div>
      <span className="panel-title">Live Sensor Values</span>
      <div className="sensor-cards">
        {FIELDS.map(({ key, label, unit, decimals }) => (
          <div className="sensor-card" key={key}>
            <span className="sensor-card-label">{label}</span>
            <span className="sensor-card-value mono">
              {sensors[key].toFixed(decimals)}
              {unit && <span className="sensor-card-unit"> {unit}</span>}
            </span>
          </div>
        ))}
      </div>
    </div>
  )
}
