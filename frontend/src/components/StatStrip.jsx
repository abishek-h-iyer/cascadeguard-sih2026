import { STATUS_LABEL } from '../utils/riskMapping'
import { getNextArrival, countdownMinutes } from '../utils/eta'
import './StatStrip.css'

export default function StatStrip({ stats, connection, etaEvents = {}, onSelectZone }) {
  const { highest, critical, watch } = stats
  const statusClass = highest.operational_status.toLowerCase()
  const nextArrival = getNextArrival(etaEvents, Date.now())

  return (
    <section className="stat-strip">
      <button className="stat-tile panel stat-tile-clickable" onClick={() => onSelectZone(highest.zone_id)}>
        <span className="panel-title">Highest Risk Zone</span>
        <span className="stat-tile-value mono">{highest.zone_id}</span>
        <span className={`status-chip ${statusClass}`}>{STATUS_LABEL[highest.operational_status]}</span>
      </button>

      <div className="stat-tile panel">
        <span className="panel-title">Critical Zones</span>
        <span className="stat-tile-value stat-tile-value-critical">{critical}</span>
        <span className="stat-tile-sub">zone{critical === 1 ? '' : 's'}</span>
      </div>

      <div className="stat-tile panel">
        <span className="panel-title">Watch Zones</span>
        <span className="stat-tile-value stat-tile-value-watch">{watch}</span>
        <span className="stat-tile-sub">zone{watch === 1 ? '' : 's'}</span>
      </div>

      <div className="stat-tile panel">
        <span className="panel-title">Gateway</span>
        <span className={`status-chip ${connection.gatewayConnected ? 'safe' : 'critical'}`}>
          {connection.gatewayConnected ? 'Connected' : 'Disconnected'}
        </span>
      </div>

      {nextArrival && (
        <button
          className="stat-tile panel stat-tile-clickable"
          onClick={() => onSelectZone(nextArrival.prediction.zone_id)}
        >
          <span className="panel-title">Next Arrival</span>
          {(() => {
            const { minLeft, maxLeft, arrivingNow } = countdownMinutes(
              nextArrival.prediction.eta_min_ms,
              nextArrival.prediction.eta_max_ms,
              Date.now(),
            )
            return (
              <span className="stat-tile-value mono">
                {nextArrival.prediction.zone_id} — {arrivingNow ? 'now' : `${minLeft}–${maxLeft}m`}
              </span>
            )
          })()}
          <span className="stat-tile-sub">from {nextArrival.sourceZone}</span>
        </button>
      )}
    </section>
  )
}
