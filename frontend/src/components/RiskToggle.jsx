import './RiskToggle.css'

export default function RiskToggle({ mode, onChange }) {
  return (
    <div className="risk-toggle">
      <button
        className={mode === 'LIVE' ? 'risk-toggle-btn active' : 'risk-toggle-btn'}
        onClick={() => onChange('LIVE')}
      >
        Live Risk
      </button>
      <button
        className={mode === 'TERRAIN' ? 'risk-toggle-btn active' : 'risk-toggle-btn'}
        onClick={() => onChange('TERRAIN')}
      >
        Terrain Susceptibility
      </button>
    </div>
  )
}
