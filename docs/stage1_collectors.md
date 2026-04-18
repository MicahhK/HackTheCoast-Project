# Stage 1 — Data Collection (`collectors.py`)

Pulls raw signals from five public sources and returns a unified list of signal dicts.
Output feeds directly into Stage 2 (`core_discovery.py`).

---

## Status

| Source | Status | Signal Count (typical) |
|---|---|---|
| Google Trends | ✅ Working | ~28 (cached 24h) |
| Reddit | ⚠️ Needs credentials | 0 until creds set |
| RSS / Trade Pubs | ✅ Working | ~67 |
| Amazon Movers & Shakers | ✅ Working | ~40 |
| FDA GRAS Notices | ✅ Working | ~50 |

**Total without Reddit: ~185 signals**

---

## Raw Signal Schema

Every collector returns a list of dicts with this exact shape:

```python
{
    "source":       str,   # "google_trends" | "reddit" | "rss" | "amazon_movers" | "fda_gras"
    "term":         str,   # ingredient/product name or raw article title
    "signal_value": int,   # strength — meaning differs by source (see table below)
    "snippet":      str,   # one human-readable evidence sentence
    "timestamp":    str,   # ISO 8601
    "metadata":     dict,  # source-specific extras
}
```

### `signal_value` by source

| Source | What `signal_value` means | Range |
|---|---|---|
| `google_trends` | % growth, last 4 weeks vs prior 12 weeks | −100 to +5000 (capped) |
| `reddit` | Post upvote score | 0 to ~50,000 |
| `rss` | Always 1 — presence is the signal; frequency counted in Stage 2 | 1 |
| `amazon_movers` | Rank positions jumped this week; 999 = previously unranked | 0 to 999 |
| `fda_gras` | Always 1 — cleared = ingredient entering U.S. market | 1 |

---

## Source 1 — Google Trends

**Function:** `collect_google_trends(keywords=None, timeframe="today 3-m")`

**What it does:**
- Queries all `SEED_TERMS` in batches of 5 (pytrends hard limit)
- For each term: computes % growth (last 4 weeks vs prior 12 weeks from interest-over-time)
- For each term: pulls top 5 **rising related queries** — these are the breakout sub-terms

**Two signal types produced:**
1. `query_type: "interest_over_time"` — one signal per seed term, `signal_value` = growth %
2. `query_type: "rising_related"` — up to 5 signals per seed term, `signal_value` = rising %

**Caching:**
Results are written to `gt_cache.json` and reused for 24 hours. Delete the file to force a fresh fetch.

**Rate limits:**
- 2-second sleep between each batch of 5
- If rate-limited, increases to 5-second backoff
- Running all ~20 seed terms takes ~30–40 seconds on a clean fetch

**Seed terms (`SEED_TERMS`):**
```
ginger shot, ginseng supplement, honey wellness,
lion's mane, ashwagandha gummy, reishi tea, cordyceps coffee,
moringa powder, mushroom coffee,
pandan snack, yuzu candy, ube latte, mochi snack, tempeh chips,
functional candy, collagen drink, elderberry syrup, turmeric latte
```

**Known issues:**
- `urllib3` must be pinned to `<2.0.0` — pytrends uses `method_whitelist` removed in urllib3 2.0
- No category filter (`cat=71` suppresses niche terms — intentionally omitted)

---

## Source 2 — Reddit

**Function:** `collect_reddit(subreddits=None, post_limit=75, days_back=30)`

**What it does:**
- Fetches the 75 most recent posts from each subreddit in `FOOD_WELLNESS_SUBREDDITS`
- Filters to posts within the last 30 days
- `term` = full post title (Stage 2 extracts ingredient names from it)
- `signal_value` = upvote score (community interest proxy)

**Subreddits watched:**
```
EatCheapAndHealthy, supplements, nootropics,
tea, veganfoodporn, asianfood, PlantBasedDiet
```

**Setting up credentials:**
1. Go to [reddit.com/prefs/apps](https://www.reddit.com/prefs/apps) → **create app** → select **script**
2. Set environment variables:
   ```bash
   # macOS/Linux
   export REDDIT_CLIENT_ID=your_id
   export REDDIT_CLIENT_SECRET=your_secret
   ```
   ```powershell
   # Windows PowerShell
   $env:REDDIT_CLIENT_ID="your_id"
   $env:REDDIT_CLIENT_SECRET="your_secret"
   ```

**Note:** Credentials don't persist between terminal sessions — must re-set each time.

---

## Source 3 — RSS / Trade Publications

**Function:** `collect_rss(feed_urls=None, days_back=90)`

**What it does:**
- Parses RSS feeds from food & wellness trade publications
- Filters to articles published within the last 90 days
- `term` = article headline (Stage 2 scans for ingredient keywords)
- `signal_value` = always 1 (presence); Stage 2 counts frequency

**Active feeds (`TRADE_RSS_FEEDS`):**

| Feed | URL | Typical articles |
|---|---|---|
| Food Dive | `https://www.fooddive.com/feeds/news/` | ~10 |
| New Hope Network | `https://www.newhope.com/rss.xml` | ~50 |
| SPINS Insights | `https://www.spins.com/feed/` | ~10 |

**Previously active (now dead — URLs changed):**
- Food Navigator USA: `https://www.foodnavigator-usa.com/rss/feed.rss`
- Nutritional Outlook: `https://www.nutritionaloutlook.com/rss/news`
- Natural Products Insider: `https://www.naturalproductsinsider.com/rss/all`

---

## Source 4 — Amazon Movers & Shakers

**Function:** `collect_amazon_movers()`

**What it does:**
- Scrapes Amazon's public Movers & Shakers pages (no login required)
- Covers **Grocery & Gourmet Food** and **Health & Household** categories
- Skips downward movers — only captures rising products
- `signal_value` = rank positions jumped (e.g., was #500, now #5 → signal = 495)
- `signal_value = 999` for "previously unranked" entries (brand new to chart)

**Selector used:** `div[data-asin]` (updated April 2026 — Amazon changed layout)

**Known fragility:**
- Amazon changes HTML structure periodically — selectors may break again
- Amazon can return 503/captcha if hit too frequently — run at most once per day
- Treat as best-effort supplementary signal, not primary source

**Categories scraped:**
```
https://www.amazon.com/gp/movers-and-shakers/grocery/
https://www.amazon.com/gp/movers-and-shakers/hpc/
```

---

## Source 5 — FDA GRAS Notices

**Function:** `collect_fda_gras(days_back=365)`

**What it does:**
- Fetches the most recent GRAS (Generally Recognized As Safe) notices from the FDA database
- A new GRAS filing = an ingredient is entering the U.S. food market
- `signal_value` = always 1 (cleared = safe to source)
- Pending notices (no closure date yet) use today's date as a proxy

**URL:** `https://www.cfsanappsexternal.fda.gov/scripts/fdcc/index.cfm?set=GRASNotices&sort=GRN_No&order=DESC`

**Table columns parsed:**
| Column | Field |
|---|---|
| `cols[0]` | GRN Notice number |
| `cols[1]` | Substance name → `term` |
| `cols[2]` | Date of closure → `timestamp` |
| `cols[3]` | FDA's Letter (Pending / No Questions / etc.) |

**Note:** The `accessdata.fda.gov` mirror returns 404 — always use `cfsanappsexternal.fda.gov`.

---

## Running Stage 1

```bash
# Activate venv first
source venv/bin/activate        # macOS/Linux
venv\Scripts\activate           # Windows

# Quick test (prints first 10 signals + total count)
python collectors.py

# Full diagnostic (tests each source individually)
python debug_collectors.py
```

**Expected output:**
```
[collectors] Collecting Google Trends...   -> 28 signals
[collectors] Collecting Reddit...          -> 0 signals (until creds set)
[collectors] Collecting RSS / Trade...     -> 67 signals
[collectors] Collecting Amazon Movers...   -> 40 signals
[collectors] Collecting FDA GRAS...        -> 50 signals
[collectors] Total raw signals: 185
```

---

## What Stage 2 Does with These Signals

Stage 2 (`core_discovery.py`) scans every signal's `term` + `snippet` for ingredient keywords from its catalog. Signals with no keyword match are discarded. Matched signals are grouped under a canonical trend name, then aggregated into growth rate, recency score, and competition density metrics.

→ See [stage2_core_discovery.md](stage2_core_discovery.md)
