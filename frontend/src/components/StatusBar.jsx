import { useEffect, useState } from 'react'
import { timeAgo } from '../utils/format'
import './StatusBar.css'

export default function StatusBar({ connection, onOpenSimulator }) {
  const [, forceTick] = useState(0)

  useEffect(() => {
    const id = setInterval(() => forceTick((n) => n + 1), 1000)
    return () => clearInterval(id)
  }, [])

  return (
    <header className="status-bar panel">
      <div className="status-bar-brand">
        <span className="status-bar-title">CASCADEGUARD</span>
        <span className="status-bar-subtitle">Flash Flood &amp; Cascade Warning — Melamchi</span>
      </div>

      <div className="status-bar-items">
        <div className="status-bar-item">
          <span className={`status-dot ${connection.systemOnline ? 'safe' : 'critical'}`} />
          <span>System {connection.systemOnline ? 'ONLINE' : 'OFFLINE'}</span>
        </div>
        <div className="status-bar-item">
          <span className={`status-dot ${connection.gatewayConnected ? 'safe' : 'critical'}`} />
          <span>Gateway {connection.gatewayConnected ? 'CONNECTED' : 'DISCONNECTED'}</span>
        </div>
        <div className="status-bar-item status-bar-item-muted">
          Last sensor update: {timeAgo(connection.lastSensorUpdate)}
        </div>
        <button className="status-bar-sim-btn" onClick={onOpenSimulator}>
          Simulate
        </button>
      </div>
    </header>
  )
}
