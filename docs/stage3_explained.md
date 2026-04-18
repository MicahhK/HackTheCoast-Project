# Stage 3 Explained — How Scoring & Ranking Works

This document explains what `scoring.py` does in plain terms: how each compliance check works, how scores are calculated, what drives the final ranking, and how to read the output.

---

## The Problem Stage 3 Solves

Stage 2 gives us 18 normalized trends with metrics like growth rate, recency, and competition density — but no actionable answer. Stage 3 answers two questions POP's buyers actually need:

1. **Can we even source this?** (compliance gates)
2. **Should we distribute it or develop our own version?** (action classifier)

Every trend gets a composite score, a market stage label, and a single action label. Buyers see a ranked list, not a pile of numbers.

---

## Step 1 — Compliance Gates (Run First, Hard Stops)

Three checks. Any failure zeros the composite score and forces action = PASS. The trend stays visible so buyers know *why* it was rejected — it doesn't just disappear.

### Gate 1: Shelf Life

POP's minimum is **12 months**. Refrigerated products, kombucha, and chips are auto-disqualified. The format string from the ingredient catalog (e.g. `"instant powder"`, `"chewy candy"`) is looked up in a table:

```
instant powder        → 36 months  ✅
dry tea               → 36 months  ✅
chewy candy           → 24 months  ✅
shelf-stable beverage → 18 months  ✅
chips/crackers        → 9 months   ❌ BLOCKED
kombucha              → 2 months   ❌ BLOCKED
```

**Real example:** Tempeh format is `"chips/crackers"` → 9 months → blocked. Even though Tempeh had strong base growth, POP can't carry it.

### Gate 2: FDA Ingredients

The trend's `ingredients` list is cross-referenced against POP's FDA table. Two outcomes:

- **Blocked** (banned/restricted): `fda_blocked = True`, composite zeroed. Examples: CBD, Ephedra, Delta-8 THC, Psilocybin, Tianeptine, Red Yeast Rice.
- **Watch** (advisory flagged): `fda_watch` list populated, trend **not blocked**. Buyer judgment required. Examples: Kratom, Kava, NMN, Colloidal Silver.

Matching is substring-based — `"ephedrine hydrochloride"` catches `"ephedrine"`, `"cbd oil"` catches `"cbd"`. This is intentionally conservative.

### Gate 3: Country Trade Risk

Each trend has a `primary_source_country`. That country's risk score is looked up (0.0 = no risk, 1.0 = sanctioned). Score > 0.60 blocks the trend.

```
USA          → 0.00  ✅
Japan        → 0.15  ✅
Indonesia    → 0.30  ✅
India        → 0.35  ✅
Vietnam      → 0.45  ✅
China        → 0.85  ❌ BLOCKED (for new categories)
Russia       → 1.00  ❌ BLOCKED
```

**China exception:** POP already has an existing supply chain for organic teas sourced from China. Trends in the `organic_teas` category are exempt from the China block.

**Real example:** Reishi Mushroom Tea — format is dry tea (36 months, passes), no FDA issues, but `primary_source_country = China` → risk 0.85 > 0.60 → blocked.

---

## Step 2 — Signal Strength Score (0–100)

Measures how strong the market signal is, built entirely from Stage 2 data. Uses **six weighted factors**:

```
Signal Strength =
    35% × (min(growth_rate_pct, 200) / 200) × 100   ← velocity
  + 30% × recency_score × 100                        ← window still open?
  + 15% × (source_count / 5) × 100                  ← corroboration
  + 10% × (1 - competition_density) × 100            ← shelf opportunity
  +  5% × (avg_gt_interest / 100) × 100              ← absolute market size
  +  5% × (min(rising_query_count, 4) / 4) × 100    ← breakout sub-queries
```

### Why these weights?

| Factor | Weight | Reasoning |
|---|---|---|
| Growth rate | 35% | POP's core failure is missing the window. Velocity = "is the window still open" |
| Recency | 30% | Fast growth that started 3 years ago is less actionable than fast growth that started 3 months ago |
| Corroboration | 15% | A trend in Google Trends + Reddit + RSS is real. A single-source spike is noise |
| Competition density | 10% | Low competition alone isn't a reason to act — it modifies urgency |
| Market size | 5% | Absolute GT interest provides a viability floor — prevents acting on niche micro-signals |
| Rising boost | 5% | Rising sub-queries mean the trend is spawning sub-categories — the window is widening, not narrowing |

**Negative growth is treated as zero** — a declining trend gets no growth credit, but the recency score handles the "window closed" signal separately.

**Growth is capped at 200%** before normalizing. A 500% and a 300% trend are both exceptional — the cap prevents outliers from dominating.

**avg_gt_interest = None** defaults to 0.5 (neutral) for trends with no Google Trends data.

**rising_query_count is capped at 4** — each signal above 4 provides diminishing information about trend breadth.

---

## Step 3 — POP-Fit Score (0–100)

Measures how naturally this trend connects to POP's existing product lines and supply chains. A high POP-Fit means shorter time-to-market because POP already has the ingredients, suppliers, or product expertise.

**+30 points per matching POP line, capped at 100.**

The function returns both the score and a list of matched line names — both are stored in the output object and the CSV export.

POP's 5 proprietary lines and what matches them:

| Line | Matches if key_ingredients contains... |
|---|---|
| POP Ginger Chews | ginger, chew, candy, chewy |
| POP Ginger Honey Crystals | ginger, honey, turmeric, wellness shot, manuka |
| American Ginseng | ginseng, american ginseng, adaptogen, nootropic |
| POP Herbal Teas | herbal, tea, functional tea, reishi, mushroom, elderberry, immunity |
| POP Organic Teas | tea, matcha, latte powder, green tea, oolong |

**Example: Mushroom Coffee**
- key_ingredients: `["cordyceps", "mushroom", "coffee", "adaptogen"]`
- "adaptogen" matches American Ginseng (+30)
- "mushroom" matches POP Herbal Teas (+30)
- POP-Fit = **60**, matched_lines = `["American Ginseng", "POP Herbal Teas"]`

**Example: Collagen Peptides**
- key_ingredients: `["collagen", "beauty", "gut health"]`
- No keyword matches any POP line
- POP-Fit = **0**, matched_lines = `[]`

---

## Step 4 — Market Stage

Derived from `growth_rate_pct` and `recency_score`. Tells buyers where the trend is in its lifecycle.

| Stage | Criteria | Interpretation |
|---|---|---|
| **emerging** | growth ≥ 10% AND recency ≥ 0.45 | Window just opening — act now |
| **growing** | growth ≥ 0% AND recency ≥ 0.35 | Window open — healthy opportunity |
| **peaking** | growth ≥ -10% AND recency ≥ 0.30 | Window still technically open but slowing |
| **declining** | everything else | Window closing or closed |

This is applied before scoring — it's stored in the output as `market_stage` and exported in the CSV.

---

## Step 5 — Composite Score

```
Composite = 0.55 × Signal Strength + 0.45 × POP-Fit
```

If `compliance_ok == False` → `Composite = 0.0` (zeroed, kept visible)

The **55/45 split** puts market signal slightly ahead of fit. A trend with strong consumer demand but weak POP adjacency still outscores a perfect-fit ingredient with no market momentum. POP can always build supply chain; they can't manufacture consumer demand.

---

## Step 6 — Action Classification

Assigned after scoring. Compliance failures always force PASS.

| Action | Criteria |
|---|---|
| **BOTH** 🌟 | can_develop AND can_distribute — strongest opportunities |
| **DEVELOP** 🔨 | POP-Fit ≥ 50 AND recency ≥ 0.30 (window still open) |
| **DISTRIBUTE** 📦 | Category in POP's distributed portfolio OR competition_density < 0.6, AND growth ≥ 0 |
| **PASS** — | None of the above, or compliance failed |

**DEVELOP** means: POP should create a proprietary product using this ingredient — add it to Ginger Chews, create a new tea blend, extend Ginger Honey Crystals.

**DISTRIBUTE** means: find an existing branded product in this category and add it to POP's distribution portfolio.

**The recency gate on DEVELOP (≥ 0.30):** If a trend is declining, it's too late to develop. You'd launch into a fading market. You can still distribute an established product in a declining category, but you can't afford the R&D cycle for a new one.

---

## Step 7 — CSV Export

`export_to_csv(scored_trends, filepath)` flattens the output into an Excel-compatible file with 23 columns ordered for buyer readability:

```
action, composite_score, name, category, market_stage,
growth_rate_pct, recency_score, competition_density,
signal_strength, pop_fit_score, pop_line_matches,
compliance_ok, shelf_life_months, fda_watch, trade_risk_score,
sources, source_count, avg_gt_interest, rising_query_count,
primary_source_country, format, compliance_note, top_evidence
```

`pop_line_matches` is serialized as a comma-separated string. `top_evidence` contains the first 100 characters of each of the top 3 evidence snippets, separated by ` || `.

---

## Reading the Live Output

```
Trend                    Score  Stage       Action       Compliance
─────────────────────────────────────────────────────────────────────
Matcha Mushroom Latte    41.0   emerging    🌟 BOTH       ✅  36mo | FDA clear | risk 0.15
Turmeric Ginger Latte    40.4   growing     🌟 BOTH       ✅  36mo | FDA clear | risk 0.35
Mushroom Coffee          39.2   growing     🌟 BOTH       ✅  36mo | FDA clear | risk 0.00
Ginger Shot              37.4   growing     🔨 DEVELOP    ✅  18mo | FDA clear | risk 0.00
Peanut Butter Powder     33.6   growing     📦 DISTRIBUTE ✅  36mo | FDA clear | risk 0.00
Tempeh                    0.0   growing     — PASS       ❌  9mo < 12mo minimum
Reishi Mushroom Tea       0.0   peaking     — PASS       ❌  risk 0.85 > 0.60 threshold
```

**What to look for:**

- **BOTH with emerging stage** = highest-value opportunities. Strong demand signal, window just opening, and POP adjacency exists.
- **DEVELOP with rising_query_count > 0** = trend spawning sub-categories, window is wide open. Act now.
- **DISTRIBUTE with high competition_density** = shelf is crowded but demand is proven. Find the best product in the category.
- **PASS due to compliance** = blocked for a specific rule. Check the note — some blocks (shelf life) might be solved by a different product format.

---

## Known Limitations

1. **Country risk is single-source.** A product with mixed sourcing (e.g. ingredients from both India and Vietnam) only gets checked against the `primary_source_country`. Multi-country sourcing isn't modeled yet.

2. **POP-Fit is keyword adjacency only.** It doesn't account for production complexity (adding a mushroom extract to a ginger chew is different from launching an entirely new supplement line).

3. **Competition density defaults to 0.5 when Amazon is unavailable.** This happens when Amazon rate-limits or changes their HTML. Everything without Amazon data gets the same neutral density.

---

## Running Tests

```bash
source venv/bin/activate
pytest tests/test_stage3.py -v   # 82 tests — Stage 3 unit + integration
pytest tests/ -v                  # 127 tests — full pipeline (Stage 2 + 3)
```
