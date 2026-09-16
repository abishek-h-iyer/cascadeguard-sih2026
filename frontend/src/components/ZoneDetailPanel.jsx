import ZoneHeader from './ZoneHeader'
import LiveSensorCards from './LiveSensorCards'
import CascadePanel from './CascadePanel'
import EtaForecast from './EtaForecast'
import WhyAtRisk from './WhyAtRisk'
import SensorNodeStatus from './SensorNodeStatus'
import { getZoneEtaInfo } from '../utils/eta'
import './ZoneDetailPanel.css'

export default function ZoneDetailPanel({ zone, etaEvents = {} }) {
  if (!zone) {
    return (
      <aside className="zone-detail panel">
        <p className="zone-detail-empty">Click a zone on the map to view details.</p>
      </aside>
    )
  }

  const hasEta = getZoneEtaInfo(etaEvents, zone.zone_id) != null || zone.incoming_warning != null

  return (
    <aside className="zone-detail panel">
      <ZoneHeader zone={zone} />
      <hr className="zone-detail-divider" />
      <LiveSensorCards sensors={zone.sensors} />
      <hr className="zone-detail-divider" />
      <CascadePanel zone={zone} etaEvents={etaEvents} />
      {hasEta && (
        <>
          <hr className="zone-detail-divider" />
          <EtaForecast zone={zone} etaEvents={etaEvents} />
        </>
      )}
      <hr className="zone-detail-divider" />
      <WhyAtRisk zone={zone} />
      <hr className="zone-detail-divider" />
      <SensorNodeStatus sensorNodes={zone.sensor_nodes} />
    </aside>
  )
}
