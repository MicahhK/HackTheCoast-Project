export default function Sidebar({
  allActions, allCategories, allStages,
  filterActions, setFilterActions,
  filterCategories, setFilterCategories,
  filterStages, setFilterStages,
  compliantOnly, setCompliantOnly,
  minScore, setMinScore,
  sortBy, setSortBy,
  onRefresh, refreshing,
}) {
  function toggle(list, setList, val) {
    setList(list.includes(val) ? list.filter(x => x !== val) : [...list, val])
  }

  return (
    <aside className="sidebar">
      <h2>POP Intelligence</h2>

      <button className="refresh-btn" onClick={onRefresh} disabled={refreshing}>
        {refreshing ? 'Refreshing…' : 'Refresh Pipeline'}
      </button>

      <div className="sidebar-section">
        <p className="sidebar-label">Action</p>
        <div className="check-list">
          {allActions.map(a => (
            <label key={a} className="check-item">
              <input type="checkbox" checked={filterActions.includes(a)} onChange={() => toggle(filterActions, setFilterActions, a)} />
              {a}
            </label>
          ))}
        </div>
      </div>

      <div className="sidebar-section">
        <p className="sidebar-label">Category</p>
        <div className="check-list">
          {allCategories.map(c => (
            <label key={c} className="check-item">
              <input type="checkbox" checked={filterCategories.includes(c)} onChange={() => toggle(filterCategories, setFilterCategories, c)} />
              {c}
            </label>
          ))}
        </div>
      </div>

      <div className="sidebar-section">
        <p className="sidebar-label">Market Stage</p>
        <div className="check-list">
          {allStages.map(s => (
            <label key={s} className="check-item">
              <input type="checkbox" checked={filterStages.includes(s)} onChange={() => toggle(filterStages, setFilterStages, s)} />
              {s}
            </label>
          ))}
        </div>
      </div>

      <div className="sidebar-section">
        <p className="sidebar-label">Compliance</p>
        <label className="toggle-row">
          <input type="checkbox" checked={compliantOnly} onChange={e => setCompliantOnly(e.target.checked)} />
          Compliant only
        </label>
      </div>

      <div className="sidebar-section">
        <p className="sidebar-label">Min Score</p>
        <div className="slider-row">
          <input type="range" min={0} max={100} step={5} value={minScore} onChange={e => setMinScore(Number(e.target.value))} />
          <span className="slider-val">{minScore}</span>
        </div>
      </div>

      <div className="sidebar-section">
        <p className="sidebar-label">Sort By</p>
        <select className="select-ctrl" value={sortBy} onChange={e => setSortBy(e.target.value)}>
          <option value="composite_score">Composite Score</option>
          <option value="signal_strength">Signal Strength</option>
          <option value="pop_fit_score">POP Fit</option>
          <option value="growth_rate_pct">Growth Rate</option>
          <option value="recency_score">Recency</option>
        </select>
      </div>
    </aside>
  )
}
