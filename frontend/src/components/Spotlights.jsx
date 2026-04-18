import { ACTION_COLORS } from '../App'

export default function Spotlights({ spotlights }) {
  if (!spotlights.length) return null

  return (
    <>
      <p className="section-label">Top Opportunities</p>
      <div className="spotlights-grid">
        {spotlights.map(t => {
          const ac = ACTION_COLORS[t.action] ?? ACTION_COLORS.PASS
          return (
            <div key={t.name} className="spotlight-card">
              <span className="action-tag" style={{ background: ac.bg, color: ac.color }}>
                {t.action}
              </span>
              <h3 style={{ fontFamily: 'Fraunces, serif', fontSize: '1.4rem', margin: '0.4rem 0 0.2rem' }}>
                {t.name}
              </h3>
              <p style={{ fontSize: '0.82rem', color: 'var(--muted)', textTransform: 'uppercase', letterSpacing: '0.12em' }}>
                {t.category}
              </p>
              <p style={{ marginTop: '0.6rem', fontSize: '0.88rem', color: 'var(--muted)', lineHeight: 1.6 }}>
                {t.top_evidence || 'No evidence snippet available.'}
              </p>
              <div style={{ marginTop: 'auto', paddingTop: '0.8rem', display: 'flex', gap: '1rem' }}>
                <div>
                  <p style={{ fontSize: '0.72rem', textTransform: 'uppercase', letterSpacing: '0.18em', color: 'var(--muted)' }}>Score</p>
                  <p style={{ fontFamily: 'Fraunces, serif', fontSize: '1.6rem', lineHeight: 1 }}>{(t.composite_score ?? 0).toFixed(0)}</p>
                </div>
                <div>
                  <p style={{ fontSize: '0.72rem', textTransform: 'uppercase', letterSpacing: '0.18em', color: 'var(--muted)' }}>POP Fit</p>
                  <p style={{ fontFamily: 'Fraunces, serif', fontSize: '1.6rem', lineHeight: 1 }}>{(t.pop_fit_score ?? 0).toFixed(0)}</p>
                </div>
              </div>
            </div>
          )
        })}
      </div>
    </>
  )
}
