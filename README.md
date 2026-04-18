# HackTheCoast 2026 — POP Trend Intelligence Tool
Product Discovery & Trend Intelligence for Prince of Peace Enterprises

---

## Quick Start

```bash
# Activate the virtual environment (all dependencies pre-installed)
source venv/bin/activate        # macOS/Linux
venv\Scripts\activate           # Windows

# Verify all sources are working
python debug_collectors.py

# Run Stage 1 (collect raw signals)
python collectors.py

# Run Stage 1 + Stage 2 (collect + normalize into trends)
python core_discovery.py
```

**First time setup** (if venv doesn't exist):
```bash
python3 -m venv venv
source venv/bin/activate
pip install streamlit pandas pytrends praw feedparser requests beautifulsoup4
pip install "urllib3<2.0.0"   # required — pytrends breaks with urllib3 >= 2.0
```

---

## Pipeline Overview

```
Stage 1              Stage 2                Stage 3
collectors.py  →  core_discovery.py  →  scoring.py  →  app.py (UI)
                        ↑
                  pop_data.py (catalog, FDA list, country risk)
```

---

## Stage 1 — Data Collection (`collectors.py`)

Pulls raw signals from five public sources. Each signal has the same schema:

```python
{
    "source":       str,   # which collector produced this
    "term":         str,   # ingredient or product name / raw title
    "signal_value": int,   # what "strength" means per source (see below)
    "snippet":      str,   # one human-readable evidence sentence
    "timestamp":    str,   # ISO 8601
    "metadata":     dict,  # source-specific extras
}
```

### Sources and Signal Values

| Source | `signal_value` meaning | Auth needed? | Status |
|---|---|---|---|
| **Google Trends** | % growth (last 4 weeks vs prior 12) | None | ✅ Working |
| **Reddit** | Post upvote score | `REDDIT_CLIENT_ID` + `REDDIT_CLIENT_SECRET` env vars | ⚠️ Needs creds |
| **RSS / Trade pubs** | 1 (presence — frequency counted in Stage 2) | None | ✅ Working |
| **Amazon Movers & Shakers** | Rank positions jumped (999 = previously unranked) | None | ✅ Working |
| **FDA GRAS Notices** | 1 (cleared = entering U.S. market) | None | ✅ Working |

### RSS Feeds

| Feed | Articles |
|---|---|
| Food Dive | ~10 |
| New Hope Network | ~50 |
| SPINS Insights | ~10 |

### Setting Up Reddit (optional but recommended)

1. Go to [reddit.com/prefs/apps](https://www.reddit.com/prefs/apps) → **create app** → select **script**
2. Export credentials in your terminal session:
   ```bash
   export REDDIT_CLIENT_ID=your_id
   export REDDIT_CLIENT_SECRET=your_secret
   ```
   On PowerShell:
   ```powershell
   $env:REDDIT_CLIENT_ID="your_id"
   $env:REDDIT_CLIENT_SECRET="your_secret"
   ```

---

## How We Analyze the Data

### Step 1 — Signal Normalization (Stage 2)

`core_discovery.py` scans every signal's `term` and `snippet` against an ingredient catalog of ~20 trend candidates. Each catalog entry defines:

- **Canonical name** (e.g., "Lion's Mane Mushroom")
- **Aliases** to match in raw text (e.g., "lions mane", "hericium", "lion's mane coffee")
- **Category** (functional food, asian specialty, adaptogen, etc.)
- **Format** (instant powder, chewy candy, supplement, etc.) — used for shelf-life check
- **Key ingredients** — used for POP-Fit scoring in Stage 3
- **Primary source country** — used for trade-risk check in Stage 3

A signal matches a trend if any alias appears in the signal's text. One signal can only match one trend entry (no double-counting).

### Step 2 — Signal Aggregation

For each matched trend, Stage 2 computes:

| Metric | How it's calculated |
|---|---|
| **Growth rate** | Max Google Trends growth % across matched signals; or Amazon rank-jump × 2 if no GT data |
| **Recency score (0–1)** | Maps average GT growth to a 0–1 window-open score: +200% → 1.0, flat → 0.5, declining → lower |
| **Competition density (0–1)** | Based on Amazon rank: rank #1 ≈ 0.95 (saturated), rank #30 ≈ 0.05 (wide open). No Amazon data → 0.5 |
| **Source count** | How many distinct sources (GT, Reddit, RSS, Amazon, FDA) flagged this trend — corroboration weight |

### Step 3 — Composite Scoring (Stage 3)

**Signal Strength Score** (0–100) — weighted from Stage 2 metrics:

| Factor | Weight | Rationale |
|---|---|---|
| Growth Rate | 40% | Highest weight because POP's core problem is missing the window — velocity is the most direct proxy for "is the window still open" |
| Recency | 35% | A fast-growing trend that started 3 years ago is less actionable than one that started 3 months ago |
| Cross-source corroboration | 15% | A signal appearing in Google Trends *and* Reddit *and* trade press is more likely real than a single-source spike. Academic research on information cascades supports corroboration as an early-trend amplifier |
| Competition density (inverse) | 10% | Lowest weight because low competition alone isn't a reason to act — it just modifies how urgently to move |

> **Note on weights:** These are custom-designed for POP's specific problem (early trend detection for a CPG distributor), not a published industry formula. SPINS, Nielsen, and Circana use similar multi-factor velocity models but their exact weights are proprietary. Google Trends defines its own "breakout" threshold at >5000% growth — we use that as a calibration anchor for signal_value caps.

**POP-Fit Score** (0–100) — keyword adjacency between trend ingredients and POP's 5 proprietary lines (Ginger Chews, Ginger Honey Crystals, American Ginseng, Herbal Teas, Organic Teas). **+30 points per matching line, capped at 100.**

This is intentionally simple: deeper ingredient overlap with POP's existing supply chain = faster time-to-market = more actionable opportunity.

**Composite Score** = `0.55 × Signal Strength + 0.45 × POP-Fit`

The 55/45 split prioritizes market signal over fit — a red-hot trend with weak POP adjacency still scores higher than a perfect-fit ingredient with no market momentum.

Compliance failures (banned FDA ingredients or trade risk > 0.60) **zero the composite score** but the trend stays visible so buyers know *why* it was rejected.

### Step 4 — Action Classification

| Action | When assigned |
|---|---|
| **DEVELOP** | POP-Fit ≥ 50 and adjacent ingredient/supply chain exists |
| **DISTRIBUTE** | Category matches POP's distributed portfolio or competition density < 0.6 |
| **BOTH** | Both criteria met — strongest opportunities |
| **PASS** | Weak fit, compliance blocked, or trend window already closed |

### Reading the Output

A high-value trend has:
- **High source count** — Google Trends + Reddit + RSS + Amazon all flagging it = real signal, not noise
- **Positive growth rate** — trend window is still open
- **High POP-Fit** — adjacent to POP's existing supply chains (faster time-to-market)
- **Low competition density** — shelf isn't crowded yet
- **No compliance flags** — FDA-clear ingredients, source country risk ≤ 0.60

### POP's Asymmetric Advantage

Products established in SE Asia but unknown in the U.S. show up in our data as:
- Low competition density (nobody's there yet on Amazon)
- Low Google Trends average interest (not mainstream)
- But **positive growth** (curve is starting to climb)

These are the highest-value DEVELOP candidates because POP already has authentic supply chain relationships that U.S. competitors don't.

### The Negative Growth / Rising Queries Signal

Some of the most actionable opportunities show **negative base growth but high rising query counts** — for example, Ginger Shot (-6% base growth, 4 rising sub-queries including "organic ginger shot" +130%) and Lion's Mane Mushroom (-5% base, rising queries like "lions mane supplement" +400%).

This pattern means: the broad trend is maturing, but specific variants and use cases are still early. For POP — who already makes Ginger Chews and Ginger Honey Crystals — a premium organic ginger shot format is a natural DEVELOP extension into a sub-category that's just opening, with no new supply chain required. The base market is proven; the variant window is still wide open.

### Live Output (April 2026)

```
Trend                   Score  Stage     Action       Compliance
────────────────────────────────────────────────────────────────────
Matcha Mushroom Latte    41.0  growing   🌟 BOTH       ✅  Matches POP Herbal Teas + Organic Teas
Mushroom Coffee          40.5  growing   🌟 BOTH       ✅  "mushroom coffee benefits" rising +3250%
Turmeric Ginger Latte    40.3  growing   🌟 BOTH       ✅  Direct adjacency to Ginger Chews line
Ginger Shot              40.0  peaking   🔨 DEVELOP    ✅  4 rising sub-queries despite -6% base
Lion's Mane Mushroom     39.5  peaking   🔨 DEVELOP    ✅  "lions mane supplement" rising +400%
Manuka Honey             38.8  growing   🌟 BOTH       ✅  New Zealand sourcing, low risk
Tempeh                    0.0  growing   — PASS       ❌  9mo shelf life < 12mo minimum
Reishi Mushroom Tea       0.0  peaking   — PASS       ❌  China trade risk 0.85, no exemption
```

---

## Hard Constraints (Non-Negotiable)

| Constraint | Rule |
|---|---|
| Shelf life | Minimum **12 months** — refrigerated/fresh products auto-disqualified |
| FDA ingredients | No banned ingredients (CBD, Kratom, Ephedra, Delta-8, etc.) — watch-list items flagged but not blocked |
| Country trade risk | Max score **0.60** — blocks China-only sourcing for new categories |

---

## Google Trends Cache

Google Trends is rate-limited. Results are cached for 24 hours in `gt_cache.json`.

- Delete `gt_cache.json` to force a fresh fetch (triggers rate-limit delays of ~2s/batch)
- Cache is automatically refreshed if older than 24 hours

---
