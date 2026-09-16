import './WhyAtRisk.css'

const STATE_LABEL = {
  LOW: 'Low', MODERATE: 'Moderate', HIGH: 'High', SEVERE: 'Severe',
  NORMAL: 'Normal', ELEVATED: 'Elevated', SATURATED: 'Saturated',
  WATCH: 'Watch', ABNORMAL: 'Abnormal',
  STABLE: 'Stable', RISING: 'Rising', RAPID_RISE: 'Rapid Rise', SURGE: 'Surge',
}

const CONCERNING = new Set(['HIGH', 'SEVERE', 'SATURATED', 'ABNORMAL', 'RAPID_RISE', 'SURGE'])
const WATCHING = new Set(['MODERATE', 'ELEVATED', 'WATCH', 'RISING'])

function severityClass(state) {
  if (CONCERNING.has(state)) return 'critical'
  if (WATCHING.has(state)) return 'watch'
  return 'safe'
}

function buildFactors(zone) {
  const s = zone.sensors
  const st = zone.sensor_states
  return [
    { label: 'Terrain Susceptibility', value: zone.terrain.susceptibility_class, state: zone.terrain.susceptibility_class },
    { label: 'Rainfall', value: `${s.rainfall_mm_h.toFixed(0)} mm/h`, state: st.rainfall },
    { label: 'Soil Moisture', value: s.soil_moisture.toFixed(2), state: st.soil },
    { label: 'Tilt Change', value: `${s.tilt_change_deg.toFixed(2)}°`, state: st.tilt },
    { label: 'Upstream Rise', value: `${s.upstream_rise_m_10m.toFixed(2)} m / 10 min`, state: st.upstream },
    { label: 'Downstream Rise', value: `${s.downstream_rise_m_10m.toFixed(2)} m / 10 min`, state: st.downstream },
  ]
}

function buildChain(zone) {
  const chain = []
  if (zone.cascade.possible_landslide) chain.push('Possible Landslide')
  if (zone.cascade.possible_blockage) chain.push('Possible River Blockage')
  if (zone.cascade.possible_surge) chain.push('Possible Surge')
  if (chain.length === 0 && zone.reasons.length > 0) chain.push(zone.reasons[0])
  chain.push(zone.operational_status)
  return chain
}

export default function WhyAtRisk({ zone }) {
  const factors = buildFactors(zone)
  const chain = buildChain(zone)

  return (
    <div>
      <span className="panel-title">Why Is This Zone At Risk?</span>
      <p className="why-hint">
        Terrain susceptibility comes from historical GIS/ML analysis of the land itself.
        Live sensors show what is happening right now. The risk engine combines both.
      </p>
      <ul className="why-factors">
        {factors.map((f) => (
          <li key={f.label} className="why-factor">
            <span className="why-factor-label">{f.label}</span>
            <span className="why-factor-value mono">{f.value}</span>
            <span className={`why-factor-state ${severityClass(f.state)}`}>{STATE_LABEL[f.state] || f.state}</span>
          </li>
        ))}
      </ul>
      <div className="why-chain">
        {chain.map((step, i) => (
          <span key={step} className="why-chain-step">
            {i > 0 && <span className="why-chain-arrow">→</span>}
            <span className={i === chain.length - 1 ? 'why-chain-final' : ''}>{step}</span>
          </span>
        ))}
      </div>
    </div>
  )
}
