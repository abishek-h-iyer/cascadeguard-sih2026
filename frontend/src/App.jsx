import { useState } from 'react'
import { useDashboardStore } from './hooks/useDashboardStore'
import { mockStore } from './services/mockStore'
import { computeStats } from './utils/stats'
import StatusBar from './components/StatusBar'
import StatStrip from './components/StatStrip'
import MapPanel from './components/MapPanel'
import DownstreamChain from './components/DownstreamChain'
import ZoneDetailPanel from './components/ZoneDetailPanel'
import AlertFeed from './components/AlertFeed'
import SensorSimulator from './components/SensorSimulator'
import './styles/tokens.css'
import './styles/layout.css'

export default function App() {
  const { zones, events, connection, riskViewMode, selectedZoneId } = useDashboardStore()
  const [simulatorOpen, setSimulatorOpen] = useState(false)

  const hasZones = Object.keys(zones).length > 0
  if (!hasZones) return null

  const stats = computeStats(zones)
  const selectedZone = selectedZoneId ? zones[selectedZoneId] : null

  return (
    <div className="dashboard">
      <StatusBar connection={connection} onOpenSimulator={() => setSimulatorOpen(true)} />

      <StatStrip stats={stats} connection={connection} onSelectZone={mockStore.selectZone} />

      <div className="dashboard-main">
        <div className="dashboard-main-left">
          <MapPanel
            zones={zones}
            riskViewMode={riskViewMode}
            onRiskViewModeChange={mockStore.setRiskViewMode}
            selectedZoneId={selectedZoneId}
            onSelectZone={mockStore.selectZone}
          />
          <DownstreamChain zones={zones} selectedZoneId={selectedZoneId} onSelectZone={mockStore.selectZone} />
        </div>

        <ZoneDetailPanel zone={selectedZone} />
      </div>

      <AlertFeed events={events} />

      {selectedZone && (
        <SensorSimulator
          isOpen={simulatorOpen}
          onClose={() => setSimulatorOpen(false)}
          zone={selectedZone}
          sensors={selectedZone.sensors}
          isOverridden={selectedZone.overridden}
          onChange={(partial) => mockStore.setSensorOverride(selectedZoneId, partial)}
          onApplyPreset={(preset) => mockStore.setSensorOverride(selectedZoneId, preset)}
          onReset={() => mockStore.clearOverride(selectedZoneId)}
        />
      )}
    </div>
  )
}
