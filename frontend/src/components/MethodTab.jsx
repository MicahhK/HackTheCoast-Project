const signalFactors = [
  {
    label: 'Growth Rate',
    weight: 35,
    note: 'Measures whether interest is accelerating in a sustained way.',
  },
  {
    label: 'Recency',
    weight: 30,
    note: 'Rewards trends whose window is still opening rather than closing.',
  },
  {
    label: 'Cross-Source Confirmation',
    weight: 15,
    note: 'Boosts terms that show up across search, retail, and trade sources.',
  },
  {
    label: 'Competition',
    weight: 10,
    note: 'Favors products with shelf space still available.',
  },
  {
    label: 'Market Size',
    weight: 5,
    note: 'Prevents tiny niches from outranking viable consumer demand.',
  },
  {
    label: 'Rising Queries',
    weight: 5,
    note: 'Captures breakout sub-terms that suggest a trend is branching.',
  },
]

const complianceGates = [
  {
    title: 'Shelf Life',
    detail: 'Products below 12 months are blocked before scoring.',
  },
  {
    title: 'FDA Ingredients',
    detail: 'Banned or restricted ingredients force the final score to zero.',
  },
  {
    title: 'Trade Risk',
    detail: 'Source-country risk above 0.60 blocks new-category sourcing.',
  },
]

const actionRules = [
  {
    label: 'Best Opportunity',
    code: 'BOTH',
    detail: 'Strong enough to source now and credible enough to develop into a POP-owned product.',
  },
  {
    label: 'Source a Product',
    code: 'DISTRIBUTE',
    detail: 'Best move is to add an outside product to POP’s distribution portfolio.',
  },
  {
    label: 'Develop a Product',
    code: 'DEVELOP',
    detail: 'Best move is to build a POP product using an adjacent ingredient or format.',
  },
  {
    label: 'Watchlist',
    code: 'PASS',
    detail: 'Too weak, too late, or blocked by compliance.',
  },
]

export default function MethodTab() {
  return (
    <div className="method-section fade-up" style={{ animationDelay: '0.05s' }}>
      <p className="method-eyebrow">Analyst View</p>
      <h2 className="method-title">How We Score</h2>

      <div className="method-intro">
        <p className="method-lead">
          Every trend is scored on market signal, POP fit, and compliance risk.
          The goal is simple: surface ideas POP can act on early, not just ideas that look noisy online.
        </p>
        <div className="method-formula">
          <div className="method-formula-kicker">Composite Formula</div>
          <div className="method-formula-row">
            <span>55% Signal Strength</span>
            <span className="method-formula-plus">+</span>
            <span>45% POP Fit</span>
          </div>
          <div className="method-formula-note">If a compliance gate fails, the score is forced to 0.</div>
        </div>
      </div>

      <div className="method-pillars">
        <div className="method-pillar-card">
          <div className="method-pillar-title">1. Signal Strength</div>
          <p className="method-pillar-copy">
            Asks whether the market is moving in a real, sustained way.
          </p>
        </div>
        <div className="method-pillar-card">
          <div className="method-pillar-title">2. POP Fit</div>
          <p className="method-pillar-copy">
            Asks whether POP can move quickly using product lines and supply chains it already knows.
          </p>
        </div>
        <div className="method-pillar-card method-pillar-alert">
          <div className="method-pillar-title">3. Compliance Gates</div>
          <p className="method-pillar-copy">
            Asks whether the opportunity is viable at all under POP’s shelf life, FDA, and trade rules.
          </p>
        </div>
      </div>

      <section className="method-block">
        <div className="method-block-head">
          <h3>Signal Strength Breakdown</h3>
          <p>Analysts can see exactly which market factors drive the score.</p>
        </div>
        <div className="factor-list">
          {signalFactors.map((factor) => (
            <div key={factor.label} className="factor-row">
              <div className="factor-copy">
                <div className="factor-label">{factor.label}</div>
                <div className="factor-note">{factor.note}</div>
              </div>
              <div className="factor-bar-wrap">
                <div className="factor-bar">
                  <div className="factor-bar-fill" style={{ width: `${factor.weight}%` }} />
                </div>
                <div className="factor-weight">{factor.weight}%</div>
              </div>
            </div>
          ))}
        </div>
      </section>

      <section className="method-grid">
        <div className="method-panel">
          <div className="method-panel-kicker">POP Fit</div>
          <h3>Why POP Fit Matters</h3>
          <p>
            POP Fit rewards trends that match the company’s existing strengths:
            ginger chews, ginger honey crystals, American ginseng, herbal teas, and organic teas.
          </p>
          <ul>
            <li>Each matching POP line adds 30 points.</li>
            <li>The score is capped at 100.</li>
            <li>High POP Fit means faster action with lower operational friction.</li>
          </ul>
        </div>

        <div className="method-panel method-panel-danger">
          <div className="method-panel-kicker">Automatic Disqualifiers</div>
          <h3>Compliance Gates</h3>
          <div className="gate-list">
            {complianceGates.map((gate) => (
              <div key={gate.title} className="gate-card">
                <div className="gate-title">{gate.title}</div>
                <div className="gate-detail">{gate.detail}</div>
              </div>
            ))}
          </div>
        </div>
      </section>

      <section className="method-block">
        <div className="method-block-head">
          <h3>Worked Example</h3>
          <p>A single example makes the model easier to audit.</p>
        </div>
        <div className="example-card">
          <div className="example-top">
            <div>
              <div className="example-label">Example Trend</div>
              <div className="example-name">Mushroom Coffee</div>
            </div>
            <div className="example-score">
              <span className="example-score-num">40.5</span>
              <span className="example-score-caption">Composite</span>
            </div>
          </div>
          <div className="example-grid">
            <div className="example-metric">
              <span className="example-metric-key">Growth</span>
              <span className="example-metric-val">+8%</span>
            </div>
            <div className="example-metric">
              <span className="example-metric-key">Recency</span>
              <span className="example-metric-val">0.36</span>
            </div>
            <div className="example-metric">
              <span className="example-metric-key">Signal Strength</span>
              <span className="example-metric-val">24.5</span>
            </div>
            <div className="example-metric">
              <span className="example-metric-key">POP Fit</span>
              <span className="example-metric-val">60</span>
            </div>
            <div className="example-metric">
              <span className="example-metric-key">Compliance</span>
              <span className="example-metric-val">Clear</span>
            </div>
            <div className="example-metric">
              <span className="example-metric-key">Decision</span>
              <span className="example-metric-val">BOTH</span>
            </div>
          </div>
          <p className="example-note">
            Read this as: the trend has real signal, fits POP’s current lines, clears compliance,
            and supports both sourcing and proprietary development.
          </p>
        </div>
      </section>

      <section className="method-block">
        <div className="method-block-head">
          <h3>Action Labels</h3>
          <p>Final labels translate the model into a next step for buyers.</p>
        </div>
        <div className="action-rule-list">
          {actionRules.map((rule) => (
            <div key={rule.code} className="action-rule-card">
              <div className="action-rule-top">
                <span className="action-rule-name">{rule.label}</span>
                <span className="action-rule-code">{rule.code}</span>
              </div>
              <p>{rule.detail}</p>
            </div>
          ))}
        </div>
      </section>

      <section className="method-block method-data-note">
        <h3>Data Freshness</h3>
        <p>
          Google Trends data is cached for 24 hours to avoid rate limits.
          Analysts can use <strong>Refresh Data</strong> in the top bar to rerun the full scoring pass.
        </p>
      </section>
    </div>
  )
}
