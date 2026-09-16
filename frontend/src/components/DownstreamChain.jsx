import { ZONE_IDS } from '../data/zoneStaticData'
import { statusColor } from '../utils/riskMapping'
import './DownstreamChain.css'

export default function DownstreamChain({ zones, selectedZoneId, onSelectZone }) {
  return (
    <div className="downstream-chain panel">
      <span className="panel-title">Downstream Flow — MEL_Z01 to MEL_Z12</span>
      <div className="downstream-chain-track">
        {ZONE_IDS.map((zoneId, i) => {
          const zone = zones[zoneId]
          const isLast = i === ZONE_IDS.length - 1
          const isCritical = zone.operational_status === 'CRITICAL'
          const shortId = zoneId.slice(-2)

          return (
            <div className="downstream-chain-item" key={zoneId}>
              <button
                className={`downstream-chain-node${zoneId === selectedZoneId ? ' selected' : ''}`}
                style={{ '--node-color': statusColor(zone.operational_status) }}
                onClick={() => onSelectZone(zoneId)}
                title={`${zoneId} — ${zone.operational_status}`}
              >
                {isCritical && <span className="downstream-chain-warn">⚠</span>}
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
