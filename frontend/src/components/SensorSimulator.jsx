import { DEMO_SCENARIOS } from '../utils/riskEngine'
import { STATUS_LABEL } from '../utils/riskMapping'
import './SensorSimulator.css'

const SLIDERS = [
  { key: 'rainfall_mm_h', label: 'Rainfall (mm/h)', min: 0, max: 80, step: 1 },
  { key: 'soil_moisture', label: 'Soil Moisture', min: 0, max: 1, step: 0.01 },
  { key: 'tilt_change_deg', label: 'Tilt Change (°)', min: 0, max: 2.5, step: 0.01 },
  { key: 'upstream_rise_m_10m', label: 'Upstream Rise (m / 10 min)', min: 0, max: 1.5, step: 0.01 },
  { key: 'downstream_rise_m_10m', label: 'Downstream Rise (m / 10 min)', min: 0, max: 1.5, step: 0.01 },
]

const PRESETS = [
  { key: 'NORMAL', label: 'Normal' },
  { key: 'HEAVY_RAIN', label: 'Heavy Rain' },
  { key: 'BLOCKAGE', label: 'Blockage' },
  { key: 'SURGE', label: 'Surge / Release' },
]

export default function SensorSimulator({ isOpen, onClose, zone, sensors, isOverridden, onChange, onApplyPreset, onReset }) {
  if (!isOpen) return null

  return (
    <div className="simulator-backdrop" onClick={onClose}>
      <div className="simulator-panel panel" onClick={(e) => e.stopPropagation()}>
        <div className="simulator-head">
          <div>
            <span className="panel-title">Sensor Simulator</span>
            <div className="simulator-zone mono">{zone.zone_id}</div>
          </div>
          <button className="simulator-close" onClick={onClose}>✕</button>
        </div>

        <p className="simulator-hint">
          Drag any value to see the risk engine react live. Values map onto the same
          thresholds as the real engine, so any combination will land on a real
          operational status — not a canned scenario.
        </p>

        <div className="simulator-result">
          <span className={`status-chip ${zone.operational_status.toLowerCase()}`}>
            {STATUS_LABEL[zone.operational_status]}
          </span>
          <span className="simulator-result-level">Engine risk: {zone.alert_level}</span>
        </div>

        <div className="simulator-presets">
          {PRESETS.map((preset) => (
            <button key={preset.key} className="simulator-preset-btn" onClick={() => onApplyPreset(DEMO_SCENARIOS[preset.key])}>
              {preset.label}
            </button>
          ))}
        </div>

        <div className="simulator-sliders">
          {SLIDERS.map(({ key, label, min, max, step }) => (
            <label className="simulator-slider" key={key}>
              <div className="simulator-slider-label">
                <span>{label}</span>
                <span className="mono">{sensors[key].toFixed(2)}</span>
              </div>
              <input
                type="range"
                min={min}
                max={max}
                step={step}
                value={sensors[key]}
                onChange={(e) => onChange({ [key]: Number(e.target.value) })}
              />
            </label>
          ))}
        </div>

        <button className="simulator-reset-btn" onClick={onReset} disabled={!isOverridden}>
          Reset to Live Feed
        </button>
      </div>
    </div>
  )
}
