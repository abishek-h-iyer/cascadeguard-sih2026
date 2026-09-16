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
  if (!info) return null

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

  return (
    <div className="eta-forecast">
      <span className="panel-title">Flood-Arrival ETA</span>
      <div className={`eta-forecast-card ${prediction.forecast_type === 'SENSOR_CALIBRATED' ? 'calibrated' : ''}`}>
        <div className="eta-forecast-badge-row">
          <span className={`eta-forecast-badge ${prediction.forecast_type === 'SENSOR_CALIBRATED' ? 'calibrated' : ''}`}>
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
