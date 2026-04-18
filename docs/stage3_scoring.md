# Stage 3 — Scoring & Ranking (`scoring.py`)

Takes normalized trend objects from Stage 2, applies POP's hard constraints, scores every trend, and classifies each one as DISTRIBUTE / DEVELOP / BOTH / PASS.

---

## Status: ✅ Built

See [stage3_explained.md](stage3_explained.md) for a plain-English walkthrough.

---

## Input

List of normalized trend objects from `core_discovery.normalize()`:

```python
[
    {
        "name": "Lion's Mane Mushroom",
        "category": "functional food",
        "format": "instant powder",
        "key_ingredients": ["lion's mane", "mushroom", "nootropic"],
        "ingredients": ["lion's mane mushroom extract", "coffee", "chaga"],
        "primary_source_country": "USA",
        "growth_rate_pct": 400,
        "recency_score": 0.83,
        "competition_density": 0.50,
        "source_count": 2,
        "signal_count": 6,
        "sources": ["google_trends", "rss"],
        "evidence": [...],
    },
    ...
]
```

---

## Output

Same list with scoring fields added, sorted by `composite_score` descending:

```python
{
    # All Stage 2 fields, plus:
    "shelf_life_ok":        bool,   # passes 12-month minimum
    "fda_blocked":          bool,   # contains banned ingredient
    "fda_watch":            list,   # watch-list ingredients present (not blocked)
    "trade_risk_score":     float,  # 0.0–1.0 from country risk table
    "trade_risk_ok":        bool,   # risk <= 0.60
    "compliance_ok":        bool,   # shelf_life_ok AND NOT fda_blocked AND trade_risk_ok

    "signal_strength":      float,  # 0–100 weighted score
    "pop_fit_score":        int,    # 0–100 adjacency to POP's lines
    "pop_line_matches":     list,   # display names of matched POP lines
    "market_stage":         str,    # "emerging" | "growing" | "peaking" | "declining"
    "composite_score":      float,  # 0–100 final score (zeroed if compliance fails)
    "action":               str,    # "DISTRIBUTE" | "DEVELOP" | "BOTH" | "PASS"
    "compliance_note":      str,    # human-readable reason if blocked
}
```

---

## Hard Constraint Checks

These run first. A single failure zeros the composite score.

### 1. Shelf Life

Minimum 12 months. Format → shelf life mapping (from `pop_data.py`):

| Format | Months | Eligible? |
|---|---|---|
| Kombucha | 2 | ❌ NO |
| Fresh/refrigerated | <2 | ❌ NO |
| Chips/crackers | 9 | ❌ NO |
| Snack bar | 12 | ✅ Borderline |
| Chewy candy | 24 | ✅ YES |
| Chocolate | 18 | ✅ YES |
| Dry tea | 36 | ✅ YES |
| Instant powder | 36 | ✅ YES |
| Supplement/capsule | 36 | ✅ YES |
| Shelf-stable beverage | 18 | ✅ YES |
| Topical ointment | 60 | ✅ YES |

### 2. FDA Ingredients

Cross-reference `trend["ingredients"]` against the FDA restricted list:

| Ingredient | Status | Action |
|---|---|---|
| CBD | restricted | `fda_blocked = True` |
| Ephedra | banned | `fda_blocked = True` |
| Delta-8 THC / Cannabis | restricted | `fda_blocked = True` |
| Psilocybin | banned | `fda_blocked = True` |
| Tianeptine | banned | `fda_blocked = True` |
| Raw milk | restricted | `fda_blocked = True` |
| Red yeast rice (high monacolin K) | restricted | `fda_blocked = True` |
| Kratom | watch | add to `fda_watch`, do not block |
| Kava | watch | add to `fda_watch`, do not block |
| NMN | watch | add to `fda_watch`, do not block |
| Colloidal silver | watch | add to `fda_watch`, do not block |

### 3. Country Trade Risk

Cross-reference `trend["primary_source_country"]` against the risk table. Score > 0.60 blocks the trend.

| Country | Risk Score |
|---|---|
| USA | 0.00 |
| Japan | 0.15 |
| South Korea | 0.15 |
| Indonesia | 0.30 |
| Thailand | 0.35 |
| India | 0.35 |
| Vietnam | 0.45 |
| China | 0.85 ← blocks new categories |
| Russia / Iran / North Korea | 1.00 |

**Exception:** China risk can be overridden for `organic_teas` category — POP has an existing supply chain there.

---

## Signal Strength Score (0–100)

Weighted composite of Stage 2 metrics (six factors, weights sum to 1.0):

| Factor | Weight | Calculation |
|---|---|---|
| Growth Rate | 35% | `min(growth_rate_pct, 200) / 200 × 100` |
| Recency | 30% | `recency_score × 100` |
| Cross-source corroboration | 15% | `(source_count / 5) × 100` (5 = max sources) |
| Competition density (inverse) | 10% | `(1 - competition_density) × 100` |
| Market size | 5% | `(avg_gt_interest / 100) × 100`; None → 0.5 neutral |
| Rising boost | 5% | `(min(rising_query_count, 4) / 4) × 100` |

```python
signal_strength = (
    0.35 * min(growth_rate_pct, 200) / 200 * 100 +
    0.30 * recency_score * 100 +
    0.15 * (source_count / 5) * 100 +
    0.10 * (1 - competition_density) * 100 +
    0.05 * (avg_gt_interest / 100) * 100 +   # None → 0.5
    0.05 * (min(rising_query_count, 4) / 4) * 100
)
```

> **Why these weights?** Growth (35%) and recency (30%) are highest because POP's core failure is missing the trend window. Corroboration (15%) guards against single-source noise. Competition density (10%) is lowest because an uncrowded shelf alone isn't actionable. Market size (5%) provides a viability floor. Rising boost (5%) flags trends spawning sub-categories — a widening window.
>
> These weights are custom-designed for POP's problem, not a published industry standard. SPINS and Nielsen use similar multi-factor velocity models but keep their exact formulas proprietary.

---

## POP-Fit Score (0–100)

Measures how adjacent the trend is to POP's existing supply chains and product lines.

**+30 points per matching line, capped at 100.**

POP's 5 proprietary lines and their key ingredients:

| Line | Key Ingredients | Dev Angle |
|---|---|---|
| POP Ginger Chews | ginger | Add adaptogens, turmeric, mushroom to chew format |
| POP Ginger Honey Crystals | ginger, honey, turmeric | Wellness shots (elderberry, manuka, ACV) |
| American Ginseng | american ginseng | Co-formulation with any adaptogen trend |
| POP Herbal Teas | herbal blend | Extend to trending health concerns (metabolic, sleep, cognitive) |
| POP Organic Teas | tea | Latte powders and flavored teas via China supply chain |

```python
pop_lines = {
    "ginger_chews":           ["ginger", "chew", "candy"],
    "ginger_honey_crystals":  ["ginger", "honey", "turmeric", "wellness shot"],
    "american_ginseng":       ["ginseng", "american ginseng", "adaptogen"],
    "functional_herbal_teas": ["herbal", "tea", "functional tea"],
    "organic_teas":           ["tea", "matcha", "latte powder"],
}

score = 0
for line, keywords in pop_lines.items():
    if any(kw in trend["key_ingredients"] for kw in keywords):
        score += 30
pop_fit_score = min(score, 100)
```

**POP's asymmetric advantage:** Products established in SE Asia but unknown in the U.S. → high POP-Fit (existing sourcing relationships) + low competition density (nobody's there yet) = highest-value DEVELOP candidates.

---

## Composite Score

```python
composite_score = 0.55 * signal_strength + 0.45 * pop_fit_score
```

**If `compliance_ok == False`:** `composite_score = 0` — trend is zeroed but **kept visible** in output so buyers see *why* it was rejected.

The 55/45 split prioritizes market signal over fit. A red-hot trend with weak POP adjacency still outscores a perfect-fit ingredient with no momentum.

---

## Action Classification

Applied after scoring:

| Action | Criteria |
|---|---|
| **DEVELOP** | `pop_fit_score >= 50` AND existing adjacent ingredient or supply chain |
| **DISTRIBUTE** | Category matches POP's distributed portfolio OR `competition_density < 0.6` |
| **BOTH** | Both DEVELOP and DISTRIBUTE criteria met — strongest opportunities |
| **PASS** | Weak fit, compliance blocked, or trend window already closed |

---

## Implementation Checklist

Build `scoring.py` with these functions:

```python
def check_shelf_life(trend) -> tuple[bool, int, str]
def check_fda_ingredients(trend) -> tuple[bool, list, str]
def check_trade_risk(trend) -> tuple[bool, float, str]
def compute_signal_strength(trend) -> float
def compute_pop_fit(trend) -> tuple[int, list[str]]   # (score, matched_line_names)
def compute_market_stage(trend) -> str
def classify_action(trend, pop_fit_score, compliance_ok) -> str
def score(trends) -> list          # main function — adds all scoring fields, sorts output
def export_to_csv(scored_trends, filepath) -> pd.DataFrame
```

Reference data lives in `pop_data.py` (not yet built — see below).

---

## Dependency: `pop_data.py` (not yet built)

`scoring.py` needs `pop_data.py` to provide:

```python
SHELF_LIFE_TABLE   # format -> months dict
FDA_RESTRICTED     # ingredient -> "banned" | "restricted" | "watch" dict
COUNTRY_RISK       # country -> float (0.0–1.0) dict
POP_LINES          # line key -> {"display_name", "keywords", "dev_angle"} dict
```

Build `pop_data.py` before implementing `scoring.py`.

---

## Running Stage 3

```bash
source venv/bin/activate

# Once scoring.py and pop_data.py are built:
python scoring.py
```

**Expected output:**
```
Trend                    Score  Action     Compliance
-----------------------------------------------------------
Mushroom Coffee          78.4   BOTH       ✅ Clear
Lion's Mane Mushroom     71.2   DEVELOP    ✅ Clear
Ginger Shot              68.9   DEVELOP    ✅ Clear
Tempeh                   42.1   PASS       ❌ Shelf life: 9mo < 12mo min
Reishi Mushroom Tea      38.5   DISTRIBUTE ⚠️  Watch: source country China (risk 0.85)
...
```

---

## What the UI Does with These Results

`app.py` (Stage 4) reads the scored list and renders:
- Sidebar filters (category, action, compliance toggle)
- Trend cards with score, evidence snippets, and compliance status
- CSV export for POP's buying team
