# Stage 2 — Trend Normalization (`core_discovery.py`)

Takes raw signals from Stage 1 and normalizes them into structured trend objects ready for scoring.

---

## Status: ✅ Built

---

## What This Stage Does

1. **Extract** — scan every signal's text for known ingredient/product keywords
2. **Deduplicate** — group aliases under one canonical name ("lion's mane coffee" + "lions mane mushroom" → "Lion's Mane Mushroom")
3. **Aggregate** — count cross-source mentions and compute growth/recency/competition metrics
4. **Output** — sorted list of trend objects for `scoring.py` (Stage 3)

---

## Input

A list of raw signal dicts from `collectors.collect_all()`:

```python
[
    {"source": "google_trends", "term": "mushroom coffee", "signal_value": 8, ...},
    {"source": "rss", "term": "Lion's mane drives nootropic boom", "signal_value": 1, ...},
    ...
]
```

---

## Output

A sorted list of normalized trend objects (sorted by source count desc, then growth rate desc):

```python
{
    # Identity (from ingredient catalog)
    "name":                   str,        # "Lion's Mane Mushroom"
    "category":               str,        # "functional food"
    "format":                 str,        # "instant powder"
    "key_ingredients":        list,       # ["lion's mane", "mushroom", "nootropic"]
    "ingredients":            list,       # full ingredient list for FDA check
    "primary_source_country": str,        # "USA" — for trade-risk check

    # Computed signal metrics
    "growth_rate_pct":        int,        # seed-term growth % (interest_over_time only)
    "recency_score":          float,      # 0.0–1.0 — how open is the trend window
    "competition_density":    float,      # 0.0–1.0 — how crowded is the shelf
    "avg_gt_interest":        float|None, # absolute GT interest 0–100; None if no GT data
    "rising_query_count":     int,        # how many breakout related queries exist

    # Evidence
    "evidence":     list,  # top 5 signals by signal_value
    "sources":      list,  # distinct source names that flagged this trend
    "source_count": int,   # how many distinct sources
    "signal_count": int,   # total number of matched signals
}
```

---

## Ingredient Catalog (`INGREDIENT_CATALOG`)

The catalog is the heart of Stage 2 — it defines what trends we look for and how they map to POP's business.

Each entry:

```python
{
    "name":                   str,   # canonical display name
    "aliases":                list,  # strings to match in signal text (case-insensitive)
    "category":               str,   # POP focus bucket
    "format":                 str,   # product format (used for shelf-life check in Stage 3)
    "key_ingredients":        list,  # for POP-Fit scoring
    "ingredients":            list,  # full list for FDA compliance check
    "primary_source_country": str,   # for trade-risk check
}
```

### Current Catalog (20 entries)

| Trend | Category | Format | Source Country |
|---|---|---|---|
| Ginger Shot | functional beverage | ready-to-drink bottle | USA |
| Turmeric Ginger Latte | functional beverage | instant powder | India |
| Manuka Honey | functional food | shelf-stable beverage | New Zealand |
| Ginseng Supplement | health & wellness | supplement / capsule | USA |
| Elderberry | functional beverage | shelf-stable beverage | USA |
| Lion's Mane Mushroom | functional food | instant powder | USA |
| Reishi Mushroom Tea | functional tea | dry tea | China |
| Mushroom Coffee | functional beverage | instant powder | USA |
| Matcha Mushroom Latte | functional beverage | instant powder | Japan |
| Ashwagandha | functional confection | chewy candy | India |
| Moringa | superfood powder | instant powder | India |
| Pandan | asian specialty | chewy candy | Thailand |
| Yuzu Citrus | asian specialty | chewy candy | Japan |
| Ube (Purple Yam) | asian specialty | instant powder | Philippines |
| Tempeh | plant-based snack | chips/crackers | Indonesia |
| Peanut Butter Powder | functional food | instant powder | USA |
| Chia Seeds | functional food | dried fruit | Peru |
| Collagen Peptides | functional beverage | instant powder | USA |

**To add a new trend:** append an entry to `INGREDIENT_CATALOG` in `core_discovery.py`. Include at least 3 aliases to improve match rate.

---

## Step-by-Step Logic

### Step 1 — `extract_mentions(signals)`

Scans every signal's `term + snippet` text (lowercased) against all aliases in the catalog.

- One match per ingredient per signal — no double-counting
- Returns `{ canonical_name -> [list of matching signals] }`

```python
text = (signal["term"] + " " + signal["snippet"]).lower()
for alias in item["aliases"]:
    if alias.lower() in text:
        mentions[item["name"]].append(signal)
        break
```

### Step 2 — `compute_growth_rate(signals)`

Returns the seed term's growth rate using **interest_over_time signals only** (signals with `metadata.query_type == "interest_over_time"`). Rising-related queries are excluded — they inflate the number and are tracked separately via `rising_query_count`.

- Prefers GT interest_over_time growth % (max across matched seed terms)
- Falls back to Amazon: `rank_jump × 2`, capped at 200 if no GT data

### Step 3 — `compute_recency_score(signals)`

Uses **interest_over_time signals only** — these measure whether the seed term itself is still climbing. Rising-related queries tell us about sub-term velocity but not whether the window is still open on the parent trend.

```
score = (avg_iot_growth + 100) / 300

Examples:
  avg_growth = +200  →  score = 1.00  (hot, window wide open)
  avg_growth =    0  →  score = 0.33  (flat)
  avg_growth =  −50  →  score = 0.17  (declining, window closing)
  avg_growth = −100  →  score = 0.00  (dead)
```

No GT interest_over_time data → 0.5 (unknown, neutral)

### Step 3b — `count_rising_queries(signals)`

Counts Google Trends signals with `metadata.query_type == "rising_related"`. Each one is a breakout sub-term (e.g. `"elderberry gummies"` when seed was `"elderberry syrup"`). High count means the trend is spawning sub-categories — a sign it's still early. Stored as `rising_query_count`.

### Step 3c — `compute_avg_interest(signals)`

Average absolute Google Trends search interest (0–100 scale) from interest_over_time signals. Stored as `avg_gt_interest`.

Distinguishes a category leader in decline (high interest + negative growth = late stage) from a true niche on the rise (low interest + positive growth = early). Example: Mushroom Coffee at 61/100 with +8% is a much bigger market than Pandan at 9/100 with +12%.

### Step 4 — `compute_competition_density(signals)`

Maps Amazon rank to a 0–1 crowdedness score:

```
density = 1.0 − (avg_rank / 30)

Examples:
  rank  1  →  0.97  (very crowded — everyone's there)
  rank 15  →  0.50  (moderate competition)
  rank 30  →  0.00  (wide open)
```

No Amazon data → 0.5 (moderate, unknown)

### Step 5 — `normalize(signals)` (main function)

Calls steps 1–4, assembles the trend object, sorts results.

**Sort order:** source count descending → growth rate descending

Trends with zero matched signals are dropped entirely.

---

## Running Stage 2

```bash
source venv/bin/activate

# Runs Stage 1 + Stage 2 and prints a summary table
python core_discovery.py
```

**Expected output:**
```
Running Stage 1 collectors...
[collectors] Total raw signals: 185

Running Stage 2 normalization on 185 signals...

12 trends identified

Trend                          Sources  Growth  Recency  Competition
----------------------------------------------------------------------
Mushroom Coffee                GT,RSS      8%     0.69         0.50
Lion's Mane Mushroom           GT,RSS     -5%     0.48         0.50
...
```

---

## Known Limitations

- **Keyword matching only** — "lion's mane latte" matches "Lion's Mane Mushroom" even if it's a different product. NLP entity extraction would improve precision but adds complexity.
- **Aliases must be maintained manually** — if a new brand name or variant emerges, add it to the catalog's `aliases` list.
- **No signal weighting by source quality** — an RSS article from SPINS counts the same as one from a generic food blog. Source quality weighting is a Stage 3 improvement.

---

## What Stage 3 Does with These Trends

Stage 3 (`scoring.py`) applies POP's hard constraints (shelf life, FDA ingredients, country trade risk), computes the composite score, and classifies each trend as DISTRIBUTE / DEVELOP / BOTH / PASS.

→ See [stage3_scoring.md](stage3_scoring.md)
