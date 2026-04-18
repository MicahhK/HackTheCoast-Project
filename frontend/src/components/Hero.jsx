export default function Hero({ trends }) {
  const total     = trends.length
  const actionable = trends.filter(t => t.action === 'DEVELOP' || t.action === 'DISTRIBUTE' || t.action === 'BOTH').length
  const compliant  = trends.filter(t => t.compliance_ok !== false).length
  const topScore   = trends.length ? Math.max(...trends.map(t => t.composite_score ?? 0)).toFixed(0) : '—'

  return (
    <div className="hero-shell">
      <div className="hero-kicker">
        <span style={{ width: 8, height: 8, borderRadius: '50%', background: '#28594d', display: 'inline-block' }} />
        POP Trend Intelligence
      </div>
      <h1 className="hero-title">Market Signal Radar</h1>
      <p className="hero-copy">
        Automated trend discovery for Prince of Peace Enterprises — surfacing high-fit opportunities
        across functional foods, wellness, and Asian specialty categories before competitors act.
      </p>
      <span className="hero-ribbon">Live Pipeline</span>

      <div className="metric-row">
        <div className="metric-card">
          <p className="metric-label">Signals Tracked</p>
          <p className="metric-value">{total}</p>
          <p className="metric-note">Across all sources</p>
        </div>
        <div className="metric-card">
          <p className="metric-label">Actionable Trends</p>
          <p className="metric-value" style={{ color: '#bb5c2a' }}>{actionable}</p>
          <p className="metric-note">DEVELOP or DISTRIBUTE</p>
        </div>
        <div className="metric-card">
          <p className="metric-label">Compliant</p>
          <p className="metric-value" style={{ color: '#28594d' }}>{compliant}</p>
          <p className="metric-note">Pass all POP gates</p>
        </div>
        <div className="metric-card">
          <p className="metric-label">Top Score</p>
          <p className="metric-value">{topScore}</p>
          <p className="metric-note">Composite (0–100)</p>
        </div>
      </div>
    </div>
  )
}
