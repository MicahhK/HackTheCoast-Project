"""
Stage 2 - Trend Identification (core_discovery.py)

Takes raw signals from collectors.py and outputs normalized trend objects
ready for scoring.py (Stage 3).

Pipeline:
  1. Scan every signal's text for known ingredient/product keywords
  2. Group matching signals under one canonical trend name (deduplication)
  3. Count how many distinct sources flagged each trend (cross-source strength)
  4. Compute growth rate, recency score, and competition density
  5. Return sorted list of trend objects
"""


# ---------------------------------------------------------------------------
# INGREDIENT CATALOG
# Every trend POP might care about. Each entry has:
#   - name:                  canonical display name
#   - aliases:               strings to match in signal text (case-insensitive)
#   - category:              POP focus bucket
#   - format:                product format (used by scoring for shelf-life check)
#   - key_ingredients:       short list for POP-Fit matching in Stage 3
#   - ingredients:           full list for FDA compliance check in Stage 3
#   - primary_source_country used for trade risk check in Stage 3
# ---------------------------------------------------------------------------

INGREDIENT_CATALOG = [
    # -- POP existing strengths and direct adjacencies --
    {
        "name": "Ginger Shot",
        "aliases": ["ginger shot", "ginger shots", "ginger wellness", "organic ginger shot",
                    "lemon ginger shot", "vive ginger"],
        "category": "functional beverage",
        "format": "ready-to-drink bottle",
        "key_ingredients": ["ginger", "wellness shot"],
        "ingredients": ["ginger", "lemon", "turmeric"],
        "primary_source_country": "USA",
    },
    {
        "name": "Turmeric Ginger Latte",
        "aliases": ["turmeric ginger", "turmeric latte", "golden milk", "turmeric shot"],
        "category": "functional beverage",
        "format": "instant powder",
        "key_ingredients": ["turmeric", "ginger"],
        "ingredients": ["turmeric", "ginger", "black pepper", "coconut milk powder"],
        "primary_source_country": "India",
    },
    {
        "name": "Manuka Honey",
        "aliases": ["manuka honey", "manuka", "honey wellness", "honey syrup"],
        "category": "functional food",
        "format": "shelf-stable beverage",
        "key_ingredients": ["manuka honey", "honey", "immunity"],
        "ingredients": ["manuka honey", "ginger", "propolis"],
        "primary_source_country": "New Zealand",
    },
    {
        "name": "Ginseng Supplement",
        "aliases": ["ginseng supplement", "american ginseng", "ginseng", "ginseng tea"],
        "category": "health & wellness",
        "format": "supplement / capsule",
        "key_ingredients": ["american ginseng", "ginseng", "adaptogen"],
        "ingredients": ["american ginseng root extract"],
        "primary_source_country": "USA",
    },
    {
        "name": "Elderberry",
        "aliases": ["elderberry", "elderberry syrup", "elderberry immunity", "elderberry gummy"],
        "category": "functional beverage",
        "format": "shelf-stable beverage",
        "key_ingredients": ["elderberry", "immunity", "honey"],
        "ingredients": ["elderberry extract", "honey", "zinc"],
        "primary_source_country": "USA",
    },

    # -- Functional mushrooms --
    {
        "name": "Lion's Mane Mushroom",
        "aliases": ["lion's mane", "lions mane", "hericium", "lion's mane coffee",
                    "lion's mane mushroom", "lions mane mushroom"],
        "category": "functional food",
        "format": "instant powder",
        "key_ingredients": ["lion's mane", "mushroom", "nootropic"],
        "ingredients": ["lion's mane mushroom extract", "coffee", "chaga"],
        "primary_source_country": "USA",
    },
    {
        "name": "Reishi Mushroom Tea",
        "aliases": ["reishi", "lingzhi", "reishi tea", "reishi mushroom"],
        "category": "functional tea",
        "format": "dry tea",
        "key_ingredients": ["reishi", "mushroom", "functional tea"],
        "ingredients": ["reishi mushroom extract", "green tea"],
        "primary_source_country": "China",
    },
    {
        "name": "Mushroom Coffee",
        "aliases": ["mushroom coffee", "cordyceps coffee", "cordyceps", "chaga coffee",
                    "functional mushroom coffee", "mud wtr", "mudwtr"],
        "category": "functional beverage",
        "format": "instant powder",
        "key_ingredients": ["cordyceps", "mushroom", "coffee", "adaptogen"],
        "ingredients": ["cordyceps mushroom", "lion's mane", "chaga", "coffee"],
        "primary_source_country": "USA",
    },
    {
        "name": "Matcha Mushroom Latte",
        "aliases": ["matcha mushroom", "matcha latte", "matcha powder", "matcha"],
        "category": "functional beverage",
        "format": "instant powder",
        "key_ingredients": ["matcha", "mushroom", "lion's mane"],
        "ingredients": ["matcha", "lion's mane", "chaga", "coconut milk powder"],
        "primary_source_country": "Japan",
    },

    # -- Adaptogens --
    {
        "name": "Ashwagandha",
        "aliases": ["ashwagandha", "ashwagandha gummy", "ashwagandha supplement",
                    "ashwagandha candy", "ashwagandha chew"],
        "category": "functional confection",
        "format": "chewy candy",
        "key_ingredients": ["ashwagandha", "adaptogen", "stress relief"],
        "ingredients": ["ashwagandha extract", "sugar", "pectin"],
        "primary_source_country": "India",
    },
    {
        "name": "Moringa",
        "aliases": ["moringa", "moringa powder", "moringa leaf", "moringa energy"],
        "category": "superfood powder",
        "format": "instant powder",
        "key_ingredients": ["moringa", "superfood", "anti-inflammatory"],
        "ingredients": ["moringa leaf powder", "spirulina", "matcha"],
        "primary_source_country": "India",
    },

    # -- Asian specialty (POP's asymmetric advantage) --
    {
        "name": "Pandan",
        "aliases": ["pandan", "pandan snack", "pandan flavor", "pandan leaf",
                    "pandan candy", "pandan chew"],
        "category": "asian specialty",
        "format": "chewy candy",
        "key_ingredients": ["pandan"],
        "ingredients": ["pandan extract", "sugar", "coconut"],
        "primary_source_country": "Thailand",
    },
    {
        "name": "Yuzu Citrus",
        "aliases": ["yuzu", "yuzu candy", "yuzu citrus", "yuzu flavor", "yuzu drink"],
        "category": "asian specialty",
        "format": "chewy candy",
        "key_ingredients": ["yuzu"],
        "ingredients": ["yuzu", "sugar", "pectin"],
        "primary_source_country": "Japan",
    },
    {
        "name": "Ube (Purple Yam)",
        "aliases": ["ube", "ube latte", "purple yam", "ube flavor", "ube powder"],
        "category": "asian specialty",
        "format": "instant powder",
        "key_ingredients": ["ube", "purple yam"],
        "ingredients": ["ube", "purple yam", "coconut milk powder"],
        "primary_source_country": "Philippines",
    },
    {
        "name": "Tempeh",
        "aliases": ["tempeh", "tempeh chips", "tempeh snack", "fermented soy tempeh"],
        "category": "plant-based snack",
        "format": "chips/crackers",
        "key_ingredients": ["tempeh", "fermented soy", "plant-based protein"],
        "ingredients": ["tempeh", "fermented soybeans", "spices"],
        "primary_source_country": "Indonesia",
    },

    # -- Protein and functional food --
    {
        "name": "Peanut Butter Powder",
        "aliases": ["peanut butter powder", "pb powder", "pbfit", "powdered peanut butter",
                    "peanut powder"],
        "category": "functional food",
        "format": "instant powder",
        "key_ingredients": ["peanut butter", "protein"],
        "ingredients": ["peanut butter powder"],
        "primary_source_country": "USA",
    },
    {
        "name": "Chia Seeds",
        "aliases": ["chia", "chia seeds", "chia seed", "organic chia"],
        "category": "functional food",
        "format": "dried fruit",
        "key_ingredients": ["chia", "omega-3", "plant-based"],
        "ingredients": ["chia seeds"],
        "primary_source_country": "Peru",
    },
    {
        "name": "Collagen Peptides",
        "aliases": ["collagen", "collagen drink", "collagen peptide", "collagen powder",
                    "bovine collagen", "marine collagen"],
        "category": "functional beverage",
        "format": "instant powder",
        "key_ingredients": ["collagen", "beauty", "gut health"],
        "ingredients": ["bovine collagen peptides", "vitamin c"],
        "primary_source_country": "USA",
    },
]


# ---------------------------------------------------------------------------
# STEP 1 — Extract ingredient mentions from signal text
# ---------------------------------------------------------------------------

def extract_mentions(signals):
    """
    Scan every signal's term + snippet for catalog aliases.
    Returns dict: { canonical_name -> [signals that mention it] }
    """
    mentions = {item["name"]: [] for item in INGREDIENT_CATALOG}

    for signal in signals:
        text = (signal.get("term", "") + " " + signal.get("snippet", "")).lower()
        for item in INGREDIENT_CATALOG:
            for alias in item["aliases"]:
                if alias.lower() in text:
                    mentions[item["name"]].append(signal)
                    break  # one match per ingredient per signal — no double-counting

    return mentions


# ---------------------------------------------------------------------------
# STEP 2 — Compute growth rate from matched signals
# ---------------------------------------------------------------------------

def compute_growth_rate(signals):
    """
    Growth rate from interest_over_time signals only (the seed term's real trajectory).
    Falls back to Amazon rank-jump if no GT interest_over_time data.
    Rising-related queries are intentionally excluded here — they inflate the number
    and are accounted for separately via rising_query_count.
    """
    iot = [s["signal_value"] for s in signals
           if s["source"] == "google_trends"
           and s["metadata"].get("query_type") == "interest_over_time"]
    amazon = [s["signal_value"] for s in signals
              if s["source"] == "amazon_movers" and s["signal_value"] > 0]

    if iot:
        return max(iot)  # best seed-term growth across batches
    if amazon:
        # Rough conversion: rank jump of 50 positions ≈ 100% demand growth; cap at 200
        return min(max(amazon) * 2, 200)
    return 0


# ---------------------------------------------------------------------------
# STEP 3 — Compute recency score (0–1)
# ---------------------------------------------------------------------------

def compute_recency_score(signals):
    """
    Uses interest_over_time signals only — these measure whether the seed term
    itself is still climbing. Rising-related queries tell us about sub-term
    velocity but not whether the window is still open on the parent trend.

    Mapping: +100% growth -> ~0.67, +200% -> 1.0, flat -> 0.5, -100% -> 0.0
    """
    iot = [s for s in signals
           if s["source"] == "google_trends"
           and s["metadata"].get("query_type") == "interest_over_time"]
    if not iot:
        return 0.5  # no GT data — neutral

    avg_growth = sum(s["signal_value"] for s in iot) / len(iot)
    score = (avg_growth + 100) / 300
    return max(0.0, min(1.0, round(score, 2)))


# ---------------------------------------------------------------------------
# STEP 3b — Count breakout rising-related queries
# ---------------------------------------------------------------------------

def count_rising_queries(signals):
    """
    Number of rising-related Google Trends queries for this trend.
    Each one is a sub-term (e.g. 'elderberry gummies') with accelerating search volume.
    High count = trend is spawning sub-categories = still early.
    """
    return sum(
        1 for s in signals
        if s["source"] == "google_trends"
        and s["metadata"].get("query_type") == "rising_related"
    )


# ---------------------------------------------------------------------------
# STEP 3c — Average absolute GT interest (0–100 scale)
# ---------------------------------------------------------------------------

def compute_avg_interest(signals):
    """
    Average absolute search interest from Google Trends interest_over_time (0–100).
    Distinguishes a declining category leader (high interest, negative growth)
    from a true niche (low interest, positive growth).
    Returns None if no GT interest_over_time data.
    """
    values = [
        s["metadata"]["avg_interest"]
        for s in signals
        if s["source"] == "google_trends"
        and s["metadata"].get("query_type") == "interest_over_time"
        and "avg_interest" in s["metadata"]
    ]
    if not values:
        return None
    return round(sum(values) / len(values), 1)


# ---------------------------------------------------------------------------
# STEP 4 — Estimate competition density (0–1)
# ---------------------------------------------------------------------------

def compute_competition_density(signals):
    """
    How crowded is the shelf?
    Based on Amazon Movers rank: low rank number = product already dominant = crowded.
    No Amazon signal = assume moderate competition (0.5).
    """
    amazon = [s for s in signals if s["source"] == "amazon_movers"]
    if not amazon:
        return 0.5

    ranks = [s["metadata"].get("rank", 15) for s in amazon]
    avg_rank = sum(ranks) / len(ranks)
    # We scrape top 20 per category — normalize against that range
    # Rank 1 -> ~0.95 (saturated), rank 20 -> ~0.05 (wide open)
    density = 1.0 - ((avg_rank - 1) / 19)
    return max(0.05, min(0.95, round(density, 2)))


# ---------------------------------------------------------------------------
# STEP 5 — Normalize: combine everything into one trend object per ingredient
# ---------------------------------------------------------------------------

def normalize(signals):
    """
    Main Stage 2 function.
    Input:  raw signal list from collectors.collect_all()
    Output: sorted list of normalized trend objects for scoring.py
    """
    mentions = extract_mentions(signals)

    trends = []
    for item in INGREDIENT_CATALOG:
        matched = mentions[item["name"]]
        if not matched:
            continue  # no signals found for this ingredient — skip

        sources     = list({s["source"] for s in matched})
        source_count = len(sources)
        evidence    = [
            {
                "source":  s["source"],
                "snippet": s["snippet"],
                "value":   s["signal_value"],
            }
            for s in sorted(matched, key=lambda x: x["signal_value"], reverse=True)[:5]
        ]

        trend = {
            # Identity
            "name":                   item["name"],
            "category":               item["category"],
            "format":                 item["format"],
            "key_ingredients":        item["key_ingredients"],
            "ingredients":            item["ingredients"],
            "primary_source_country": item["primary_source_country"],
            # Computed signals
            "growth_rate_pct":        compute_growth_rate(matched),
            "recency_score":          compute_recency_score(matched),
            "competition_density":    compute_competition_density(matched),
            "avg_gt_interest":        compute_avg_interest(matched),   # absolute GT interest 0–100
            "rising_query_count":     count_rising_queries(matched),   # breakout sub-term count
            # Evidence
            "evidence":               evidence,
            "sources":                sources,
            "source_count":           source_count,
            "signal_count":           len(matched),
        }
        trends.append(trend)

    # Sort: more sources first, then higher growth
    trends.sort(key=lambda t: (t["source_count"], t["growth_rate_pct"]), reverse=True)
    return trends


# ---------------------------------------------------------------------------
# Quick test — python core_discovery.py
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    from collectors import collect_all

    print("Running Stage 1 collectors...")
    signals = collect_all()

    print(f"\nRunning Stage 2 normalization on {len(signals)} signals...\n")
    trends = normalize(signals)

    SOURCE_ABBREV = {
        "google_trends": "GT",
        "amazon_movers": "AMZ",
        "rss":           "RSS",
        "reddit":        "RED",
        "fda_gras":      "FDA",
    }

    print(f"{len(trends)} trends identified\n")
    print(f"{'Trend':<28} {'Src':>8} {'Growth':>7} {'Recency':>8} {'Compete':>8} {'GT Int':>7} {'Rising':>7}")
    print("-" * 80)
    for t in trends:
        src_str = ",".join(SOURCE_ABBREV.get(s, s) for s in sorted(t["sources"]))
        interest = f"{t['avg_gt_interest']:.0f}" if t["avg_gt_interest"] is not None else "—"
        print(
            f"{t['name']:<28} {src_str:>8} "
            f"{t['growth_rate_pct']:>6}% "
            f"{t['recency_score']:>8.2f} "
            f"{t['competition_density']:>8.2f} "
            f"{interest:>7} "
            f"{t['rising_query_count']:>7}"
        )
