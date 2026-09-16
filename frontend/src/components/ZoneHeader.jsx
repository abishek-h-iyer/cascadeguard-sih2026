import { clockTime } from '../utils/format'
import { STATUS_LABEL } from '../utils/riskMapping'
import './ZoneHeader.css'

export default function ZoneHeader({ zone }) {
  const statusClass = zone.operational_status.toLowerCase()

  return (
    <div className="zone-header">
      <div className="zone-header-top">
        <span className="zone-header-id mono">{zone.zone_id}</span>
        <span className={`status-chip ${statusClass}`}>{STATUS_LABEL[zone.operational_status]}</span>
      </div>

      <dl className="zone-header-grid">
        <dt>Engine Risk</dt>
        <dd>{zone.alert_level}</dd>

        <dt>Terrain Susceptibility</dt>
        <dd>{zone.terrain.susceptibility_class}</dd>

        <dt>Static Susceptibility Score</dt>
        <dd className="mono">{zone.terrain.susceptibility_score.toFixed(3)}</dd>

        <dt>Last Updated</dt>
        <dd className="mono">{clockTime(zone.last_updated)}</dd>
      </dl>

      {zone.overridden && (
        <div className="zone-header-override">Manual simulation active for this zone</div>
      )}
    </div>
  )
}
