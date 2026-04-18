"""
Stage 1 — Data Collection.

Each collector pulls raw signals from one public source and returns a list of dicts
with a consistent schema. core_discovery.py (Stage 2) normalizes and aggregates them.

Raw signal schema:
{
    "source":       str,   # "google_trends" | "reddit" | "rss" | "amazon" | "fda_gras"
    "term":         str,   # ingredient, product, or category found
    "signal_value": int,   # growth %, upvotes, rank delta, or 1 for presence
    "snippet":      str,   # one human-readable line of evidence
    "timestamp":    str,   # ISO 8601
    "metadata":     dict,  # source-specific extras (subreddit, url, parent_term, etc.)
}

Credentials (Reddit only) — set as environment variables, never hardcode:
    REDDIT_CLIENT_ID
    REDDIT_CLIENT_SECRET
"""

import os
import json
import time
from datetime import datetime, timedelta

CACHE_FILE = "gt_cache.json"
CACHE_MAX_AGE_HOURS = 24


def _load_gt_cache():
    if not os.path.exists(CACHE_FILE):
        return None
    try:
        with open(CACHE_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        saved_at = datetime.fromisoformat(data["saved_at"])
        if (datetime.now() - saved_at).total_seconds() < CACHE_MAX_AGE_HOURS * 3600:
            print(f"[collectors] Google Trends: using cache from {saved_at.strftime('%H:%M')} today.")
            return data["signals"]
    except Exception:
        pass
    return None


def _save_gt_cache(signals):
    try:
        with open(CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump({"saved_at": datetime.now().isoformat(), "signals": signals}, f)
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Seed terms — ingredients and formats POP cares about. Used as starting
# points for Google Trends queries. Stage 2 expands from these via signal data.
# ---------------------------------------------------------------------------

SEED_TERMS = [
    # POP's existing strengths — look for adjacencies
    "ginger shot", "ginseng supplement", "honey wellness",
    # Functional / adaptogen space
    "lion's mane", "ashwagandha gummy", "reishi tea", "cordyceps coffee",
    "moringa powder", "mushroom coffee",
    # Asian specialty — POP's asymmetric advantage
    "pandan snack", "yuzu candy", "ube latte", "mochi snack", "tempeh chips",
    # Trending wellness formats
    "functional candy", "collagen drink", "elderberry syrup", "turmeric latte",
]

FOOD_WELLNESS_SUBREDDITS = [
    "EatCheapAndHealthy", "supplements", "nootropics",
    "tea", "veganfoodporn", "asianfood", "PlantBasedDiet",
]

TRADE_RSS_FEEDS = {
    "Food Dive":               "https://www.fooddive.com/feeds/news/",
    "Natural Products Insider": "https://www.naturalproductsinsider.com/rss/all",
    "Nutritional Outlook":     "https://www.nutritionaloutlook.com/rss/news",
    "Food Navigator USA":      "https://www.foodnavigator-usa.com/rss/feed.rss",
}


# ---------------------------------------------------------------------------
# SOURCE 1 — Google Trends  (pytrends, no API key required)
# ---------------------------------------------------------------------------

def collect_google_trends(keywords=None, timeframe="today 3-m"):
    """
    Pull interest-over-time and rising related queries from Google Trends.

    Batches 5 terms per request (pytrends limit). No category filter so we
    get data for niche terms that cat=71 would suppress.

    Install: pip install pytrends
    """
    try:
        from pytrends.request import TrendReq
    except ImportError:
        print("[collectors] pytrends not installed — skipping Google Trends.")
        return []

    cached = _load_gt_cache()
    if cached is not None:
        return cached

    kws = keywords or SEED_TERMS
    pytrends = TrendReq(hl="en-US", tz=360, timeout=(10, 25), retries=2, backoff_factor=0.5)
    signals = []

    # Batch 5 terms at a time (pytrends hard limit)
    for i in range(0, len(kws), 5):
        batch = kws[i:i + 5]
        try:
            pytrends.build_payload(batch, timeframe=timeframe, geo="US")

            # --- interest over time: compare recent 4 weeks vs prior 12 weeks ---
            interest_df = pytrends.interest_over_time()
            if not interest_df.empty:
                for term in batch:
                    if term not in interest_df.columns:
                        continue
                    series = interest_df[term]
                    recent = series.iloc[-4:]
                    older  = series.iloc[-16:-4]
                    if older.mean() > 0:
                        growth_pct = int(((recent.mean() - older.mean()) / older.mean()) * 100)
                    else:
                        growth_pct = 0
                    # Include all terms with any search volume, even flat ones
                    if series.mean() > 0:
                        signals.append({
                            "source": "google_trends",
                            "term": term,
                            "signal_value": growth_pct,
                            "snippet": (
                                f"Google Trends: '{term}' avg interest={series.mean():.1f}/100, "
                                f"growth {growth_pct:+d}% (last 4 wks vs prior 12)"
                            ),
                            "timestamp": datetime.now().isoformat(),
                            "metadata": {
                                "timeframe": timeframe,
                                "query_type": "interest_over_time",
                                "avg_interest": round(float(series.mean()), 1),
                            },
                        })

            # --- rising related queries for each term ---
            related = pytrends.related_queries()
            for term in batch:
                rising_df = (related.get(term) or {}).get("rising")
                if rising_df is None or rising_df.empty:
                    continue
                for _, row in rising_df.head(5).iterrows():
                    signals.append({
                        "source": "google_trends",
                        "term": str(row["query"]),
                        "signal_value": min(int(row["value"]), 5000),
                        "snippet": (
                            f"Google Trends rising query: '{row['query']}' "
                            f"+{row['value']}% (related to '{term}')"
                        ),
                        "timestamp": datetime.now().isoformat(),
                        "metadata": {"parent_term": term, "query_type": "rising_related"},
                    })

            time.sleep(2.0)  # stay under rate limits between batches
        except Exception as exc:
            print(f"[collectors/google_trends] batch {batch}: {exc}")
            time.sleep(5.0)
            continue

    _save_gt_cache(signals)
    return signals


# ---------------------------------------------------------------------------
# SOURCE 2 — Reddit  (praw, needs free Reddit developer credentials)
# ---------------------------------------------------------------------------

def collect_reddit(subreddits=None, post_limit=75, days_back=30):
    """
    Fetch recent posts from food/wellness subreddits via the official Reddit API (PRAW).

    What to look for:
      - Post titles mentioning ingredients or products
      - High upvote + comment count = community signal
      - Stage 2 scans titles for ingredient keywords

    Credentials — get a free Reddit app at https://www.reddit.com/prefs/apps
    Then set:
        export REDDIT_CLIENT_ID=your_id
        export REDDIT_CLIENT_SECRET=your_secret

    Install: pip install praw
    """
    try:
        import praw
    except ImportError:
        print("[collectors] praw not installed — skipping Reddit.")
        return []

    client_id     = os.environ.get("REDDIT_CLIENT_ID")
    client_secret = os.environ.get("REDDIT_CLIENT_SECRET")
    if not client_id or not client_secret:
        print("[collectors] REDDIT_CLIENT_ID / REDDIT_CLIENT_SECRET not set — skipping Reddit.")
        return []

    reddit = praw.Reddit(
        client_id=client_id,
        client_secret=client_secret,
        user_agent="POP_TrendIntelligence/1.0 (hackathon, read-only)",
    )

    subs   = subreddits or FOOD_WELLNESS_SUBREDDITS
    cutoff = datetime.now() - timedelta(days=days_back)
    signals = []

    for sub_name in subs:
        try:
            for post in reddit.subreddit(sub_name).new(limit=post_limit):
                created = datetime.fromtimestamp(post.created_utc)
                if created < cutoff:
                    continue
                signals.append({
                    "source": "reddit",
                    "term": post.title,           # Stage 2 extracts ingredient names from this
                    "signal_value": post.score,   # upvotes = community interest strength
                    "snippet": (
                        f"r/{sub_name}: '{post.title[:80]}' — "
                        f"{post.score} upvotes, {post.num_comments} comments"
                    ),
                    "timestamp": created.isoformat(),
                    "metadata": {
                        "subreddit":     sub_name,
                        "upvote_ratio":  post.upvote_ratio,
                        "num_comments":  post.num_comments,
                        "url":           f"https://reddit.com{post.permalink}",
                    },
                })
            time.sleep(0.6)
        except Exception as exc:
            print(f"[collectors/reddit] r/{sub_name}: {exc}")
            continue

    return signals


# ---------------------------------------------------------------------------
# SOURCE 3 — Trade Publication RSS  (feedparser, no API key)
# ---------------------------------------------------------------------------

def collect_rss(feed_urls=None, days_back=90):
    """
    Fetch recent articles from food & wellness trade publication RSS feeds.

    No login or API key needed. Good coverage of Fancy Food Show, Expo West,
    new product launches, and ingredient trend pieces.

    Stage 2 scans titles + summaries for ingredient/category keywords.

    Install: pip install feedparser
    """
    try:
        import feedparser
    except ImportError:
        print("[collectors] feedparser not installed — skipping RSS.")
        return []

    feeds  = feed_urls or TRADE_RSS_FEEDS
    cutoff = datetime.now() - timedelta(days=days_back)
    signals = []

    for feed_name, url in (feeds.items() if isinstance(feeds, dict) else enumerate(feeds)):
        try:
            feed = feedparser.parse(url)
            display_name = feed.feed.get("title", str(feed_name))

            for entry in feed.entries:
                if hasattr(entry, "published_parsed") and entry.published_parsed:
                    published = datetime(*entry.published_parsed[:6])
                else:
                    published = datetime.now()
                if published < cutoff:
                    continue

                title   = entry.get("title", "")
                summary = entry.get("summary", "")
                signals.append({
                    "source": "rss",
                    "term": title,                # Stage 2 extracts ingredient mentions
                    "signal_value": 1,            # presence = signal; frequency counted in Stage 2
                    "snippet": f"{display_name}: '{title[:80]}' — {summary[:100]}",
                    "timestamp": published.isoformat(),
                    "metadata": {
                        "feed":    display_name,
                        "url":     entry.get("link", ""),
                        "title":   title,
                        "summary": summary,
                    },
                })
            time.sleep(0.4)
        except Exception as exc:
            print(f"[collectors/rss] {feed_name}: {exc}")
            continue

    return signals


# ---------------------------------------------------------------------------
# SOURCE 4 — Amazon Movers & Shakers  (requests + BeautifulSoup, best-effort)
# ---------------------------------------------------------------------------

def collect_amazon_movers(days_back=None):  # noqa: ARG001  (param reserved for caching)
    """
    Scrape Amazon's public Movers & Shakers pages for Grocery and Health categories.
    Fast rank climbers (e.g., #80 -> #5 in a week) are strong retail demand signals.

    IMPORTANT — known fragility:
      - Amazon returns 503/captcha if hit too often. Run at most once per day.
      - HTML selectors may break if Amazon updates their layout.
      - This is read-only scraping of public pages (no login required).

    Install: pip install requests beautifulsoup4
    """
    try:
        import requests
        from bs4 import BeautifulSoup
    except ImportError:
        print("[collectors] requests/beautifulsoup4 not installed — skipping Amazon.")
        return []

    # Public Movers & Shakers pages — no login required
    CATEGORY_URLS = {
        "Grocery & Gourmet Food": "https://www.amazon.com/gp/movers-and-shakers/grocery/",
        "Health & Household":     "https://www.amazon.com/gp/movers-and-shakers/hpc/",
    }

    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0.0.0 Safari/537.36"
        ),
        "Accept-Language": "en-US,en;q=0.9",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    }

    signals = []
    for category_name, url in CATEGORY_URLS.items():
        try:
            resp = requests.get(url, headers=headers, timeout=15)
            if resp.status_code != 200:
                print(f"[collectors/amazon] HTTP {resp.status_code} for '{category_name}'")
                continue

            soup  = BeautifulSoup(resp.text, "html.parser")
            items = soup.select(".a-ordered-list .a-list-item")[:20]

            if not items:
                print(f"[collectors/amazon] No items found for '{category_name}' — selectors may be stale.")
                continue

            for item in items:
                # Skip downward movers — only care about rising products
                arrow = item.select_one("img.zg-grid-arrow")
                if arrow and "down" in arrow.get("alt", "").lower():
                    continue

                # Product name from image alt text
                img = item.select_one("img.p13n-product-image")
                if not img:
                    continue
                name = img.get("alt", "").strip()
                if not name:
                    continue

                # Rank change from metadata text e.g. "Sales rank: 5 (was 80)"
                meta_el  = item.select_one("._cDEzb_zg-grid-rank-metadata_33jPv")
                meta_txt = meta_el.get_text(" ", strip=True) if meta_el else ""
                rank_el  = item.select_one(".zg-bdg-text")
                rank_now = int(rank_el.get_text(strip=True).replace("#", "")) if rank_el else 0

                # Parse signal value: positions jumped, or 999 for brand-new entries
                import re
                was_match = re.search(r"was\s+(\d+)", meta_txt)
                if was_match:
                    rank_before = int(was_match.group(1))
                    signal_val  = rank_before - rank_now  # bigger jump = higher value
                elif "previously unranked" in meta_txt.lower():
                    signal_val = 999  # brand new — maximum signal
                else:
                    signal_val = 0

                signals.append({
                    "source": "amazon_movers",
                    "term": name,
                    "signal_value": signal_val,
                    "snippet": (
                        f"Amazon {category_name} #{rank_now}: "
                        f"'{name[:60]}' — {meta_txt}"
                    ),
                    "timestamp": datetime.now().isoformat(),
                    "metadata": {
                        "rank":     rank_now,
                        "category": category_name,
                        "rank_change": meta_txt,
                    },
                })

            time.sleep(3.0)  # be polite — Amazon blocks fast scrapers
        except Exception as exc:
            print(f"[collectors/amazon] '{category_name}': {exc}")
            continue

    return signals


# ---------------------------------------------------------------------------
# SOURCE 5 — FDA GRAS Notices  (requests, fully public)
# ---------------------------------------------------------------------------

def collect_fda_gras(days_back=365):
    """
    Fetch recent FDA GRAS (Generally Recognized As Safe) notices.

    A new GRAS filing means an ingredient is entering the U.S. food market —
    early signal of what suppliers will start offering. Feeds both trend
    discovery AND compliance context (cleared = safe to source).

    Data is from the public FDA GRAS Notices database — no API key needed.
    URL: https://www.accessdata.fda.gov/scripts/fdcc/index.cfm?set=GRASNotices

    Install: pip install requests beautifulsoup4
    """
    try:
        import requests
        from bs4 import BeautifulSoup
    except ImportError:
        print("[collectors] requests/beautifulsoup4 not installed — skipping FDA GRAS.")
        return []

    url = (
        "https://www.cfsanappsexternal.fda.gov/scripts/fdcc/"
        "index.cfm?set=GRASNotices&sort=GRN_No&order=DESC&startrow=1&type=basic&search="
    )

    signals  = []
    cutoff   = datetime.now() - timedelta(days=days_back)

    try:
        resp = requests.get(
            url,
            timeout=20,
            headers={"User-Agent": "POP_TrendIntelligence/1.0 (hackathon, read-only)"},
        )
        if resp.status_code != 200:
            print(f"[collectors/fda_gras] HTTP {resp.status_code}")
            return []

        soup = BeautifulSoup(resp.text, "html.parser")
        rows = soup.select("table.fdatable tr, table tr")[1:]  # skip header row

        for row in rows[:60]:  # scan last 60 notices
            cols = row.select("td")
            if len(cols) < 4:
                continue

            substance = cols[1].get_text(strip=True)
            date_str  = cols[3].get_text(strip=True)

            try:
                notice_date = datetime.strptime(date_str, "%m/%d/%Y")
            except ValueError:
                continue

            if notice_date < cutoff:
                continue

            signals.append({
                "source": "fda_gras",
                "term": substance,
                "signal_value": 1,  # presence = cleared for market
                "snippet": (
                    f"FDA GRAS Notice: '{substance}' cleared {date_str} — "
                    f"ingredient entering U.S. food market"
                ),
                "timestamp": notice_date.isoformat(),
                "metadata": {"notice_date": date_str, "fda_status": "GRAS_cleared"},
            })

    except Exception as exc:
        print(f"[collectors/fda_gras] {exc}")

    return signals


# ---------------------------------------------------------------------------
# AGGREGATE — run all collectors, return combined raw signal list
# ---------------------------------------------------------------------------

def collect_all():
    """
    Run all five collectors. Returns a combined list of raw signal dicts.

    Pass the result to core_discovery.py (Stage 2) for normalization,
    ingredient extraction, deduplication, and scoring.
    """
    all_signals = []

    sources = [
        ("Google Trends",   collect_google_trends),
        ("Reddit",          collect_reddit),
        ("RSS / Trade",     collect_rss),
        ("Amazon Movers",   collect_amazon_movers),
        # FDA GRAS endpoint currently unavailable — re-enable when URL is confirmed
    ]

    for label, fn in sources:
        print(f"[collectors] Collecting {label}...")
        try:
            batch = fn()
            print(f"[collectors]   -> {len(batch)} signals")
            all_signals.extend(batch)
        except Exception as exc:
            print(f"[collectors]   -> failed: {exc}")

    print(f"[collectors] Total raw signals: {len(all_signals)}")
    return all_signals


# ---------------------------------------------------------------------------
# Quick test — python collectors.py
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    signals = collect_all()
    for s in signals[:10]:
        print(f"[{s['source']}] {s['term'][:50]} | value={s['signal_value']} | {s['timestamp'][:10]}")
    print(f"\n{len(signals)} total signals collected.")
