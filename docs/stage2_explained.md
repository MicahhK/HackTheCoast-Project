# Stage 2 Explained — How Trend Normalization Works micahhhhh ily 

This document explains what `core_discovery.py` actually does in plain terms, why each decision was made, and what the output numbers mean.

---

## The Problem Stage 2 Solves

Stage 1 gives us 185 raw signals that look like this:

```
[google_trends] "mushroom coffee"         value=8     (growth %)
[google_trends] "mushroom coffee benefits" value=3250  (rising related query)
[rss]           "Matcha-do about matcha..."value=1     (article presence)
[amazon_movers] "PBfit Peanut Butter..."   value=999   (rank jump)
[fda_gras]      "chia seeds extract"       value=1     (GRAS clearance)
```

These 185 signals are messy and incompatible — different units, different sources, different granularity. Stage 2 turns them into 18 clean, comparable trend objects that Stage 3 can score consistently.

---

## Step 1 — Matching Signals to Trends (Keyword Extraction)

**Function:** `extract_mentions(signals)`

Stage 2 has a hardcoded **Ingredient Catalog** of 18 trend candidates POP cares about. Each entry has a list of aliases — every way that trend might appear in raw text.

```
"Lion's Mane Mushroom" aliases:
  lion's mane, lions mane, hericium, lion's mane coffee,
  lion's mane mushroom, lions mane mushroom
```

For every signal, Stage 2 concatenates `term + snippet` into one lowercase string and checks whether any alias appears in it. If yes, that signal is filed under the trend's canonical name.

**Why aliases?** The same ingredient appears differently across sources:
- Google Trends uses your exact query: `"lion's mane"`
- Reddit might say: `"anyone tried lions mane mushroom?"`
- New Hope Network might write: `"Hericium extract drives nootropic category"`

Without aliases, all three would be missed or counted separately.

**One signal, one trend.** A signal can only match one alias per trend (no double-counting within a trend). But a signal can match multiple different trends — an article about "turmeric ginger mushroom coffee" contributes to both Turmeric Ginger Latte and Mushroom Coffee.

---

## Step 2 — Growth Rate

**Function:** `compute_growth_rate(signals)`

Answers: *Is this trend growing right now?*

**Source priority:**
1. **Google Trends interest_over_time** — the seed term's actual search trajectory over the last 3 months (% change, last 4 weeks vs prior 12)
2. **Amazon rank jump** — if no Google Trends data, converts rank positions jumped into a rough % equivalent (jump × 2, capped at 200%)

**Critical design choice:** Rising related queries from Google Trends are intentionally excluded here. When you search "mushroom coffee" in Google Trends, it also returns related queries like "mushroom coffee benefits" at +3250%. That +3250% describes a sub-term, not the parent trend. Including it would make "Mushroom Coffee" look like it's growing 3250% when it's actually growing 8%.

```
Mushroom Coffee:
  interest_over_time signal:  +8%    ← growth_rate_pct = 8
  rising related query:    +3250%    ← ignored here, counted in rising_query_count
```

---

## Step 3 — Recency Score (0–1)

**Function:** `compute_recency_score(signals)`

Answers: *Is the trend window still open, or did we miss it?*

Uses the same interest_over_time signals as growth rate:

```
recency_score = (avg_iot_growth + 100) / 300

+200% growth  →  1.00  (window wide open, accelerating)
  +0% growth  →  0.33  (flat, still alive but not climbing)
−100% growth  →  0.00  (dead, window closed)
```

**Why exclude rising related queries here too?**
Rising queries describe sub-terms that are breakout. "Elderberry gummies" being breakout (+5000%) doesn't tell us if the parent "elderberry syrup" category window is still open. It just tells us a specific product format is hot. That's useful context, but it shouldn't inflate the recency score of the parent trend.

**A flat trend (0.33) isn't neutral — it's actually slightly negative.** We mapped 0.5 to a healthy +50% growth. Flat means the trend has matured and the window is narrowing, even if it hasn't reversed yet.

---

## Step 3b — Rising Query Count

**Function:** `count_rising_queries(signals)`

Answers: *Is this trend spawning sub-categories?*

Counts how many Google Trends "rising related queries" matched this trend. A rising query is a search term that's accelerating in volume relative to the seed term.

This is a separate field from growth rate because it tells a different story:

| Trend | Base Growth | Rising Queries | What it means |
|---|---|---|---|
| Ginger Shot | −6% | 4 | Base market maturing, but specific brands/formats still early |
| Mushroom Coffee | +8% | 1 | Growing category with one dominant sub-query |
| Pandan | +12% | 0 | Growing but no sub-term fragmentation yet — very early |
| Peanut Butter Powder | — | 0 | Amazon-only data, no GT coverage |

Ginger Shot at −6% base growth with 4 rising queries is actually an interesting DEVELOP signal for POP — the generic market is maturing, but "organic ginger shot" (+130%) and branded variants are still early. POP could develop a premium variant.

---

## Step 3c — Absolute GT Interest

**Function:** `compute_avg_interest(signals)`

Answers: *How big is this market actually?*

Google Trends reports search interest on a 0–100 scale normalized to the peak in your timeframe. It doesn't tell you raw search volume — just relative interest.

This field (`avg_gt_interest`) is critical for distinguishing:

| Trend | Growth | GT Interest | Reality |
|---|---|---|---|
| Mushroom Coffee | +8% | 61/100 | Large growing market |
| Pandan | +12% | 9/100 | Tiny but climbing — very early stage |
| Ashwagandha | −18% | 31/100 | Large market declining — mainstream saturation |

Without absolute interest, Pandan (+12%, niche) would look better than Mushroom Coffee (+8%, mainstream). For POP's DISTRIBUTE decision, a 61/100 declining category might still be more worth entering than a 9/100 growing one.

---

## Step 4 — Competition Density (0–1)

**Function:** `compute_competition_density(signals)`

Answers: *How crowded is the Amazon shelf right now?*

Built from Amazon Movers & Shakers rank. We scrape the top 20 per category, so we normalize against that range:

```
density = 1.0 − ((rank − 1) / 19)

Rank  1  →  0.95  (most crowded — product is already dominant)
Rank 10  →  0.53  (moderate competition)
Rank 20  →  0.05  (wide open — almost no shelf presence)
```

No Amazon data → 0.5 (assume moderate, unknown).

**A crowded shelf (high density) isn't automatically bad.** It means there's proven demand. For DISTRIBUTE, a crowded shelf with a rising product means the category is real. For DEVELOP, you want a less crowded shelf.

---

## Step 5 — Assembling the Trend Object

**Function:** `normalize(signals)` — main Stage 2 entry point

For each catalog entry that has at least one matched signal, Stage 2 builds a complete trend object combining all the above. The evidence field keeps the top 5 signals by signal_value so buyers can see exactly what drove the score.

**Sort order:** Source count descending → growth rate descending. A trend appearing in Google Trends + RSS + Amazon is ranked above one that only appeared in Google Trends, because corroboration across independent sources reduces the chance of a false signal.

---

## What the Numbers Look Like

Current output from live data (April 2026):

```
Trend                    Src    Growth  Recency  Compete  GT Int  Rising
------------------------------------------------------------------------
Collagen Peptides     AMZ,GT      +9%     0.36     0.42      19       0
Peanut Butter Powder     AMZ    +200%     0.50     0.95       —       0
Tempeh                    GT     +28%     0.43     0.50      11       0
Mushroom Coffee           GT      +8%     0.36     0.50      61       1
Lion's Mane Mushroom      GT      −5%     0.32     0.50      54       2
Ginger Shot               GT      −6%     0.31     0.50      26       4
Ube (Purple Yam)          GT     −20%     0.27     0.50      24       1
```

**How to read this:**

- **Collagen Peptides** — two sources (best corroboration in this run), moderate GT interest, wide-open Amazon shelf. Worth watching.
- **Peanut Butter Powder** — Amazon-only signal. #1 on Movers & Shakers (density 0.95 = very crowded). Not a new trend — a dominant product already on shelf.
- **Tempeh** — fastest real growth in the catalog (+28% seed term), but tiny absolute interest (11/100). Very early stage, niche. POP's Indonesian supply chain is an advantage here.
- **Mushroom Coffee** — largest absolute market (61/100), +8% growth, 1 rising sub-query. A large, still-growing category.
- **Ginger Shot** — base term declining (−6%) but 4 rising related queries. The generic market is maturing but premium/branded variants are early. Strong DEVELOP candidate for POP given their ginger supply chain.
- **Ube** — declining base (−20%) with 1 rising query. May have peaked — but "ube powder" as a format sub-term still has momentum.

---

## Known Limitations

1. **Keyword matching only.** "Lion's mane latte from Trader Joe's" matches Lion's Mane Mushroom even if it's describing a different product. NLP entity extraction would improve precision but was out of scope.

2. **No cross-catalog disambiguation.** An article about "mushroom coffee with lion's mane" matches both Mushroom Coffee and Lion's Mane Mushroom. That's intentional — it's evidence for both — but it means source counts can be correlated rather than independent.

3. **Amazon coverage depends on page scraping.** Amazon changes their HTML layout periodically. When selectors break, all trends lose their Amazon competition signal and default to 0.5 density until the scraper is fixed.

4. **No source quality weighting.** An RSS article from SPINS (industry data company) counts the same as one from a general food blog. A future improvement would weight SPINS/Nielsen/Circana coverage higher.

5. **Reddit is offline without credentials.** Once connected, upvote scores from r/supplements, r/nootropics, r/asianfood etc. would add a consumer sentiment layer that trade press can't capture.

---

## Running Tests

```bash
source venv/bin/activate
pytest tests/test_stage2.py -v
```

45 tests covering every function: alias matching, growth rate isolation, recency score formula, rising query counting, competition density normalization, and full normalize() integration.
