"""
Run this to see exactly which collector is failing and why.
    python debug_collectors.py
"""

print("=" * 60)
print("CHECKING INSTALLED PACKAGES")
print("=" * 60)

packages = {
    "pytrends":       "from pytrends.request import TrendReq",
    "praw":           "import praw",
    "feedparser":     "import feedparser",
    "requests":       "import requests",
    "beautifulsoup4": "from bs4 import BeautifulSoup",
}
for name, stmt in packages.items():
    try:
        exec(stmt)
        print(f"  OK  {name}")
    except ImportError:
        print(f"  MISSING  {name}  <-- pip install {name}")

print()
print("=" * 60)
print("TEST 1 — GOOGLE TRENDS (no credentials needed)")
print("=" * 60)
try:
    from pytrends.request import TrendReq
    pt = TrendReq(hl="en-US", tz=360, timeout=(10, 25))
    pt.build_payload(["mushroom coffee"], timeframe="today 3-m", geo="US")
    df = pt.interest_over_time()
    if df.empty:
        print("  WARNING: interest_over_time() returned empty DataFrame")
        print("  This usually means the term has too little data or Google is rate-limiting.")
    else:
        print(f"  OK: got {len(df)} rows of interest data")
        print(f"  Sample: {df['mushroom coffee'].tail(3).to_dict()}")

    related = pt.related_queries()
    rising = related.get("mushroom coffee", {}).get("rising")
    if rising is None or rising.empty:
        print("  WARNING: related_queries() rising returned empty — this is common.")
    else:
        print(f"  OK: {len(rising)} rising related queries found")
        print(f"  Top 3: {rising.head(3)[['query','value']].to_dict('records')}")
except Exception as e:
    print(f"  FAILED: {e}")

print()
print("=" * 60)
print("TEST 2 — REDDIT CREDENTIALS")
print("=" * 60)
import os
client_id     = os.environ.get("REDDIT_CLIENT_ID")
client_secret = os.environ.get("REDDIT_CLIENT_SECRET")
print(f"  REDDIT_CLIENT_ID     = {'SET (' + client_id[:4] + '...)' if client_id else 'NOT SET'}")
print(f"  REDDIT_CLIENT_SECRET = {'SET' if client_secret else 'NOT SET'}")
if client_id and client_secret:
    try:
        import praw
        reddit = praw.Reddit(
            client_id=client_id,
            client_secret=client_secret,
            user_agent="POP_TrendIntelligence/1.0 (debug)",
        )
        posts = list(reddit.subreddit("supplements").new(limit=3))
        print(f"  OK: fetched {len(posts)} posts from r/supplements")
        for p in posts:
            print(f"    - '{p.title[:60]}'")
    except Exception as e:
        print(f"  FAILED: {e}")
else:
    print("  SKIPPED (credentials not set)")

print()
print("=" * 60)
print("TEST 3 — RSS FEEDS (no credentials needed)")
print("=" * 60)
try:
    import feedparser
    feeds = {
        "Food Navigator USA": "https://www.foodnavigator-usa.com/rss/feed.rss",
        "New Hope Network":   "https://www.newhope.com/rss.xml",
        "Nutritional Outlook": "https://www.nutritionaloutlook.com/rss/news",
    }
    for name, url in feeds.items():
        try:
            feed = feedparser.parse(url)
            print(f"  {name}: {len(feed.entries)} articles — ", end="")
            if feed.entries:
                print(f"latest: '{feed.entries[0].title[:50]}'")
            else:
                print("EMPTY (feed URL may have changed)")
        except Exception as e:
            print(f"  {name}: FAILED — {e}")
except ImportError:
    print("  feedparser not installed")

print()
print("=" * 60)
print("TEST 4 — AMAZON MOVERS (scraping, may be blocked)")
print("=" * 60)
try:
    import requests
    from bs4 import BeautifulSoup
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0.0.0 Safari/537.36"
        )
    }
    resp = requests.get(
        "https://www.amazon.com/gp/movers-and-shakers/grocery/",
        headers=headers, timeout=15
    )
    print(f"  HTTP status: {resp.status_code}")
    if resp.status_code == 200:
        soup  = BeautifulSoup(resp.text, "html.parser")
        items = soup.select(".zg-item-immersion")
        print(f"  Found {len(items)} items with selector '.zg-item-immersion'")
        if not items:
            # Try alternate selectors
            alt = soup.select(".p13n-desktop-grid")
            print(f"  Alt selector '.p13n-desktop-grid': {len(alt)} items")
            print("  Amazon may have changed their layout or is blocking the request.")
    else:
        print("  Amazon is blocking the request (rate limit / captcha).")
except Exception as e:
    print(f"  FAILED: {e}")

print()
print("=" * 60)
print("TEST 5 — FDA GRAS (no credentials needed)")
print("=" * 60)
try:
    import requests
    from bs4 import BeautifulSoup
    resp = requests.get(
        "https://www.accessdata.fda.gov/scripts/fdcc/"
        "index.cfm?set=GRASNotices&sort=GRN_No&order=DESC&startrow=1&type=basic&search=",
        timeout=20,
        headers={"User-Agent": "POP_TrendIntelligence/1.0 (debug)"},
    )
    print(f"  HTTP status: {resp.status_code}")
    if resp.status_code == 200:
        soup = BeautifulSoup(resp.text, "html.parser")
        rows = soup.select("table tr")
        print(f"  Found {len(rows)} table rows")
        if rows:
            first_cols = rows[1].select("td") if len(rows) > 1 else []
            print(f"  First data row has {len(first_cols)} columns")
            if first_cols:
                print(f"  Sample: {[c.get_text(strip=True)[:30] for c in first_cols[:4]]}")
    else:
        print("  FDA site returned non-200 status.")
except Exception as e:
    print(f"  FAILED: {e}")

print()
print("=" * 60)
print("DIAGNOSIS COMPLETE")
print("=" * 60)
