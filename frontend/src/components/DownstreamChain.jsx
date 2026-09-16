import { ZONE_IDS } from '../data/zoneStaticData'
import { statusColor } from '../utils/riskMapping'
import { getZoneEtaInfo, countdownMinutes } from '../utils/eta'
import './DownstreamChain.css'

function etaTooltip(zone, etaInfo) {
  if (!etaInfo) return `${zone.zone_id} — ${zone.operational_status}`
  if (etaInfo.type === 'SOURCE') return `${zone.zone_id} — Surge source`
  if (etaInfo.type === 'WATCH_SOURCE') return `${zone.zone_id} — On watch, preliminary warning issued downstream`
  if (etaInfo.type === 'ARRIVED') return `${zone.zone_id} — Arrived, wave observed`
  const { minLeft, maxLeft, arrivingNow } = countdownMinutes(etaInfo.prediction.eta_min_ms, etaInfo.prediction.eta_max_ms, Date.now())
  const verb = etaInfo.prediction.forecast_type === 'EARLY_WARNING' ? 'Possible impact' : 'Impact'
  return arrivingNow ? `${zone.zone_id} — Arriving now` : `${zone.zone_id} — ${verb} in ${minLeft}-${maxLeft} min`
}

export default function DownstreamChain({ zones, etaEvents = {}, selectedZoneId, onSelectZone }) {
  return (
    <div className="downstream-chain panel">
      <span className="panel-title">Downstream Flow — MEL_Z01 to MEL_Z12</span>
      <div className="downstream-chain-track">
        {ZONE_IDS.map((zoneId, i) => {
          const zone = zones[zoneId]
          const isLast = i === ZONE_IDS.length - 1
          const isCritical = zone.operational_status === 'CRITICAL'
          const shortId = zoneId.slice(-2)
          const etaInfo = getZoneEtaInfo(etaEvents, zoneId)

          return (
            <div className="downstream-chain-item" key={zoneId}>
              <button
                className={`downstream-chain-node${zoneId === selectedZoneId ? ' selected' : ''}${etaInfo?.type === 'FORECAST' || etaInfo?.type === 'WATCH_SOURCE' ? ' eta-pending' : ''}`}
                style={{ '--node-color': statusColor(zone.operational_status) }}
                onClick={() => onSelectZone(zoneId)}
                title={etaTooltip(zone, etaInfo)}
              >
                {isCritical && <span className="downstream-chain-warn">⚠</span>}
                {etaInfo?.type === 'ARRIVED' && <span className="downstream-chain-arrived">✓</span>}
                Z{shortId}
              </button>
              {!isLast && <span className="downstream-chain-arrow">→</span>}
            </div>
          )
        })}
      </div>
    </div>
  )
}
