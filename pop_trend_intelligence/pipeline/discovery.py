"""
Stage 2 — Trend Identification (core_discovery.py)

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
# TREND NORMALIZER
# ---------------------------------------------------------------------------

class TrendNormalizer:
    """
    Stage 2 normalizer. Accepts an ingredient catalog on construction so it
    can be initialized with a custom catalog in tests.
    """

    def __init__(self, catalog=None):
        self.catalog = catalog if catalog is not None else INGREDIENT_CATALOG

    # -- Step 1: match signals to catalog entries --

    def extract_mentions(self, signals: list[dict]) -> dict:
        """
        Scan every signal's term + snippet for catalog aliases.
        Returns dict: { canonical_name -> [signals that mention it] }
        """
        mentions = {item["name"]: [] for item in self.catalog}

        for signal in signals:
            text = (signal.get("term", "") + " " + signal.get("snippet", "")).lower()
            for item in self.catalog:
                for alias in item["aliases"]:
                    if alias.lower() in text:
                        mentions[item["name"]].append(signal)
                        break  # one match per ingredient per signal

        return mentions

    # -- Step 2: growth rate --

    def compute_growth_rate(self, signals: list[dict]) -> int:
        """
        Growth rate from interest_over_time signals only.
        Falls back to Amazon rank-jump if no GT IOT data.
        Rising-related queries are excluded — accounted for separately.
        """
        iot    = [s["signal_value"] for s in signals
                  if s["source"] == "google_trends"
                  and s["metadata"].get("query_type") == "interest_over_time"]
        amazon = [s["signal_value"] for s in signals
                  if s["source"] == "amazon_movers" and s["signal_value"] > 0]

        if iot:
            return max(iot)
        if amazon:
            return min(max(amazon) * 2, 200)
        return 0

    # -- Step 3: recency score --

    def compute_recency_score(self, signals: list[dict]) -> float:
        """
        Uses interest_over_time signals only.
        Mapping: +200% -> 1.0, flat -> 0.5, -100% -> 0.0
        """
        iot = [s for s in signals
               if s["source"] == "google_trends"
               and s["metadata"].get("query_type") == "interest_over_time"]
        if not iot:
            return 0.5

        avg_growth = sum(s["signal_value"] for s in iot) / len(iot)
        score = (avg_growth + 100) / 300
        return max(0.0, min(1.0, round(score, 2)))

    # -- Step 3b: rising query count --

    def count_rising_queries(self, signals: list[dict]) -> int:
        """Number of rising-related Google Trends queries for this trend."""
        return sum(
            1 for s in signals
            if s["source"] == "google_trends"
            and s["metadata"].get("query_type") == "rising_related"
        )

    # -- Step 3c: average absolute GT interest --

    def compute_avg_interest(self, signals: list[dict]):
        """
        Average absolute search interest (0–100) from GT interest_over_time.
        Returns None if no GT IOT data.
        """
        values = [
            s["metadata"]["avg_interest"]
            for s in signals
            if s["source"] == "google_trends"
            and s["metadata"].get("query_type") == "interest_over_time"
            and "avg_interest" in s["metadata"]
        ]
        return round(sum(values) / len(values), 1) if values else None

    # -- Step 4: competition density --

    def compute_competition_density(self, signals: list[dict]) -> float:
        """
        Competition density from Amazon rank (0 = wide open, 1 = saturated).
        Defaults to 0.5 when no Amazon data.
        """
        amazon = [s for s in signals if s["source"] == "amazon_movers"]
        if not amazon:
            return 0.5

        ranks    = [s["metadata"].get("rank", 15) for s in amazon]
        avg_rank = sum(ranks) / len(ranks)
        density  = 1.0 - ((avg_rank - 1) / 19)
        return max(0.05, min(0.95, round(density, 2)))

    # -- Step 5: assemble trend objects --

    def normalize(self, signals: list[dict]) -> list[dict]:
        """
        Main Stage 2 method.
        Input:  raw signal list from collectors.collect_all()
        Output: sorted list of normalized trend objects for scoring.py
        """
        mentions = self.extract_mentions(signals)
        trends   = []

        for item in self.catalog:
            matched = mentions[item["name"]]
            if not matched:
                continue

            sources      = list({s["source"] for s in matched})
            source_count = len(sources)
            evidence     = [
                {"source": s["source"], "snippet": s["snippet"], "value": s["signal_value"]}
                for s in sorted(matched, key=lambda x: x["signal_value"], reverse=True)[:5]
            ]

            trends.append({
                # Identity
                "name":                   item["name"],
                "category":               item["category"],
                "format":                 item["format"],
                "key_ingredients":        item["key_ingredients"],
                "ingredients":            item["ingredients"],
                "primary_source_country": item["primary_source_country"],
                # Computed signals
                "growth_rate_pct":        self.compute_growth_rate(matched),
                "recency_score":          self.compute_recency_score(matched),
                "competition_density":    self.compute_competition_density(matched),
                "avg_gt_interest":        self.compute_avg_interest(matched),
                "rising_query_count":     self.count_rising_queries(matched),
                # Evidence
                "evidence":               evidence,
                "sources":                sources,
                "source_count":           source_count,
                "signal_count":           len(matched),
            })

        trends.sort(key=lambda t: (t["source_count"], t["growth_rate_pct"]), reverse=True)
        return trends


# ---------------------------------------------------------------------------
# Module-level convenience functions — preserve public API for tests + scripts
# ---------------------------------------------------------------------------

_normalizer = TrendNormalizer()

def extract_mentions(signals):           return _normalizer.extract_mentions(signals)
def compute_growth_rate(signals):        return _normalizer.compute_growth_rate(signals)
def compute_recency_score(signals):      return _normalizer.compute_recency_score(signals)
def count_rising_queries(signals):       return _normalizer.count_rising_queries(signals)
def compute_avg_interest(signals):       return _normalizer.compute_avg_interest(signals)
def compute_competition_density(signals): return _normalizer.compute_competition_density(signals)
def normalize(signals):                  return _normalizer.normalize(signals)


# ---------------------------------------------------------------------------
# Quick test — python core_discovery.py
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    from pop_trend_intelligence.pipeline.collectors import collect_all

    print("Running Stage 1 collectors...")
    signals = collect_all()

    print(f"\nRunning Stage 2 normalization on {len(signals)} signals...\n")
    trends = TrendNormalizer().normalize(signals)

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
        src_str  = ",".join(SOURCE_ABBREV.get(s, s) for s in sorted(t["sources"]))
        interest = f"{t['avg_gt_interest']:.0f}" if t["avg_gt_interest"] is not None else "—"
        print(
            f"{t['name']:<28} {src_str:>8} "
            f"{t['growth_rate_pct']:>6}% "
            f"{t['recency_score']:>8.2f} "
            f"{t['competition_density']:>8.2f} "
            f"{interest:>7} "
            f"{t['rising_query_count']:>7}"
        )
