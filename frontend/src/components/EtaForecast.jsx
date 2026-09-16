import { useEffect, useState } from 'react'
import { getZoneEtaInfo, countdownMinutes, FORECAST_BASIS } from '../utils/eta'
import { clockTime } from '../utils/format'
import './EtaForecast.css'

export default function EtaForecast({ zone, etaEvents }) {
  const [, forceTick] = useState(0)

  // Arrival windows are relative to the live clock, so this panel needs its
  // own tick the same way StatusBar.jsx ticks timeAgo().
  useEffect(() => {
    const id = setInterval(() => forceTick((n) => n + 1), 1000)
    return () => clearInterval(id)
  }, [])

  const info = getZoneEtaInfo(etaEvents, zone.zone_id)

  if (!info) {
    if (!zone.incoming_warning) return null
    // Downstream pre-warning (blockage detected upstream) but no confirmed
    // release yet — the ETA engine only activates on an actual surge, so
    // make it explicit this is pending rather than looking broken/missing.
    return (
      <div className="eta-forecast">
        <span className="panel-title">Flood-Arrival ETA</span>
        <div className="eta-forecast-pending">
          <span className="status-chip watch">Pending</span>
          <p className="eta-forecast-hint">
            {zone.incoming_warning.from_zone} is on watch for a possible blockage release.
            An arrival window will appear here once a real surge is detected —
            not before, since there's no confirmed wave to estimate yet.
          </p>
        </div>
      </div>
    )
  }

  if (info.type === 'SOURCE') {
    return (
      <div className="eta-forecast">
        <span className="panel-title">Flood-Arrival ETA</span>
        <div className="eta-forecast-source">
          <span className="eta-forecast-source-label">SURGE DETECTED — SOURCE ZONE</span>
          <span className="eta-forecast-source-time mono">
            Source event time: {clockTime(info.sourceTimeMs)}
          </span>
          <p className="eta-forecast-hint">
            Downstream arrival windows below are physics-informed from here, and will
            update as real sensors confirm the wave passing through each zone.
          </p>
        </div>
      </div>
    )
  }

  if (info.type === 'WATCH_SOURCE') {
    return (
      <div className="eta-forecast">
        <span className="panel-title">Flood-Arrival ETA</span>
        <div className="eta-forecast-pending">
          <span className="status-chip watch">On Watch</span>
          <p className="eta-forecast-hint">
            {zone.zone_id} is on watch — {info.warnedZones.join(', ')} now have a preliminary
            arrival estimate as a precaution. This is not a confirmed surge; it will clear if
            {' '}{zone.zone_id} returns to normal, or be replaced by a confirmed forecast if a
            real surge is detected.
          </p>
        </div>
      </div>
    )
  }

  if (info.type === 'ARRIVED') {
    const speed = info.observation.observed_celerity_m_s
    const travelMin = (info.observation.travel_seconds / 60).toFixed(1)
    return (
      <div className="eta-forecast">
        <span className="panel-title">Flood-Arrival ETA</span>
        <div className="eta-forecast-arrived">
          <span className="status-chip critical">Arrived</span>
          <dl className="eta-forecast-grid">
            <dt>Observed</dt>
            <dd className="mono">{clockTime(info.observedTimeMs)}</dd>
            <dt>Measured Travel Time</dt>
            <dd className="mono">{travelMin} min from {info.sourceZone}</dd>
            <dt>Observed Propagation</dt>
            <dd className="mono">{speed} m/s</dd>
          </dl>
        </div>
      </div>
    )
  }

  // FORECAST
  const { prediction } = info
  const basis = FORECAST_BASIS[prediction.forecast_type]
  const { minLeft, maxLeft, arrivingNow } = countdownMinutes(prediction.eta_min_ms, prediction.eta_max_ms, Date.now())
  const variantClass = prediction.forecast_type === 'SENSOR_CALIBRATED' ? 'calibrated'
    : prediction.forecast_type === 'EARLY_WARNING' ? 'preliminary'
    : ''

  return (
    <div className="eta-forecast">
      <span className="panel-title">Flood-Arrival ETA</span>
      <div className={`eta-forecast-card ${variantClass}`}>
        <div className="eta-forecast-badge-row">
          <span className={`eta-forecast-badge ${variantClass}`}>
            {basis.badge}
          </span>
          <span className="eta-forecast-badge-sub">{basis.sub}</span>
        </div>

        <div className="eta-forecast-main">
          <div className="eta-forecast-stat">
            <span className="eta-forecast-stat-label">Estimated Arrival</span>
            <span className="eta-forecast-stat-value mono">
              {clockTime(prediction.eta_min_ms)}–{clockTime(prediction.eta_max_ms)}
            </span>
          </div>
          <div className="eta-forecast-stat">
            <span className="eta-forecast-stat-label">Time to Impact</span>
            <span className="eta-forecast-stat-value mono">
              {arrivingNow ? 'ARRIVING' : `${minLeft}–${maxLeft} MIN`}
            </span>
          </div>
        </div>

        <p className="eta-forecast-source-line">
          Source: {info.sourceZone} &middot; {clockTime(info.sourceTimeMs)}
        </p>

        <details className="eta-forecast-details">
          <summary>Engineering details</summary>
          <dl className="eta-forecast-grid">
            <dt>Forecast Basis</dt>
            <dd>{basis.basisLine}</dd>
            {prediction.reach_length_km != null && (
              <>
                <dt>Reach Length</dt>
                <dd className="mono">{prediction.reach_length_km} km</dd>
                <dt>Reach Slope</dt>
                <dd className="mono">{prediction.reach_slope}</dd>
                <dt>Celerity Range</dt>
                <dd className="mono">{prediction.celerity_min_m_s}–{prediction.celerity_max_m_s} m/s</dd>
              </>
            )}
            {prediction.corrected_celerity_m_s != null && (
              <>
                <dt>Nominal Celerity</dt>
                <dd className="mono">{prediction.nominal_celerity_m_s} m/s</dd>
                <dt>Corrected Celerity</dt>
                <dd className="mono">{prediction.corrected_celerity_m_s} m/s</dd>
              </>
            )}
          </dl>
        </details>
      </div>
    </div>
  )
}
