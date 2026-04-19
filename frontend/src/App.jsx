import { useState, useEffect, useMemo, useCallback, useRef } from 'react'
import BuyerExport from './components/BuyerExport'
import MethodTab from './components/MethodTab'
import Sidebar from './components/Sidebar'

/* ── Evidence parser: turns raw pipeline strings into plain English ── */
function formatEvidence(raw) {
  if (!raw) return null
  const parts = raw.split('||').map(s => s.trim()).filter(Boolean)

  const risers = []
  let overallStat  = null
  let newsMention  = null

  for (const part of parts) {
    const rise = part.match(/rising query:\s*'([^']+)'\s*\+?([\d,]+)%/i)
    if (rise) { risers.push({ term: rise[1], pct: parseInt(rise[2].replace(/,/g, '')) }); continue }

    const avg = part.match(/avg interest=([\d.]+)\/100,\s*growth\s*([+-]?\d+)%/i)
    if (avg) { overallStat = { interest: parseFloat(avg[1]), growth: parseInt(avg[2]) }; continue }

    const news = part.match(/^([^:]+):\s*'(.+?)'/)
    if (news && !part.toLowerCase().startsWith('google'))
      newsMention = { source: news[1].trim(), title: news[2].replace(/\s*—\s*\S+$/, '').trim() }
  }

  const SOURCE_NAMES = {
    newhope: 'New Hope Network', fooddive: 'Food Dive',
    naturalproductsinsider: 'Natural Products Insider',
    foodnavigator: 'Food Navigator', nutritionaloutlook: 'Nutritional Outlook',
  }

  const lines = []

  if (newsMention) {
    const src   = SOURCE_NAMES[newsMention.source.toLowerCase()] ?? newsMention.source
    const title = newsMention.title

    // If the headline mentions a trade show / expo, surface that directly
    const expo = title.match(/(?:from |at |in )((?:Natural Products |)[A-Z][^'"]*(?:Expo|Show|Summit|Conference|Fair)[^'"]*\d{4})/i)
    if (expo) {
      lines.push(`Spotlighted at ${expo[1].trim()} (${src})`)
    } else {
      // Take the part after a colon if there is one; otherwise the whole title
      const display = (title.includes(':') ? title.split(':').slice(1).join(':').trim() : title)
      // Truncate cleanly at a word boundary
      const short = display.length > 65
        ? display.slice(0, 62).replace(/\s+\S*$/, '') + '…'
        : display
      lines.push(`${src}: ${short}`)
    }
  }

  if (risers.length > 0) {
    const top = [...risers].sort((a, b) => b.pct - a.pct)[0]
    lines.push(
      top.pct >= 1000
        ? `Searches for "${top.term}" are surging`
        : `Search interest in "${top.term}" up ${top.pct}%`
    )
  }

  if (overallStat && lines.length < 2) {
    const { interest, growth } = overallStat
    if (interest >= 60) {
      if (growth > 5) lines.push(`High consumer interest and still growing`)
      else if (growth < -5) lines.push(`High consumer interest, but momentum is cooling`)
      else lines.push(`High consumer interest with steady demand`)
    } else if (interest >= 25) {
      if (growth > 5) lines.push(`Moderate consumer interest with growing momentum`)
      else if (growth < -5) lines.push(`Moderate consumer interest, but momentum is fading`)
      else lines.push(`Moderate consumer interest with steady demand`)
    } else {
      if (growth > 10) lines.push(`Early-stage interest, but search activity is starting to climb`)
      else if (growth < -5) lines.push(`Low search interest and weakening momentum`)
      else if (lines.length === 0) lines.push(`Limited search demand so far`)
    }
  }

  return lines.slice(0, 3)
}

/* ── badge style by action ── */
function Badge({ action }) {
  const cls = {
    BOTH:       'badge badge-both',
    DISTRIBUTE: 'badge badge-distribute',
    DEVELOP:    'badge badge-develop',
    PASS:       'badge badge-pass',
  }[action] ?? 'badge badge-pass'

  const labels = { BOTH: '★ Best Opportunity', DISTRIBUTE: 'Distribute', DEVELOP: 'Develop', PASS: 'Watch' }
  return <span className={cls}>{labels[action] ?? action}</span>
}

/* ── growth tag ── */
function GrowthTag({ value }) {
  if (value == null) return null
  const cls  = value > 0 ? 'growth-tag growth-pos' : value < 0 ? 'growth-tag growth-neg' : 'growth-tag growth-flat'
  const text = value > 0 ? `↑ +${value}%` : value < 0 ? `↓ ${value}%` : '→ Stable'
  return <span className={cls}>{text}</span>
}

/* ─────────────────────────────────────────────
   Detail Modal
───────────────────────────────────────────── */
function DetailModal({ trend: t, onClose }) {
  // close on ESC
  useEffect(() => {
    const handler = e => { if (e.key === 'Escape') onClose() }
    window.addEventListener('keydown', handler)
    return () => window.removeEventListener('keydown', handler)
  }, [onClose])

  const popMatches = t.pop_line_matches && t.pop_line_matches !== '[]' ? t.pop_line_matches : null
  const complianceText = t.compliance_ok === false ? 'Blocked' : 'Clear'
  const tradeRisk = t.trade_risk_score != null
    ? t.trade_risk_score <= 0.2 ? 'Low' : t.trade_risk_score <= 0.5 ? 'Moderate' : 'High'
    : null

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal" onClick={e => e.stopPropagation()}>
        <div className="modal-stripe" />
        <div className="modal-body">

          {/* Header */}
          <div className="modal-header">
            <div className="modal-title-block">
              <Badge action={t.action} />
              <div className="modal-name" style={{ marginTop: '0.6rem' }}>{t.name}</div>
              <div className="modal-sub">
                {[t.category, t.format, t.market_stage].filter(Boolean).join(' · ')}
              </div>
            </div>
            <button className="modal-close" onClick={onClose} aria-label="Close">✕</button>
          </div>

          {/* Scores */}
          <div className="modal-score-row">
            <div className="modal-score-card">
              <div className="modal-score-num" style={{ color: 'var(--red)' }}>
                {(t.composite_score ?? 0).toFixed(0)}
              </div>
              <div className="modal-score-label">Score</div>
            </div>
            <div className="modal-score-card">
              <div className="modal-score-num">{(t.pop_fit_score ?? 0).toFixed(0)}</div>
              <div className="modal-score-label">POP Fit</div>
            </div>
            <div className="modal-score-card">
              <div className="modal-score-num">
                {t.growth_rate_pct != null ? `${t.growth_rate_pct > 0 ? '+' : ''}${t.growth_rate_pct}%` : '—'}
              </div>
              <div className="modal-score-label">Growth</div>
            </div>
          </div>

          {/* Evidence */}
          {(() => { const ev = formatEvidence(t.top_evidence); return ev?.length ? (
            <>
              <div className="modal-section-label">Why It's Trending</div>
              <div className="modal-evidence">
                <ul className="modal-evidence-list">
                  {ev.map((item, index) => (
                    <li key={`${t.name}-evidence-${index}`} className="modal-evidence-item">
                      {item}
                    </li>
                  ))}
                </ul>
              </div>
            </>
          ) : null })()}

          <div className="modal-divider" />

          {/* Facts */}
          <div className="modal-section-label" style={{ marginBottom: '0.7rem' }}>Details</div>
          <div className="modal-facts">
            {t.primary_source_country && t.primary_source_country !== 'Unknown' && (
              <div className="modal-fact">
                <span className="modal-fact-key">Source Country</span>
                <span className="modal-fact-val">{t.primary_source_country}</span>
              </div>
            )}
            {t.shelf_life_months && (
              <div className="modal-fact">
                <span className="modal-fact-key">Shelf Life</span>
                <span className={t.shelf_life_months >= 12 ? 'modal-fact-ok' : 'modal-fact-bad'}>
                  {t.shelf_life_months} months {t.shelf_life_months >= 12 ? '✓' : '✗'}
                </span>
              </div>
            )}
            {t.format && (
              <div className="modal-fact">
                <span className="modal-fact-key">Format</span>
                <span className="modal-fact-val">{t.format}</span>
              </div>
            )}
            <div className="modal-fact">
              <span className="modal-fact-key">FDA Status</span>
              <span className={t.compliance_ok === false ? 'modal-fact-bad' : 'modal-fact-ok'}>
                {complianceText}
              </span>
            </div>
            {tradeRisk && (
              <div className="modal-fact">
                <span className="modal-fact-key">Trade Risk</span>
                <span className={tradeRisk === 'Low' ? 'modal-fact-ok' : tradeRisk === 'High' ? 'modal-fact-bad' : 'modal-fact-val'}>
                  {tradeRisk} ({t.trade_risk_score?.toFixed(2)})
                </span>
              </div>
            )}
            {t.source_count > 0 && (
              <div className="modal-fact">
                <span className="modal-fact-key">Sources</span>
                <span className="modal-fact-val">{t.source_count} data source{t.source_count !== 1 ? 's' : ''}</span>
              </div>
            )}
          </div>

          {/* POP Fit */}
          {popMatches && (
            <div className="modal-popfit">
              <strong>Fits POP's existing lines</strong>
              {popMatches}
            </div>
          )}

        </div>
      </div>
    </div>
  )
}

/* ─────────────────────────────────────────────
   Carousel
───────────────────────────────────────────── */
function Carousel({ items, renderItem }) {
  const trackRef = useRef(null)
  const [canPrev, setCanPrev] = useState(false)
  const [canNext, setCanNext] = useState(false)

  function checkArrows() {
    const el = trackRef.current
    if (!el) return
    setCanPrev(el.scrollLeft > 8)
    setCanNext(el.scrollLeft < el.scrollWidth - el.clientWidth - 8)
  }

  useEffect(() => { checkArrows() }, [items])

  function scrollBy(dir) {
    const el = trackRef.current
    if (!el) return
    const card = el.querySelector('.carousel-item')
    const step = (card ? card.offsetWidth + 16 : 260) * 4
    el.scrollBy({ left: dir * step, behavior: 'smooth' })
  }

  return (
    <div className="carousel-wrapper">
      <div className="carousel-controls">
        <button className="carousel-arrow" onClick={() => scrollBy(-1)} disabled={!canPrev} aria-label="Previous">‹</button>
        <button className="carousel-arrow" onClick={() => scrollBy(1)}  disabled={!canNext} aria-label="Next">›</button>
      </div>
      <div className="carousel-track" ref={trackRef} onScroll={checkArrows}>
        {items.map((item, i) => (
          <div key={i} className="carousel-item">{renderItem(item, i)}</div>
        ))}
      </div>
    </div>
  )
}

/* ─────────────────────────────────────────────
   Featured Card (BOTH)
───────────────────────────────────────────── */
function FeaturedCard({ trend: t, onClick }) {
  const score = t.composite_score ?? 0
  return (
    <div className="card featured-card" onClick={onClick}>
      <div className="featured-top-stripe" />
      <div className="featured-card-score">{score.toFixed(0)}<span className="featured-card-score-label">Score</span></div>
      <Badge action={t.action} />
      <div className="featured-name">{t.name}</div>
      <div className="featured-sub">
        <span className="sub-text">{t.category}</span>
        {t.market_stage && <span className="sub-text">{t.market_stage}</span>}
      </div>
      <GrowthTag value={t.growth_rate_pct} />
      <span className="card-hint">Click for details →</span>
    </div>
  )
}

/* ─────────────────────────────────────────────
   Action Card (DISTRIBUTE / DEVELOP)
───────────────────────────────────────────── */
function ActionCard({ trend: t, onClick, style }) {
  const growth = t.growth_rate_pct
  const growthCls = growth > 0 ? 'meta-pos' : growth < 0 ? 'meta-neg' : ''
  const score = t.composite_score ?? 0

  return (
    <div className="card action-card fade-up" style={style} onClick={onClick}>
      <div className="action-card-header">
        <div className="action-card-name">{t.name}</div>
        <div className="action-card-score">{score.toFixed(0)}</div>
      </div>
      <div className="meta-row">
        {growth != null && (
          <span className={`meta-pill ${growthCls}`}>
            {growth > 0 ? `+${growth}%` : growth === 0 ? 'Stable' : `${growth}%`}
          </span>
        )}
        {t.market_stage && <span className="meta-pill">{t.market_stage}</span>}
        {t.primary_source_country && t.primary_source_country !== 'Unknown' &&
          <span className="meta-pill">{t.primary_source_country}</span>}
        {t.format && <span className="meta-pill">{t.format}</span>}
      </div>
      <div className="score-bar-wrap">
        <div className="score-bar-labels">
          <span>Opportunity score</span>
          <span>{score.toFixed(0)} / 100</span>
        </div>
        <div className="score-bar">
          <div className="score-bar-fill" style={{ width: `${score}%` }} />
        </div>
      </div>
      <span className="card-hint">Click for details →</span>
    </div>
  )
}

/* ─────────────────────────────────────────────
   Watch Card (PASS)
───────────────────────────────────────────── */
function WatchCard({ trend: t, onClick, style }) {
  const reason = t.market_stage === 'saturated' ? 'Market too crowded'
    : t.market_stage === 'late'   ? 'Trend window closing'
    : t.compliance_ok === false   ? 'Compliance issue'
    : 'Monitor — weak signal'
  const score = t.composite_score ?? 0

  return (
    <div className="card watch-card fade-up" style={style} onClick={onClick}>
      <div className="watch-card-top">
        <div className="watch-name">{t.name}</div>
        <div className="watch-score">{score.toFixed(0)}</div>
      </div>
      <div className="watch-reason">{reason}</div>
    </div>
  )
}

/* ─────────────────────────────────────────────
   App
───────────────────────────────────────────── */
export default function App() {
  const [trends,        setTrends]        = useState([])
  const [loading,       setLoading]       = useState(true)
  const [refreshing,    setRefreshing]    = useState(false)
  const [activeTab,     setActiveTab]     = useState('trends')
  const [error,         setError]         = useState(null)
  const [compliantOnly, setCompliantOnly] = useState(false)
  const [selected,      setSelected]      = useState(null)
  const [searchQuery,   setSearchQuery]   = useState('')
  const [filterActions, setFilterActions] = useState([])
  const [filterCategories, setFilterCategories] = useState([])
  const [filterStages, setFilterStages] = useState([])
  const [minScore,      setMinScore]      = useState(0)
  const [sortBy,        setSortBy]        = useState('composite_score')
  const [filtersInitialized, setFiltersInitialized] = useState(false)
  const [filtersOpen,   setFiltersOpen]   = useState(false)

  useEffect(() => {
    if (!filtersOpen) return
    const handler = e => { if (e.key === 'Escape') setFiltersOpen(false) }
    window.addEventListener('keydown', handler)
    return () => window.removeEventListener('keydown', handler)
  }, [filtersOpen])

  const openModal  = useCallback(t  => setSelected(t),    [])
  const closeModal = useCallback(() => setSelected(null), [])

  useEffect(() => {
    fetch('/api/trends')
      .then(r => r.json())
      .then(d => setTrends(Array.isArray(d) ? d : []))
      .catch(e => setError(e.message))
      .finally(() => setLoading(false))
  }, [])

  async function handleRefresh() {
    try {
      setRefreshing(true); setError(null)
      await fetch('/api/refresh', { method: 'POST' })
      const d = await fetch('/api/trends').then(r => r.json())
      setTrends(Array.isArray(d) ? d : [])
    } catch (e) { setError(e.message) }
    finally     { setRefreshing(false) }
  }

  const allActions = useMemo(
    () => [...new Set(trends.map(t => t.action).filter(Boolean))],
    [trends],
  )
  const allCategories = useMemo(
    () => [...new Set(trends.map(t => t.category).filter(Boolean))].sort(),
    [trends],
  )
  const allStages = useMemo(
    () => [...new Set(trends.map(t => t.market_stage).filter(Boolean))],
    [trends],
  )

  useEffect(() => {
    if (!filtersInitialized && trends.length > 0) {
      setFilterActions(allActions)
      setFilterCategories(allCategories)
      setFilterStages(allStages)
      setFiltersInitialized(true)
    }
  }, [filtersInitialized, trends, allActions, allCategories, allStages])

  const filtered = useMemo(() => {
    const query = searchQuery.trim().toLowerCase()
    const searched = trends.filter((t) => {
      if (compliantOnly && t.compliance_ok === false) return false
      if (filterActions.length > 0 && !filterActions.includes(t.action)) return false
      if (filterCategories.length > 0 && !filterCategories.includes(t.category)) return false
      if (filterStages.length > 0 && !filterStages.includes(t.market_stage)) return false
      if ((t.composite_score ?? 0) < minScore) return false
      if (!query) return true

      const haystack = [
        t.name,
        t.category,
        t.format,
        t.primary_source_country,
        t.action,
        t.market_stage,
        t.top_evidence,
      ]
        .filter(Boolean)
        .join(' ')
        .toLowerCase()

      return haystack.includes(query)
    })

    return [...searched].sort((a, b) => (b[sortBy] ?? 0) - (a[sortBy] ?? 0))
  }, [
    trends,
    compliantOnly,
    filterActions,
    filterCategories,
    filterStages,
    minScore,
    searchQuery,
    sortBy,
  ])

  const featured   = useMemo(() => filtered.filter(t => t.action === 'BOTH')       .sort((a,b) => b.composite_score - a.composite_score), [filtered])
  const distribute = useMemo(() => filtered.filter(t => t.action === 'DISTRIBUTE') .sort((a,b) => b.composite_score - a.composite_score), [filtered])
  const develop    = useMemo(() => filtered.filter(t => t.action === 'DEVELOP')    .sort((a,b) => b.composite_score - a.composite_score), [filtered])
  const watchList  = useMemo(() => filtered.filter(t => t.action === 'PASS')       .sort((a,b) => b.composite_score - a.composite_score), [filtered])
  const actionable = featured.length + distribute.length + develop.length
  const topScore   = filtered.length ? Math.max(...filtered.map(t => t.composite_score ?? 0)) : 0

  return (
    <>
      {/* Nav */}
      <nav className="topbar">
        <div className="topbar-brand">
          <div className="topbar-logo">P</div>
          <span className="topbar-wordmark">POP <em>Trend</em> Intelligence</span>
        </div>
        <div className="topbar-controls">
          <div className="topbar-tabs">
            {[['trends','Trends'],['export','Export'],['method','How We Score']].map(([id,label]) => (
              <button key={id} className={`topbar-tab${activeTab===id?' active':''}`} onClick={()=>setActiveTab(id)}>{label}</button>
            ))}
          </div>
          {activeTab === 'trends' && (
            <button
              className="filters-btn"
              onClick={() => setFiltersOpen(true)}
              aria-label="Open filters"
            >
              <span className="filters-btn-icon" aria-hidden>☰</span>
              Filters
            </button>
          )}
          <button className="refresh-btn" onClick={handleRefresh} disabled={refreshing||loading}>
            {refreshing ? 'Refreshing…' : 'Refresh Data'}
          </button>
        </div>
      </nav>

      <div className="page">
        {error && (
          <div className="error-bar">
            Backend unreachable — run <code>uvicorn api:app --reload</code> then refresh. ({error})
          </div>
        )}

        {activeTab === 'trends' && (
          <>
            {/* ── Hero ── */}
            <div className="hero">
              <div className="hero-eyebrow">
                <span className="hero-live-dot" />
                Prince of Peace Enterprises · April 2026
              </div>
              <h1 className="hero-title">Trend Intelligence<br />for CPG Buyers</h1>
              <p className="hero-desc">
                Automated market signal radar that scans Google Trends, trade publications,
                and social data to surface which food &amp; wellness trends POP should act on — and how.
                Every trend is scored against POP's shelf-life, FDA, and trade-risk requirements.
              </p>
              <div className="hero-nav">
                {[
                  { label: 'Best Opportunities', id: 'sec-best',   tone: 'best' },
                  { label: 'Source a Product',   id: 'sec-single', tone: 'source' },
                  { label: 'Develop a Product',  id: 'sec-single', tone: 'develop' },
                  { label: 'Watchlist',          id: 'sec-watch',  tone: 'watch' },
                ].map(({ label, id, tone }) => (
                  <button
                    key={label}
                    className={`hero-nav-btn hero-nav-${tone}`}
                    onClick={() => document.getElementById(id)?.scrollIntoView({ behavior: 'smooth', block: 'start' })}
                  >
                    <span className="hero-nav-label">{label}</span>
                  </button>
                ))}
              </div>

              <p className="hero-scroll-hint">↓ Scroll to explore</p>
            </div>

            {/* Stats */}
            {!loading && (
              <div className="summary-bar">
                {[
                  { label:'Signals Tracked',   value: filtered.length,     note:'Across all sources',         color: null },
                  { label:'Actionable Now',     value: actionable,           note:'Ready to distribute or build', color:'var(--red)' },
                  { label:'Best Opportunities', value: featured.length,      note:'Distribute AND develop',     color:'#111' },
                  { label:'Top Score',          value: topScore.toFixed(0),  note:'Out of 100',                 color: null },
                ].map(({ label, value, note, color }, i) => (
                  <div key={label} className="summary-stat fade-up" style={{ animationDelay:`${i*0.07}s` }}>
                    <div className="summary-stat-label">{label}</div>
                    <div className="summary-stat-value" style={color?{color}:{}}>{value}</div>
                    <div className="summary-stat-note">{note}</div>
                  </div>
                ))}
              </div>
            )}

            {loading ? <div className="loading-state">Fetching live market signals…</div> : (
              <div className="trends-main">
                  <div className="search-panel">
                    <div>
                      <div className="search-panel-kicker">Analyst Filters</div>
                      <div className="search-panel-title">Search and narrow the opportunity set.</div>
                    </div>
                    <div className="search-wrap">
                      <input
                        className="search-input"
                        type="search"
                        value={searchQuery}
                        onChange={(e) => setSearchQuery(e.target.value)}
                        placeholder="Search by trend, category, format, country, or action"
                      />
                    </div>
                  </div>

                  {filtered.length === 0 && (
                    <div className="empty-filter-state">
                      No trends match the current search and filter settings.
                    </div>
                  )}

                  {/* 01 Best Opportunities */}
                  {featured.length > 0 && (
                    <section className="section" id="sec-best">
                      <div className="section-header">
                        <span className="section-ordinal">01</span>
                        <h2 className="section-title">Best Opportunities</h2>
                        <span className="section-count-badge">{featured.length} trends</span>
                      </div>
                      <p className="section-desc">These are the strongest trends right now. POP could source them and also turn them into its own product.</p>
                      <Carousel
                        items={featured}
                        renderItem={(t) => <FeaturedCard trend={t} onClick={() => openModal(t)} />}
                      />
                    </section>
                  )}

                  {/* 02 Single-action — only render if at least one side has items */}
                  {(distribute.length > 0 || develop.length > 0) && (
                    <section className="section" id="sec-single">
                      <div className="section-header">
                        <span className="section-ordinal">02</span>
                        <h2 className="section-title">Single-Action Trends</h2>
                      </div>
                      <p className="section-desc">These trends point to one clear move: either bring in an outside product or build a new POP one.</p>

                      <div className={distribute.length > 0 && develop.length > 0 ? 'split-section' : undefined}>
                        {distribute.length > 0 && (
                          <div>
                            <div className="col-head col-distribute">
                              <span className="col-head-label">Source a Product</span>
                              <span className="col-head-count">{distribute.length} trends</span>
                            </div>
                            <p className="section-desc" style={{marginBottom:'1rem'}}>
                              Find an existing product that POP can start selling through its distribution network.
                            </p>
                            <div className="action-cards">
                              {distribute.map((t,i) => <ActionCard key={t.name} trend={t} onClick={()=>openModal(t)} style={{animationDelay:`${0.12+i*0.08}s`}} />)}
                            </div>
                          </div>
                        )}

                        {develop.length > 0 && (
                          <div>
                            <div className="col-head col-develop">
                              <span className="col-head-label">Develop a Product</span>
                              <span className="col-head-count">{develop.length} trends</span>
                            </div>
                            <p className="section-desc" style={{marginBottom:'1rem'}}>
                              Create a new POP product by extending lines the company already knows well.
                            </p>
                            <div className="action-cards">
                              {develop.map((t,i) => <ActionCard key={t.name} trend={t} onClick={()=>openModal(t)} style={{animationDelay:`${0.12+i*0.08}s`}} />)}
                            </div>
                          </div>
                        )}
                      </div>
                    </section>
                  )}

                  {/* 03 Watch List */}
                  {watchList.length > 0 && (
                    <section className="section" id="sec-watch">
                      <div className="section-header">
                        <span className="section-ordinal">03</span>
                        <h2 className="section-title">Watchlist</h2>
                        <span className="section-count-badge">{watchList.length} trends</span>
                      </div>
                      <p className="section-desc">Signal too weak, market too crowded, or doesn't fit POP's lines right now. Revisit next quarter.</p>
                      <div className="watch-grid">
                        {watchList.map((t,i) => <WatchCard key={t.name} trend={t} onClick={()=>openModal(t)} style={{animationDelay:`${0.1+i*0.05}s`}} />)}
                      </div>
                    </section>
                  )}
              </div>
            )}
          </>
        )}

        {activeTab === 'export' && <BuyerExport trends={filtered} />}
        {activeTab === 'method' && <MethodTab />}
      </div>

      {/* Detail Modal */}
      {selected && <DetailModal trend={selected} onClose={closeModal} />}

      {/* Filters Drawer */}
      {filtersOpen && (
        <div className="filter-drawer-overlay" onClick={() => setFiltersOpen(false)}>
          <div className="filter-drawer" onClick={e => e.stopPropagation()}>
            <button
              className="filter-drawer-close"
              onClick={() => setFiltersOpen(false)}
              aria-label="Close filters"
            >
              ✕
            </button>
            <Sidebar
              allActions={allActions}
              allCategories={allCategories}
              allStages={allStages}
              filterActions={filterActions}
              setFilterActions={setFilterActions}
              filterCategories={filterCategories}
              setFilterCategories={setFilterCategories}
              filterStages={filterStages}
              setFilterStages={setFilterStages}
              compliantOnly={compliantOnly}
              setCompliantOnly={setCompliantOnly}
              minScore={minScore}
              setMinScore={setMinScore}
              sortBy={sortBy}
              setSortBy={setSortBy}
              onRefresh={handleRefresh}
              refreshing={refreshing}
            />
          </div>
        </div>
      )}
    </>
  )
}
