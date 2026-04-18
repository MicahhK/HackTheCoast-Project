"""
Stage 1 — Data Collection.

Each collector is a class that inherits from BaseCollector and implements
collect() -> list[dict]. collect_all() instantiates all five and aggregates.

Raw signal schema:
{
    "source":       str,   # "google_trends" | "reddit" | "rss" | "amazon_movers" | "fda_gras"
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
from abc import ABC, abstractmethod
from datetime import datetime, timedelta


# ---------------------------------------------------------------------------
# Cache helpers — used by GoogleTrendsCollector
# ---------------------------------------------------------------------------

CACHE_FILE         = "gt_cache.json"
CACHE_MAX_AGE_HOURS = 24


# ---------------------------------------------------------------------------
# Seed terms — ingredients and formats POP cares about.
# ---------------------------------------------------------------------------

SEED_TERMS = [
    "ginger shot", "ginseng supplement", "honey wellness",
    "lion's mane", "ashwagandha gummy", "reishi tea", "cordyceps coffee",
    "moringa powder", "mushroom coffee",
    "pandan snack", "yuzu candy", "ube latte", "mochi snack", "tempeh chips",
    "functional candy", "collagen drink", "elderberry syrup", "turmeric latte",
]

FOOD_WELLNESS_SUBREDDITS = [
    "EatCheapAndHealthy", "supplements", "nootropics",
    "tea", "veganfoodporn", "asianfood", "PlantBasedDiet",
]

TRADE_RSS_FEEDS = {
    "Food Dive":        "https://www.fooddive.com/feeds/news/",
    "New Hope Network": "https://www.newhope.com/rss.xml",
    "SPINS Insights":   "https://www.spins.com/feed/",
}


# ---------------------------------------------------------------------------
# BASE CLASS
# ---------------------------------------------------------------------------

class BaseCollector(ABC):
    """Abstract base for all data source collectors."""

    name: str  # set by each subclass

    @abstractmethod
    def collect(self) -> list[dict]:
        """Fetch signals from this source and return a list of raw signal dicts."""


# ---------------------------------------------------------------------------
# SOURCE 1 — Google Trends
# ---------------------------------------------------------------------------

class GoogleTrendsCollector(BaseCollector):
    name = "google_trends"

    def __init__(self, keywords=None, timeframe="today 3-m"):
        self.keywords  = keywords or SEED_TERMS
        self.timeframe = timeframe

    # -- cache helpers --

    @staticmethod
    def _load_cache():
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

    @staticmethod
    def _save_cache(signals):
        try:
            with open(CACHE_FILE, "w", encoding="utf-8") as f:
                json.dump({"saved_at": datetime.now().isoformat(), "signals": signals}, f)
        except Exception:
            pass

    def collect(self) -> list[dict]:
        try:
            from pytrends.request import TrendReq
        except ImportError:
            print("[collectors] pytrends not installed — skipping Google Trends.")
            return []

        cached = self._load_cache()
        if cached is not None:
            return cached

        pytrends = TrendReq(hl="en-US", tz=360, timeout=(10, 25), retries=2, backoff_factor=0.5)
        signals  = []

        for i in range(0, len(self.keywords), 5):
            batch = self.keywords[i:i + 5]
            try:
                pytrends.build_payload(batch, timeframe=self.timeframe, geo="US")

                interest_df = pytrends.interest_over_time()
                if not interest_df.empty:
                    for term in batch:
                        if term not in interest_df.columns:
                            continue
                        series = interest_df[term]
                        recent = series.iloc[-4:]
                        older  = series.iloc[-16:-4]
                        growth_pct = (
                            int(((recent.mean() - older.mean()) / older.mean()) * 100)
                            if older.mean() > 0 else 0
                        )
                        if series.mean() > 0:
                            signals.append({
                                "source":       "google_trends",
                                "term":         term,
                                "signal_value": growth_pct,
                                "snippet": (
                                    f"Google Trends: '{term}' avg interest={series.mean():.1f}/100, "
                                    f"growth {growth_pct:+d}% (last 4 wks vs prior 12)"
                                ),
                                "timestamp": datetime.now().isoformat(),
                                "metadata": {
                                    "timeframe":   self.timeframe,
                                    "query_type":  "interest_over_time",
                                    "avg_interest": round(float(series.mean()), 1),
                                },
                            })

                related = pytrends.related_queries()
                for term in batch:
                    rising_df = (related.get(term) or {}).get("rising")
                    if rising_df is None or rising_df.empty:
                        continue
                    for _, row in rising_df.head(5).iterrows():
                        signals.append({
                            "source":       "google_trends",
                            "term":         str(row["query"]),
                            "signal_value": min(int(row["value"]), 5000),
                            "snippet": (
                                f"Google Trends rising query: '{row['query']}' "
                                f"+{row['value']}% (related to '{term}')"
                            ),
                            "timestamp": datetime.now().isoformat(),
                            "metadata": {"parent_term": term, "query_type": "rising_related"},
                        })

                time.sleep(2.0)
            except Exception as exc:
                print(f"[collectors/google_trends] batch {batch}: {exc}")
                time.sleep(5.0)
                continue

        self._save_cache(signals)
        return signals


# ---------------------------------------------------------------------------
# SOURCE 2 — Reddit
# ---------------------------------------------------------------------------

class RedditCollector(BaseCollector):
    name = "reddit"

    def __init__(self, subreddits=None, post_limit=75, days_back=30):
        self.subreddits = subreddits or FOOD_WELLNESS_SUBREDDITS
        self.post_limit = post_limit
        self.days_back  = days_back

    def collect(self) -> list[dict]:
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

        cutoff  = datetime.now() - timedelta(days=self.days_back)
        signals = []

        for sub_name in self.subreddits:
            try:
                for post in reddit.subreddit(sub_name).new(limit=self.post_limit):
                    created = datetime.fromtimestamp(post.created_utc)
                    if created < cutoff:
                        continue
                    signals.append({
                        "source":       "reddit",
                        "term":         post.title,
                        "signal_value": post.score,
                        "snippet": (
                            f"r/{sub_name}: '{post.title[:80]}' — "
                            f"{post.score} upvotes, {post.num_comments} comments"
                        ),
                        "timestamp": created.isoformat(),
                        "metadata": {
                            "subreddit":    sub_name,
                            "upvote_ratio": post.upvote_ratio,
                            "num_comments": post.num_comments,
                            "url":          f"https://reddit.com{post.permalink}",
                        },
                    })
                time.sleep(0.6)
            except Exception as exc:
                print(f"[collectors/reddit] r/{sub_name}: {exc}")
                continue

        return signals


# ---------------------------------------------------------------------------
# SOURCE 3 — Trade Publication RSS
# ---------------------------------------------------------------------------

class RSSCollector(BaseCollector):
    name = "rss"

    def __init__(self, feed_urls=None, days_back=90):
        self.feed_urls = feed_urls or TRADE_RSS_FEEDS
        self.days_back = days_back

    def collect(self) -> list[dict]:
        try:
            import feedparser
        except ImportError:
            print("[collectors] feedparser not installed — skipping RSS.")
            return []

        cutoff  = datetime.now() - timedelta(days=self.days_back)
        signals = []
        feeds   = self.feed_urls

        for feed_name, url in (feeds.items() if isinstance(feeds, dict) else enumerate(feeds)):
            try:
                feed         = feedparser.parse(url)
                display_name = feed.feed.get("title", str(feed_name))

                for entry in feed.entries:
                    published = (
                        datetime(*entry.published_parsed[:6])
                        if hasattr(entry, "published_parsed") and entry.published_parsed
                        else datetime.now()
                    )
                    if published < cutoff:
                        continue

                    title   = entry.get("title", "")
                    summary = entry.get("summary", "")
                    signals.append({
                        "source":       "rss",
                        "term":         title,
                        "signal_value": 1,
                        "snippet":      f"{display_name}: '{title[:80]}' — {summary[:100]}",
                        "timestamp":    published.isoformat(),
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
# SOURCE 4 — Amazon Movers & Shakers
# ---------------------------------------------------------------------------

class AmazonMoversCollector(BaseCollector):
    name = "amazon_movers"

    CATEGORY_URLS = {
        "Grocery & Gourmet Food": "https://www.amazon.com/gp/movers-and-shakers/grocery/",
        "Health & Household":     "https://www.amazon.com/gp/movers-and-shakers/hpc/",
    }

    HEADERS = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0.0.0 Safari/537.36"
        ),
        "Accept-Language": "en-US,en;q=0.9",
        "Accept":          "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    }

    def collect(self) -> list[dict]:
        try:
            import re
            import requests
            from bs4 import BeautifulSoup
        except ImportError:
            print("[collectors] requests/beautifulsoup4 not installed — skipping Amazon.")
            return []

        signals = []
        for category_name, url in self.CATEGORY_URLS.items():
            try:
                resp = requests.get(url, headers=self.HEADERS, timeout=15)
                if resp.status_code != 200:
                    print(f"[collectors/amazon] HTTP {resp.status_code} for '{category_name}'")
                    continue

                soup  = BeautifulSoup(resp.text, "html.parser")
                items = soup.find_all("div", attrs={"data-asin": True})[:20]

                if not items:
                    print(f"[collectors/amazon] No items for '{category_name}' — layout may have changed.")
                    continue

                for item in items:
                    rank_el  = item.find(class_=re.compile(r"zg-bdg-text"))
                    rank_now = int(rank_el.get_text(strip=True).replace("#", "")) if rank_el else 0

                    name = ""
                    for a in item.find_all("a", href=re.compile(r"/dp/")):
                        t = a.get_text(strip=True)
                        if len(t) > 20 and not t.startswith("$"):
                            name = t[:80]
                            break
                    if not name:
                        continue

                    full_text = item.get_text(separator=" ", strip=True)
                    rank_info = re.search(r"Sales rank: \d[\d,]* \([^)]+\)", full_text)
                    meta_txt  = rank_info.group(0) if rank_info else ""

                    if re.search(r"\bdown\b", full_text, re.IGNORECASE) and not meta_txt:
                        continue

                    was_match = re.search(r"was\s+([\d,]+)", meta_txt)
                    if was_match:
                        signal_val = int(was_match.group(1).replace(",", "")) - rank_now
                    elif "previously unranked" in meta_txt.lower():
                        signal_val = 999
                    else:
                        signal_val = 0

                    signals.append({
                        "source":       "amazon_movers",
                        "term":         name,
                        "signal_value": signal_val,
                        "snippet": (
                            f"Amazon {category_name} #{rank_now}: "
                            f"'{name[:60]}' — {meta_txt}"
                        ),
                        "timestamp": datetime.now().isoformat(),
                        "metadata": {
                            "rank":        rank_now,
                            "category":    category_name,
                            "rank_change": meta_txt,
                        },
                    })

                time.sleep(3.0)
            except Exception as exc:
                print(f"[collectors/amazon] '{category_name}': {exc}")
                continue

        return signals


# ---------------------------------------------------------------------------
# SOURCE 5 — FDA GRAS Notices
# ---------------------------------------------------------------------------

class FDAGRASCollector(BaseCollector):
    name = "fda_gras"

    URL = (
        "https://www.cfsanappsexternal.fda.gov/scripts/fdcc/"
        "index.cfm?set=GRASNotices&sort=GRN_No&order=DESC&startrow=1&type=basic&search="
    )

    def __init__(self, days_back=365):
        self.days_back = days_back

    def collect(self) -> list[dict]:
        try:
            import requests
            from bs4 import BeautifulSoup
        except ImportError:
            print("[collectors] requests/beautifulsoup4 not installed — skipping FDA GRAS.")
            return []

        signals = []
        cutoff  = datetime.now() - timedelta(days=self.days_back)

        try:
            resp = requests.get(
                self.URL, timeout=20,
                headers={"User-Agent": "POP_TrendIntelligence/1.0 (hackathon, read-only)"},
            )
            if resp.status_code != 200:
                print(f"[collectors/fda_gras] HTTP {resp.status_code}")
                return []

            soup = BeautifulSoup(resp.text, "html.parser")
            rows = soup.select("table.fdatable tr, table tr")[1:]

            for row in rows[:60]:
                cols = row.select("td")
                if len(cols) < 3:
                    continue

                substance = cols[1].get_text(strip=True)
                if not substance:
                    continue
                date_str = cols[2].get_text(strip=True)

                try:
                    notice_date = datetime.strptime(date_str, "%m/%d/%Y")
                except ValueError:
                    notice_date = datetime.now()

                if notice_date < cutoff:
                    continue

                signals.append({
                    "source":       "fda_gras",
                    "term":         substance,
                    "signal_value": 1,
                    "snippet": (
                        f"FDA GRAS Notice: '{substance}' cleared {date_str} — "
                        f"ingredient entering U.S. food market"
                    ),
                    "timestamp": notice_date.isoformat(),
                    "metadata":  {"notice_date": date_str, "fda_status": "GRAS_cleared"},
                })

        except Exception as exc:
            print(f"[collectors/fda_gras] {exc}")

        return signals


# ---------------------------------------------------------------------------
# AGGREGATE — run all collectors
# ---------------------------------------------------------------------------

def collect_all(collectors=None) -> list[dict]:
    """
    Run all five collectors and return a combined raw signal list.
    Accepts an optional list of BaseCollector instances for custom runs.
    """
    active = collectors or [
        GoogleTrendsCollector(),
        RedditCollector(),
        RSSCollector(),
        AmazonMoversCollector(),
        FDAGRASCollector(),
    ]

    all_signals = []
    for collector in active:
        label = getattr(collector, "name", type(collector).__name__)
        print(f"[collectors] Collecting {label}...")
        try:
            batch = collector.collect()
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
