import ZoneHeader from './ZoneHeader'
import LiveSensorCards from './LiveSensorCards'
import CascadePanel from './CascadePanel'
import WhyAtRisk from './WhyAtRisk'
import SensorNodeStatus from './SensorNodeStatus'
import './ZoneDetailPanel.css'

export default function ZoneDetailPanel({ zone }) {
  if (!zone) {
    return (
      <aside className="zone-detail panel">
        <p className="zone-detail-empty">Click a zone on the map to view details.</p>
      </aside>
    )
  }

  return (
    <aside className="zone-detail panel">
      <ZoneHeader zone={zone} />
      <hr className="zone-detail-divider" />
      <LiveSensorCards sensors={zone.sensors} />
      <hr className="zone-detail-divider" />
      <CascadePanel zone={zone} />
      <hr className="zone-detail-divider" />
      <WhyAtRisk zone={zone} />
      <hr className="zone-detail-divider" />
      <SensorNodeStatus sensorNodes={zone.sensor_nodes} />
    </aside>
  )
}
