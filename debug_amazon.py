"""
Fetches Amazon Movers & Shakers and prints the HTML structure
so we can identify the correct current CSS selectors.
Run: python debug_amazon.py
"""
import requests
from bs4 import BeautifulSoup

url = "https://www.amazon.com/gp/movers-and-shakers/grocery/"
headers = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}

print("Fetching Amazon Movers & Shakers...")
resp = requests.get(url, headers=headers, timeout=15)
print(f"HTTP status: {resp.status_code}")

soup = BeautifulSoup(resp.text, "html.parser")

# Try known selector variations
selectors = [
    ".zg-item-immersion",
    ".p13n-gridRow .a-section",
    "[data-p13n-asin-metadata]",
    ".zg-grid-general-faceout",
    "#zg-ordered-list li",
    ".a-ordered-list .a-list-item",
]
for sel in selectors:
    found = soup.select(sel)
    print(f"  {sel!r:45s} -> {len(found)} elements")

# Print a chunk of raw HTML around the product list so we can spot the structure
print("\n--- RAW HTML SAMPLE (first 3000 chars of body) ---")
body = soup.find("body")
if body:
    print(body.get_text(separator="\n", strip=True)[:2000])
