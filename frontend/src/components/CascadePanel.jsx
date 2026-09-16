import { getZoneEtaInfo } from '../utils/eta'
import './CascadePanel.css'

function buildStages(zone, etaEvents) {
  const { sensor_states, cascade, downstream_warnings } = zone
  const etaInfo = getZoneEtaInfo(etaEvents, zone.zone_id)
  return [
    { label: 'Heavy Rain', detected: sensor_states.rainfall === 'HIGH' || sensor_states.rainfall === 'SEVERE' },
    { label: 'Soil Saturation', detected: sensor_states.soil === 'HIGH' || sensor_states.soil === 'SATURATED' },
    { label: 'Slope Movement', detected: sensor_states.tilt === 'ABNORMAL' },
    { label: 'Possible Landslide', detected: cascade.possible_landslide },
    { label: 'Possible River Blockage', detected: cascade.possible_blockage },
    { label: 'Possible Surge', detected: cascade.possible_surge, inactiveLabel: 'Surge Not Yet Detected' },
    { label: 'Downstream Warning', detected: downstream_warnings.length > 0 },
    {
      label: etaInfo?.type === 'ARRIVED' ? 'Flood Arrival Observed' : 'Arrival Forecast (ETA)',
      detected: etaInfo != null,
      inactiveLabel: 'ETA Not Yet Activated',
    },
  ]
}

export default function CascadePanel({ zone, etaEvents = {} }) {
  const stages = buildStages(zone, etaEvents)

  return (
    <div>
      <span className="panel-title">Cascade Detection</span>
      <ol className="cascade-list">
        {stages.map((stage, i) => (
          <li key={stage.label} className={stage.detected ? 'cascade-item detected' : 'cascade-item'}>
            <span className="cascade-marker">{stage.detected ? '✓' : '○'}</span>
            <span className="cascade-label">{stage.detected ? stage.label : (stage.inactiveLabel || stage.label)}</span>
            {i < stages.length - 1 && <span className="cascade-connector" aria-hidden="true" />}
          </li>
        ))}
      </ol>
    </div>
  )
}
