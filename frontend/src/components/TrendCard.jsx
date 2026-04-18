import { ACTION_COLORS } from '../App'

export default function TrendCard({ trend: t }) {
  const ac = ACTION_COLORS[t.action] ?? ACTION_COLORS.PASS
  const flags = []
  if (t.compliance_ok === false) flags.push('FDA/Trade Blocked')
  if (t.shelf_life_months != null && t.shelf_life_months < 12) flags.push('Shelf Life < 12 mo')

  const pills = [
    t.category,
    t.market_stage,
    t.source_count > 1 ? `${t.source_count} sources` : null,
  ].filter(Boolean)

  const growth = t.growth_rate_pct
  const growthStr = growth != null ? `${growth > 0 ? '+' : ''}${growth}%` : '—'

  return (
    <div className="trend-card">
      <div className="trend-card-top">
        <div style={{ flex: 1 }}>
          <span className="action-tag" style={{ background: ac.bg, color: ac.color }}>{t.action}</span>
          <h3 className="trend-title">{t.name}</h3>
          <p className="trend-meta">
            Growth: <strong>{growthStr}</strong>
            {' · '}
            Recency: <strong>{t.recency_score != null ? t.recency_score.toFixed(2) : '—'}</strong>
            {flags.length > 0 && <span style={{ color: '#6f3640', marginLeft: '0.5rem' }}>⚠ {flags.join(', ')}</span>}
          </p>
        </div>
        <div className="score-block">
          <p className="score-caption">Composite</p>
          <p className="score-big" style={{ color: ac.color }}>{(t.composite_score ?? 0).toFixed(0)}</p>
          <p className="score-caption" style={{ marginTop: '0.4rem' }}>POP Fit</p>
          <p style={{ fontFamily: 'Fraunces, serif', fontSize: '1.3rem', lineHeight: 1, color: 'var(--muted)' }}>
            {(t.pop_fit_score ?? 0).toFixed(0)}
          </p>
        </div>
      </div>

      {pills.length > 0 && (
        <div className="pill-row">
          {pills.map(p => <span key={p} className="mini-pill">{p}</span>)}
          {t.pop_line_matches && t.pop_line_matches !== '[]' && t.pop_line_matches !== '' && (
            <span className="mini-pill" style={{ background: 'rgba(40,89,77,0.08)', color: '#28594d' }}>
              {(() => {
                try {
                  const m = JSON.parse(t.pop_line_matches)
                  return Array.isArray(m) ? m.join(', ') : t.pop_line_matches
                } catch { return t.pop_line_matches }
              })()}
            </span>
          )}
        </div>
      )}

      {t.top_evidence && (
        <div className="evidence-box">{t.top_evidence}</div>
      )}
    </div>
  )
}
