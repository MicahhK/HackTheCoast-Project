const COLS = [
  ['name',               'Trend'],
  ['action',             'Action'],
  ['category',           'Category'],
  ['composite_score',    'Score'],
  ['pop_fit_score',      'POP Fit'],
  ['growth_rate_pct',    'Growth %'],
  ['market_stage',       'Stage'],
  ['format',             'Format'],
  ['primary_source_country', 'Country'],
  ['shelf_life_months',  'Shelf Life (mo)'],
  ['compliance_ok',      'Compliant'],
]

const BADGE = {
  BOTH:       { bg: 'rgba(192,85,32,0.10)',  color: '#c05520' },
  DISTRIBUTE: { bg: 'rgba(138,106,24,0.10)', color: '#8a6a18' },
  DEVELOP:    { bg: 'rgba(30,82,68,0.10)',   color: '#1e5244' },
  PASS:       { bg: 'rgba(106,48,64,0.08)',  color: '#6a3040' },
}

export default function BuyerExport({ trends }) {
  function downloadCSV() {
    const header = COLS.map(([, l]) => l).join(',')
    const rows   = trends.map(t =>
      COLS.map(([key]) => {
        const v = t[key]
        if (v == null) return ''
        const s = typeof v === 'number' ? v.toFixed(2) : String(v)
        return s.includes(',') ? `"${s}"` : s
      }).join(',')
    )
    const blob = new Blob([[header, ...rows].join('\n')], { type: 'text/csv' })
    const a    = Object.assign(document.createElement('a'), { href: URL.createObjectURL(blob), download: 'pop_trends.csv' })
    a.click(); URL.revokeObjectURL(a.href)
  }

  return (
    <div className="export-section fade-up" style={{ animationDelay: '0.05s' }}>
      <div className="export-head">
        <div>
          <p className="export-eyebrow">Buyer Export</p>
          <h2 className="export-title">{trends.length} Trends</h2>
        </div>
        <div className="dl-row">
          <button className="dl-btn primary" onClick={downloadCSV}>Download CSV</button>
          <a className="dl-btn secondary" href="/api/export/csv" download="pop_trends_full.csv">
            Full Export (API)
          </a>
        </div>
      </div>

      <div className="table-wrap">
        <table className="data-table">
          <thead>
            <tr>{COLS.map(([, l]) => <th key={l}>{l}</th>)}</tr>
          </thead>
          <tbody>
            {trends.map(t => {
              const badge = BADGE[t.action] ?? BADGE.PASS
              return (
                <tr key={t.name}>
                  {COLS.map(([key, label]) => {
                    const v = t[key]
                    if (key === 'action') return (
                      <td key={label}>
                        <span className="action-badge" style={{ background: badge.bg, color: badge.color }}>{v}</span>
                      </td>
                    )
                    if (key === 'composite_score' || key === 'pop_fit_score')
                      return <td key={label}>{v != null ? Number(v).toFixed(1) : '—'}</td>
                    if (key === 'growth_rate_pct')
                      return <td key={label} style={{ color: v > 0 ? 'var(--jade)' : v < 0 ? 'var(--wine)' : undefined, fontWeight: 600 }}>
                        {v != null ? (v > 0 ? `+${v}%` : `${v}%`) : '—'}
                      </td>
                    if (key === 'compliance_ok')
                      return <td key={label} style={{ color: v === false ? 'var(--wine)' : 'var(--jade)', fontWeight: 600 }}>
                        {v === false ? 'No' : 'Yes'}
                      </td>
                    return <td key={label}>{v != null ? String(v) : '—'}</td>
                  })}
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>
    </div>
  )
}
