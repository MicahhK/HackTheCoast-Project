# POP Trend Intelligence

A trend-discovery tool built for **Prince of Peace Enterprises (POP)** at Hack the Coast 2026.

POP's buyers scout new products by hand, and they've missed trends like ube because by the time they found a compliant supplier, the market window had closed. This tool pulls signals from public sources, keeps only products that pass POP's sourcing rules, and ranks what's left. Each trend gets one of four actions:

- **DISTRIBUTE**: an existing product POP could add to its portfolio
- **DEVELOP**: a trend close to POP's ginger, ginseng, or tea lines that could become a POP-branded product
- **BOTH**: meets both criteria (the strongest opportunities)
- **PASS**: weak fit, blocked by a sourcing rule, or too late

## How It Works

```
collect signals  →  normalize into trends  →  score & filter  →  CSV + UI
(collectors.py)     (discovery.py)            (scoring.py)
```

1. **Collect** signals from Google Trends, trade-publication RSS feeds, Amazon Movers & Shakers, FDA GRAS notices, and Reddit (optional).
2. **Normalize** the signals: match them against a catalog of ingredients, merge duplicates, and count how many sources mention each trend.
3. **Score** each trend: `0.55 × Signal Strength + 0.45 × POP-Fit`. Signal Strength combines growth, recency, how many sources agree, and how crowded the market already is. POP-Fit measures overlap with POP's existing product lines.
4. **Filter** against POP's hard rules: at least 12 months shelf life, no banned FDA ingredients, and a country trade risk of 0.60 or less. A trend that fails gets a score of 0 but stays in the list, so buyers can see why it was rejected.

Results are exported to `artifacts/exports/pop_trend_report.csv`, which opens in Excel. More detail on each stage is in [`docs/`](docs/).

## Setup

```bash
python3 -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
pip install -r requirements.txt
pip install "urllib3<2.0.0"       # required: pytrends breaks on urllib3 2.x
```

**Optional:** to include Reddit, set credentials from [reddit.com/prefs/apps](https://www.reddit.com/prefs/apps) (create a "script" app):

```bash
export REDDIT_CLIENT_ID=your_id
export REDDIT_CLIENT_SECRET=your_secret
```

## Running

**Run the pipeline** and export the CSV:

```bash
python main.py
```

**Streamlit UI** at http://localhost:8501:

```bash
streamlit run app.py
```

**React UI + API** at http://localhost:5173 (two terminals):

```bash
# Terminal 1: API on :8000
uvicorn api:app --reload --port 8000

# Terminal 2: frontend
cd frontend && npm install && npm run dev
```

Both UIs read the exported CSV. If it doesn't exist yet, the API runs the pipeline once on startup. The **Refresh Data** button in the React UI runs the pipeline again with live data.

## Notes

- Google Trends results are cached for 24 hours in `artifacts/cache/gt_cache.json`. Delete that file to force a fresh fetch.
- Amazon scraping is best-effort. Amazon changes its page layout often, so this source can break without warning.
- `scripts/debug_collectors.py` checks that each data source is reachable.
