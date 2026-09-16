import './SensorNodeStatus.css'

export default function SensorNodeStatus({ sensorNodes }) {
  return (
    <div>
      <span className="panel-title">Sensor / Communication Status</span>
      <div className="node-list">
        {sensorNodes.map((node) => (
          <div className="node-card" key={node.node}>
            <div className="node-card-head">
              <span className="node-card-id mono">{node.node}</span>
              <span className={`status-chip ${node.online ? 'safe' : 'offline'}`}>
                {node.online ? 'Online' : 'Offline'}
              </span>
            </div>
            <div className="node-card-value mono">
              {node.value.toFixed(2)} {node.unit}
            </div>
            <div className="node-card-meta mono">
              SEQ {node.sequence} &nbsp;CRC {node.crcValid ? '✓' : '✗'}
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
