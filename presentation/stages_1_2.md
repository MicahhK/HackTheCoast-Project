# HackTheCoast 2026 — Presentation Script
## Stages 1 & 2: Data Collection + Trend Identification
### Target runtime: ~7 minutes

---

## SLIDE 1 — The Problem (0:00–0:45)

**Speaker:**

Prince of Peace has been in this business for over 40 years. They know health foods. They know ginger. They know their customers. But here's a problem that expertise alone can't solve:

In 2023, ube was blowing up. Pinterest boards, TikTok videos, bubble tea shops everywhere. POP spotted it. But by the time they found an FDA-compliant supplier — one that met their shelf life, ingredient, and sourcing standards — the window had closed. Competitors had already filled the shelf.

The same thing happened with tempeh chips.

The trend wasn't the problem. **The lag was.**

So the question we asked ourselves was: what if we could automate the spotting — and give the buying team a head start before the shelf is already full?

---

## SLIDE 2 — Our Approach: A 3-Stage Pipeline (0:45–1:30)

**Speaker:**

We built a trend intelligence pipeline with three stages.

Think of it like a funnel. Stage 1 casts a wide net across public data sources and collects raw signals — thousands of data points from across the internet. Stage 2 takes that noise and turns it into something meaningful: normalized, ranked trend objects. And Stage 3 — which we'll get to — applies POP's actual business rules and tells the buying team: distribute this, or develop that.

Today we're going to walk you through the first two stages — the engine under the hood.

---

## SLIDE 3 — Stage 1: Where We Listen (1:30–3:00)

**Speaker:**

Stage 1 is our data collection layer, built in `collectors.py`. We pull from three public sources — no paid APIs, no proprietary data.

**Google Trends** is our backbone. We watch 20 seed terms that POP actually cares about — things like "lion's mane," "ashwagandha gummy," "ube latte," "ginger shot." We batch them in groups of five — that's a hard pytrends limit — and compare the last four weeks of search interest against the prior twelve. That gives us a real growth rate, not just a snapshot. We also capture *rising related queries*, which is how we catch terms we didn't think to ask about. Lion's mane leads us to "lion's mane coffee," which we might not have seeded. That's the system surfacing signals on its own.

**RSS feeds** from four trade publications — Food Dive, Natural Products Insider, Food Navigator USA, Nutritional Outlook. These are the same publications POP's buyers would read at a trade show. We pull headlines and article summaries from the last 90 days. The signal here isn't a number — it's frequency. If an ingredient shows up in three articles in two weeks, something is happening.

**Amazon Movers & Shakers** — the public grocery and health pages that show which products jumped the fastest in rank. A product going from #80 to #5 in a week is a strong retail signal. We capture the rank delta and treat it as a demand indicator.

Every signal from every source comes out in a consistent schema: source, term, signal value, a human-readable snippet, a timestamp, and source-specific metadata. That uniformity is what lets Stage 2 work.

---

## SLIDE 4 — Stage 1: What We Get Out (3:00–3:45)

**Speaker:**

A typical run produces 50–80 raw signals. Here's an example of what that looks like:

> `[google_trends] lion's mane | value=+142% | 2026-04-17`
> `[rss] "Mushroom coffee sees 3rd consecutive quarter of growth" — Food Dive`
> `[amazon_movers] Host Defense MyCommunity Capsules | rank: #3 (was #41)`

Three different sources. Three different formats. All pointing at the same thing: functional mushrooms are moving.

But raw signals aren't decisions. That's Stage 2's job.

---

## SLIDE 5 — Stage 2: From Noise to Trends (3:45–5:15)

**Speaker:**

Stage 2 is our normalization engine, built in `core_discovery.py`. It answers one question: *which ingredient is this signal actually about?*

We maintain an ingredient catalog of 20 entries — every ingredient or product type POP might care about. Each entry has a canonical name, a list of aliases, a product category, and source country. So "lions mane mushroom," "lion's mane coffee," and "hericium" all collapse into one trend: **Lion's Mane Mushroom**.

That deduplication is critical. Without it, the same trend fragments across a dozen variations and looks weaker than it is.

Once we've matched signals to ingredients, we compute four things for each trend:

- **Growth rate** — pulled from Google Trends search velocity or Amazon rank delta
- **Recency score** — is this trend accelerating or plateauing? A rising growth rate means the window is still open.
- **Competition density** — how crowded is the shelf? High Amazon rank = crowded. No Amazon signal = unknown, we default to moderate.
- **Cross-source count** — how many of our three sources flagged this ingredient? One source is noise. Three sources is a signal.

The output is a ranked list of trend objects, sorted first by how many sources corroborated them, then by growth rate. Here's a sample of what Stage 2 hands off:

| Trend | Sources | Growth | Recency | Competition |
|---|---|---|---|---|
| Lion's Mane Mushroom | GT, RSS, AMZ | +142% | 0.81 | 0.42 |
| Ashwagandha | GT, RSS | +89% | 0.74 | 0.55 |
| Ube (Purple Yam) | GT, RSS | +63% | 0.69 | 0.28 |
| Ginger Shot | GT, AMZ | +38% | 0.61 | 0.67 |

---

## SLIDE 6 — Why This Matters for POP Specifically (5:15–6:00)

**Speaker:**

We didn't build a generic trend scanner. We built one for POP.

The seed terms we chose, the subreddits we watch, the ingredient catalog we built — they all reflect POP's actual product lines. Ginger. Ginseng. Herbal teas. Asian specialty formats. We're not watching craft beer trends or fresh produce. We're watching the space where POP competes.

And POP has an asymmetric advantage here that most U.S. distributors don't. They already understand authentic Asian markets. Pandan, yuzu, ube — these are products established in Southeast Asia that haven't crossed over to mainstream U.S. retail yet. Our pipeline is specifically designed to catch those before they do.

When lion's mane shows up in three sources and ube is growing at 63% with low competition density — that's not just data. That's a buying team conversation waiting to happen.

---

## SLIDE 7 — The Handoff (6:00–7:00)

**Speaker:**

So by the end of Stage 2, we have a clean, ranked list of trends. Each one has a name, a category, a source country, a list of ingredients, and four computed signals.

But we haven't answered the question POP actually needs answered.

*Is this something we can even source?* Does it pass POP's 12-month shelf life requirement? Does it have any FDA-restricted ingredients? Is the primary source country locked under trade restrictions?

And once it clears compliance: *should POP distribute an existing brand — or develop a new product of their own?*

That's the decision layer. And that's exactly what Stage 3 is built to do.

---

*[End of Stages 1 & 2 — hand off to Stage 3 presenter]*
