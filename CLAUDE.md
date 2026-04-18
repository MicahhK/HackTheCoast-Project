# HackTheCoast 2026 — POP Trend Intelligence Tool
## Project Reference for Claude

---

## What This Is

A product discovery and trend intelligence tool built for **Prince of Peace Enterprises (POP)** as part of **Hack the Coast 2026** (Forward Mentorship, April 16–18, 2026, Irvine CA).

POP is a CPG distributor (health foods, herbal teas, ginger chews, Tiger Balm, etc.) that sells ~800 SKUs to 100,000+ retail outlets. Their buyers currently scout trends manually via trade shows. This tool automates that process.

---

## The Business Problem

POP spotted ube trending early in 2023 but lost the market window because finding an FDA-compliant supplier took too long. Same thing happened with tempeh chips. **The gap is between spotting a trend and acting on it.** POP's compliance standards are non-negotiable, so they need to see trends *earlier* than competitors.

**Two outputs the tool must produce:**
1. **DISTRIBUTE** — find an existing branded product POP can add to its distribution portfolio
2. **DEVELOP** — identify a trend adjacent to POP's existing ginger/ginseng/tea lines for a proprietary product

---

## Company Background

| Field | Detail |
|---|---|
| Founded | 1983, Kenneth Yeung |
| HQ | Livermore, CA (+ NY, LA, Hong Kong, China offices) |
| Distribution Centers | 3 U.S. facilities |
| Active SKUs | ~800 (1,000 including variants) |
| Retail Reach | 100,000+ outlets |
| Systems | Microsoft Dynamics GP (on-prem), Cavallo SalesPad. **No WMS, no API, no cloud warehouse.** |
| Buying Team | 5 full-time + 2 part-time buyers managing ~1,000 SKUs |

**Two divisions with different dynamics:**
- **American Market** — mainstream retailers (Walmart, CVS), planogram-driven, annual category reviews
- **Asian Market** — ethnic grocery chains, opportunistic, no slotting fees, no planograms

**Key proprietary brands:** Ginger Honey Crystals, Ginger Chews, American Ginseng, Organic & Premium Teas
**Key distributed brands:** Tiger Balm, Ferrero Rocher, Nutella, Ricola, Bee & Flower Soap

---

## Hard Constraints (Non-Negotiable)

### POP Sourcing Criteria
| Constraint | Rule |
|---|---|
| Shelf life | Minimum **12 months** — refrigerated/fresh products are automatically disqualified |
| FDA ingredients | No banned or restricted ingredients. Watch-list items flagged but not blocked. |
| Country trade risk | Maximum risk score **0.60** — blocks China-only sourcing for *new* categories (POP already has a China supply chain for organic teas, so existing relationships can override) |

### Technical Constraints
- **All data must come from flat files or public sources** — no real-time database access
- **Output must be Excel-compatible** — buyers use spreadsheets, not dashboards (ideally)
- Solutions should ingest CSV/Excel exports, not assume live ERP access
- No hardcoded credentials — use environment variables

---

## POP's Existing Product Lines (for POP-Fit scoring)

| Line Key | Display Name | SKUs | Key Ingredients | Dev Angle |
|---|---|---|---|---|
| `ginger_chews` | POP Ginger Chews | 17 | ginger | Add functional ingredients (adaptogens, turmeric, mushroom) to chew format |
| `ginger_honey_crystals` | POP Ginger Honey Crystals | 6 | ginger, honey, turmeric | Expand into wellness shots (elderberry, manuka, ACV) |
| `american_ginseng` | American Ginseng (tea/root/candy) | 13 | american ginseng | Every adaptogen trend is a potential co-formulation |
| `functional_herbal_teas` | POP Herbal Teas (BP/BS/Cholesterol) | 3 | herbal blend | Extend into trending health concerns (metabolic, sleep, cognitive) |
| `organic_teas` | POP Organic Teas | 4 | tea | Latte powders and flavored teas via existing China supply chain |

**POP's asymmetric advantage:** Deep familiarity with authentic Asian product markets that mainstream U.S. distributors don't understand. Products established in SE Asia but unknown in the U.S. are priority opportunities.

---

## FDA Restricted Ingredients (Compliance Filter)

| Ingredient | Status | Reason |
|---|---|---|
| CBD | restricted | Not permitted as food ingredient — ongoing FDA review |
| Kratom | watch | FDA warnings; not approved as food additive |
| Kava | watch | Hepatotoxicity advisory; careful labeling required |
| Ephedra | banned | Banned in dietary supplements since 2004 |
| Red yeast rice (high monacolin K) | restricted | Treated as unapproved drug |
| Delta-8 THC / Cannabis | restricted | Not permitted in interstate food commerce |
| Psilocybin | banned | Schedule I controlled substance |
| NMN | watch | FDA position: excluded from dietary supplement definition |
| Tianeptine | banned | Not approved drug or dietary ingredient in U.S. |
| Raw milk | restricted | Interstate sale banned |
| Colloidal silver | watch | FDA warnings against health claims |

---

## Country Trade Risk Scores

Key countries for POP's sourcing:
| Country | Risk Score | Notes |
|---|---|---|
| USA | 0.0 | No risk |
| Indonesia | 0.30 | POP's primary source for ginger chews |
| China | 0.85 | Section 301 tariffs — blocks NEW categories, not existing supply chains |
| Thailand | 0.35 | SE Asian specialty opportunity |
| Japan | 0.15 | Low risk |
| South Korea | 0.15 | Low risk |
| India | 0.35 | Moderate |
| Vietnam | 0.45 | Elevated |
| Russia/Iran/North Korea | 1.0 | Sanctioned — hard block |

---

## Shelf Life by Product Format

| Format | Months | POP-Eligible? |
|---|---|---|
| Kombucha | 2 | NO — fails 12-month minimum |
| Fresh/refrigerated | <2 | NO |
| Chips/crackers | 9 | NO |
| Snack bar | 12 | Borderline |
| Chewy candy | 24 | YES |
| Chocolate | 18 | YES |
| Dry tea | 36 | YES |
| Instant powder | 36 | YES |
| Supplement/capsule | 36 | YES |
| Shelf-stable beverage | 18 | YES |
| Topical ointment | 60 | YES |

---

## Project Architecture (3 Stages)

```
Stage 1          Stage 2              Stage 3
collectors.py -> core_discovery.py -> scoring.py -> app.py (UI)
                      |
                 pop_data.py (POP catalog, FDA list, country risk)
```

### Stage 1 — Data Collection (`collectors.py`) ✅ BUILT
Pulls raw signals from public sources. Output schema per signal:
```python
{
    "source":       str,   # "google_trends" | "reddit" | "rss" | "amazon" | "fda_gras"
    "term":         str,   # ingredient or product name found
    "signal_value": int,   # growth %, upvotes, rank delta, or 1 for presence
    "snippet":      str,   # one human-readable evidence line
    "timestamp":    str,   # ISO 8601
    "metadata":     dict,  # source-specific extras
}
```

**Data sources:**
| Source | Library | Auth | Current Status |
|---|---|---|---|
| Google Trends | `pytrends` | None | Working — 48 signals |
| RSS / Trade pubs | `feedparser` | None | Working — 10 signals |
| Reddit | `praw` | Env vars needed | Skipped until credentials set |
| Amazon Movers | `requests` + `bs4` | None | Selectors stale — needs fix |
| FDA GRAS | `requests` + `bs4` | None | Endpoint returning 404 |

**Known issues:**
- `urllib3` must be pinned to `<2.0.0` — pytrends uses `method_whitelist` which was removed in urllib3 2.0
- Amazon HTML selectors break when Amazon updates their layout
- FDA GRAS URL: `https://www.cfsanappsexternal.fda.gov/scripts/fdcc/index.cfm?set=GRASNotices...` returning 404

**Reddit credentials (PowerShell):**
```powershell
$env:REDDIT_CLIENT_ID="your_id"
$env:REDDIT_CLIENT_SECRET="your_secret"
```
Get credentials at: reddit.com/prefs/apps → create app → script type

**RSS Feeds in use:**
- Food Dive: `https://www.fooddive.com/feeds/news/`
- Natural Products Insider: `https://www.naturalproductsinsider.com/rss/all`
- Nutritional Outlook: `https://www.nutritionaloutlook.com/rss/news`
- Food Navigator USA: `https://www.foodnavigator-usa.com/rss/feed.rss`

---

### Stage 2 — Trend Identification (`core_discovery.py`) ⬜ NOT BUILT YET
Takes raw signals from Stage 1 and normalizes them into trend objects.

**Responsibilities:**
1. Extract ingredient/product names from free-text (post titles, article headlines)
2. Count cross-source mentions (same ingredient appearing in Google + Reddit + RSS = stronger signal)
3. Bucket signals into POP's focus categories (functional food, wellness, Asian snacks, personal care)
4. Deduplicate (e.g., "lion's mane coffee" and "lions mane mushroom coffee" → same trend)
5. Output normalized trend objects ready for Stage 3 scoring

**Keyword extraction approach:** Simple keyword matching against a known ingredient/product list first, then NLP if time permits.

---

### Stage 3 — Scoring & Ranking (`scoring.py`) ⬜ (template exists in docs, not yet on disk)
Scores each normalized trend and classifies the action.

**Scoring model:**
| Factor | Weight | Source |
|---|---|---|
| Growth Rate | 40% | YoY or 30-day velocity from Google Trends |
| Recency | 35% | How new — newer = window still open |
| Cross-source corroboration | 15% | How many of the 5 sources flagged it |
| Competition Density | 10% | How crowded is the shelf already |

**Composite = 0.55 × Signal Strength + 0.45 × POP-Fit Score**
- If compliance fails → composite zeroed, trend sorted to bottom but kept visible

**Action classifier:**
| Action | Criteria |
|---|---|
| DEVELOP | POP-Fit ≥ 50 and existing adjacent ingredient/supply chain |
| DISTRIBUTE | Category matches POP distributed portfolio OR competition density < 0.6 |
| BOTH | Both criteria met — strongest opportunities |
| PASS | Weak fit, compliance blocked, or trend too late |

**POP-Fit Score:** Keyword adjacency match between trend ingredients and POP's 5 proprietary lines. 30 points per match, capped at 100.

---

## Files on Disk

```
HackTheCoast-Project/
├── CLAUDE.md              # This file
├── collectors.py          # Stage 1 — data collection (BUILT)
├── core_discovery.py      # Stage 2 — normalization (NOT BUILT)
├── main.py                # Placeholder
├── requirements.txt       # Dependencies
├── debug_collectors.py    # Diagnostic script
└── debug_amazon.py        # Amazon selector debugger
```

**Files referenced in project docs but not yet on disk:**
- `scoring.py` — Stage 3 scoring engine
- `app.py` — Streamlit UI
- `pop_data.py` — POP catalog, FDA list, country risk, shelf-life heuristics
- `trends.py` — Mock trend data + live API stubs

---

## Hackathon Deliverables

Teams must present:
1. How the tool discovers trends (data sources, pipeline, scoring logic)
2. How it filters against POP's sourcing criteria
3. Sample output: top recommendations for at least one product category, with context
4. How it identifies product *development* opportunities (not just distribution)
5. Key challenges and lessons learned

**Presentation: 6–8 minutes**

**Judging note:** "A focused prototype covering one product category well is better than a broad but shallow scan across everything."

---

## What's Left to Build

1. **Stage 2** (`core_discovery.py`) — ingredient extraction, cross-source counting, deduplication, category bucketing
2. **Stage 3** (`scoring.py`) — compliance filters, signal scoring, POP-fit scoring, action classification
3. **`pop_data.py`** — POP catalog data (product lines, FDA list, country risk, shelf-life table)
4. **`app.py`** — Streamlit UI with sidebar filters, trend cards, CSV export
5. **Fix Amazon** — selectors stale, need to inspect current page HTML
6. **Fix FDA GRAS** — endpoint returning 404, need correct URL

---

## Install Commands

```bash
pip install streamlit pandas pytrends praw feedparser requests beautifulsoup4
pip install "urllib3<2.0.0"   # REQUIRED — pytrends breaks with urllib3 >= 2.0
```

---

## Key Design Decisions Made So Far

- Stage 1 output is **raw signals**, not fully normalized trends — normalization is Stage 2's job
- Google Trends queries are **batched 5 at a time** (pytrends hard limit) with no category filter (`cat=71` was suppressing niche terms)
- Amazon scraping is **best-effort** — Amazon changes their HTML frequently, treat as supplementary
- Reddit credentials must be set as **env vars per PowerShell session** — they don't persist
- Compliance filters are **hard gates** — a blocked trend gets zeroed composite score but stays visible so buyers understand *why* it was rejected
