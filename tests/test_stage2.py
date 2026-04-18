"""
Tests for Stage 2 — core_discovery.py

Run:  venv/bin/pytest tests/test_stage2.py -v
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from core_discovery import (
    extract_mentions,
    compute_growth_rate,
    compute_recency_score,
    count_rising_queries,
    compute_avg_interest,
    compute_competition_density,
    normalize,
    INGREDIENT_CATALOG,
)


# ---------------------------------------------------------------------------
# Helpers — build minimal signal dicts for tests
# ---------------------------------------------------------------------------

def gt_iot(term, growth_pct, avg_interest=30.0):
    """Google Trends interest_over_time signal."""
    return {
        "source": "google_trends",
        "term": term,
        "signal_value": growth_pct,
        "snippet": f"Google Trends: '{term}' avg interest={avg_interest}/100, growth {growth_pct:+d}%",
        "timestamp": "2026-04-18T00:00:00",
        "metadata": {
            "query_type": "interest_over_time",
            "avg_interest": avg_interest,
            "timeframe": "today 3-m",
        },
    }


def gt_rising(query, value, parent):
    """Google Trends rising related query signal."""
    return {
        "source": "google_trends",
        "term": query,
        "signal_value": value,
        "snippet": f"Google Trends rising query: '{query}' +{value}% (related to '{parent}')",
        "timestamp": "2026-04-18T00:00:00",
        "metadata": {
            "query_type": "rising_related",
            "parent_term": parent,
        },
    }


def amazon_signal(name, rank, rank_before=None):
    """Amazon Movers & Shakers signal."""
    if rank_before is not None:
        signal_val = rank_before - rank
        rank_change = f"Sales rank: {rank} (was {rank_before})"
    else:
        signal_val = 999
        rank_change = f"Sales rank: {rank} (previously unranked)"
    return {
        "source": "amazon_movers",
        "term": name,
        "signal_value": signal_val,
        "snippet": f"Amazon Grocery #{rank}: '{name}' — {rank_change}",
        "timestamp": "2026-04-18T00:00:00",
        "metadata": {
            "rank": rank,
            "category": "Grocery & Gourmet Food",
            "rank_change": rank_change,
        },
    }


def rss_signal(title, feed="New Hope Network"):
    return {
        "source": "rss",
        "term": title,
        "signal_value": 1,
        "snippet": f"{feed}: '{title[:80]}'",
        "timestamp": "2026-04-18T00:00:00",
        "metadata": {"feed": feed, "url": "", "title": title, "summary": ""},
    }


def fda_signal(substance):
    return {
        "source": "fda_gras",
        "term": substance,
        "signal_value": 1,
        "snippet": f"FDA GRAS Notice: '{substance}' cleared",
        "timestamp": "2026-04-18T00:00:00",
        "metadata": {"fda_status": "GRAS_cleared"},
    }


# ===========================================================================
# extract_mentions
# ===========================================================================

class TestExtractMentions:
    def test_exact_alias_match(self):
        signals = [gt_iot("mushroom coffee", 8, 61)]
        mentions = extract_mentions(signals)
        assert len(mentions["Mushroom Coffee"]) == 1

    def test_alias_match_in_snippet(self):
        # "cordyceps" appears in snippet, not term
        signal = rss_signal("New study on cordyceps and athletic performance")
        mentions = extract_mentions([signal])
        assert len(mentions["Mushroom Coffee"]) == 1

    def test_case_insensitive(self):
        signal = rss_signal("LION'S MANE supplement review")
        mentions = extract_mentions([signal])
        assert len(mentions["Lion's Mane Mushroom"]) == 1

    def test_no_double_count_per_signal(self):
        # Signal mentions both "lions mane" AND "lion's mane mushroom" — should count once
        signal = rss_signal("lion's mane mushroom and lions mane coffee compared")
        mentions = extract_mentions([signal])
        assert len(mentions["Lion's Mane Mushroom"]) == 1

    def test_one_signal_matches_two_different_trends(self):
        # An article about turmeric ginger AND mushroom coffee should match both
        signal = rss_signal("turmeric ginger meets mushroom coffee in new launch")
        mentions = extract_mentions([signal])
        assert len(mentions["Turmeric Ginger Latte"]) == 1
        assert len(mentions["Mushroom Coffee"]) == 1

    def test_no_match_returns_empty(self):
        signal = rss_signal("General food industry news with no ingredient names")
        mentions = extract_mentions([signal])
        for name in [item["name"] for item in INGREDIENT_CATALOG]:
            assert len(mentions[name]) == 0

    def test_all_catalog_names_present_as_keys(self):
        mentions = extract_mentions([])
        for item in INGREDIENT_CATALOG:
            assert item["name"] in mentions


# ===========================================================================
# compute_growth_rate
# ===========================================================================

class TestComputeGrowthRate:
    def test_uses_interest_over_time_not_rising(self):
        signals = [
            gt_iot("mushroom coffee", 8),
            gt_rising("mushroom coffee benefits", 3250, "mushroom coffee"),
        ]
        # Should return 8 (IOT), not 3250 (rising)
        assert compute_growth_rate(signals) == 8

    def test_returns_max_iot_across_batches(self):
        signals = [
            gt_iot("ginger shot", -6),
            gt_iot("organic ginger shot", 15),  # same trend, different batch
        ]
        assert compute_growth_rate(signals) == 15

    def test_falls_back_to_amazon_when_no_gt(self):
        signals = [amazon_signal("PBfit Peanut Butter Powder", rank=1, rank_before=None)]
        # 999 * 2 = 1998, capped at 200
        assert compute_growth_rate(signals) == 200

    def test_amazon_rank_jump_converted_correctly(self):
        signals = [amazon_signal("Some product", rank=5, rank_before=55)]
        # rank_before - rank = 50, signal_value = 50, growth = 50 * 2 = 100
        assert compute_growth_rate(signals) == 100

    def test_no_signals_returns_zero(self):
        assert compute_growth_rate([]) == 0

    def test_all_declining_returns_zero(self):
        # All negative IOT — should return 0 (max of negative filtered to >0... wait)
        # Actually: we filter gt to signal_value > 0 for amazon only.
        # For GT, we take max(iot) regardless of sign.
        signals = [gt_iot("ube latte", -20)]
        assert compute_growth_rate(signals) == -20  # negative growth is valid data

    def test_rss_and_fda_signals_ignored(self):
        signals = [
            rss_signal("elderberry gummy trend"),
            fda_signal("elderberry extract"),
        ]
        assert compute_growth_rate(signals) == 0


# ===========================================================================
# compute_recency_score
# ===========================================================================

class TestComputeRecencyScore:
    def test_hot_trend_scores_near_one(self):
        signals = [gt_iot("tempeh chips", 200)]
        score = compute_recency_score(signals)
        assert score == 1.0

    def test_flat_trend_scores_one_third(self):
        signals = [gt_iot("reishi tea", 0)]
        score = compute_recency_score(signals)
        assert abs(score - 0.33) < 0.01

    def test_declining_trend_scores_low(self):
        signals = [gt_iot("ube latte", -100)]
        score = compute_recency_score(signals)
        assert score == 0.0

    def test_score_clamped_to_zero_to_one(self):
        signals = [gt_iot("test", -999)]
        assert compute_recency_score(signals) == 0.0
        signals = [gt_iot("test", 9999)]
        assert compute_recency_score(signals) == 1.0

    def test_rising_related_queries_excluded(self):
        # Only rising_related signal — should return neutral 0.5
        signals = [gt_rising("elderberry gummies", 5000, "elderberry syrup")]
        assert compute_recency_score(signals) == 0.5

    def test_mixed_iot_and_rising_uses_only_iot(self):
        signals = [
            gt_iot("elderberry syrup", 0),           # flat
            gt_rising("elderberry gummies", 5000, "elderberry syrup"),  # breakout
        ]
        score = compute_recency_score(signals)
        # Should use only IOT (0%), NOT be inflated by 5000
        assert abs(score - 0.33) < 0.01

    def test_no_gt_data_returns_neutral(self):
        signals = [rss_signal("matcha mushroom product launch"), amazon_signal("Matcha powder", 5)]
        assert compute_recency_score(signals) == 0.5


# ===========================================================================
# count_rising_queries
# ===========================================================================

class TestCountRisingQueries:
    def test_counts_rising_related_only(self):
        signals = [
            gt_iot("ginger shot", -6),
            gt_rising("organic ginger shot", 130, "ginger shot"),
            gt_rising("vive ginger shot", 60, "ginger shot"),
            gt_rising("lemon ginger shot benefits", 50, "ginger shot"),
            rss_signal("Ginger shot benefits article"),
        ]
        assert count_rising_queries(signals) == 3

    def test_zero_when_no_rising(self):
        signals = [gt_iot("pandan snack", 12), rss_signal("Pandan snack review")]
        assert count_rising_queries(signals) == 0

    def test_empty_signals_returns_zero(self):
        assert count_rising_queries([]) == 0


# ===========================================================================
# compute_avg_interest
# ===========================================================================

class TestComputeAvgInterest:
    def test_averages_iot_avg_interest(self):
        signals = [
            gt_iot("mushroom coffee", 8, avg_interest=61.0),
            gt_iot("mushroom coffee blend", 5, avg_interest=39.0),
        ]
        result = compute_avg_interest(signals)
        assert result == 50.0

    def test_ignores_rising_related(self):
        signals = [
            gt_iot("lion's mane", -5, avg_interest=54.0),
            gt_rising("lions mane supplement", 400, "lion's mane"),  # no avg_interest
        ]
        assert compute_avg_interest(signals) == 54.0

    def test_returns_none_when_no_gt_iot(self):
        signals = [rss_signal("matcha latte trend"), amazon_signal("Matcha powder", 3)]
        assert compute_avg_interest(signals) is None

    def test_empty_returns_none(self):
        assert compute_avg_interest([]) is None


# ===========================================================================
# compute_competition_density
# ===========================================================================

class TestComputeCompetitionDensity:
    def test_rank_one_is_most_crowded(self):
        signals = [amazon_signal("Top product", rank=1)]
        density = compute_competition_density(signals)
        assert density == 0.95  # clamped max

    def test_rank_twenty_is_least_crowded(self):
        signals = [amazon_signal("Niche product", rank=20)]
        density = compute_competition_density(signals)
        assert density == 0.05  # clamped min

    def test_rank_ten_is_midpoint(self):
        signals = [amazon_signal("Mid product", rank=10)]
        density = compute_competition_density(signals)
        # 1.0 - (10-1)/19 = 1.0 - 0.473 = 0.527
        assert abs(density - 0.53) < 0.01

    def test_no_amazon_returns_neutral(self):
        signals = [gt_iot("moringa powder", 5), rss_signal("Moringa trend")]
        assert compute_competition_density(signals) == 0.5

    def test_multiple_amazon_signals_averaged(self):
        signals = [
            amazon_signal("Product A", rank=1),
            amazon_signal("Product B", rank=19),
        ]
        density = compute_competition_density(signals)
        # avg_rank = 10, density = 1.0 - 9/19 = 0.526
        assert 0.50 < density < 0.56


# ===========================================================================
# normalize — integration test
# ===========================================================================

class TestNormalize:
    def _make_signals(self):
        return [
            gt_iot("mushroom coffee", 8, avg_interest=61.0),
            gt_rising("mushroom coffee benefits", 3250, "mushroom coffee"),
            gt_iot("lion's mane", -5, avg_interest=54.0),
            gt_rising("lions mane supplement", 400, "lion's mane"),
            gt_rising("lions mane mushroom benefits", 200, "lion's mane"),
            rss_signal("matcha mushroom latte launches at Expo West"),
            amazon_signal("PBfit Peanut Butter Powder", rank=1),
            fda_signal("chia seeds extract"),
        ]

    def test_returns_list_of_dicts(self):
        trends = normalize(self._make_signals())
        assert isinstance(trends, list)
        assert all(isinstance(t, dict) for t in trends)

    def test_all_required_fields_present(self):
        trends = normalize(self._make_signals())
        required = [
            "name", "category", "format", "key_ingredients", "ingredients",
            "primary_source_country", "growth_rate_pct", "recency_score",
            "competition_density", "avg_gt_interest", "rising_query_count",
            "evidence", "sources", "source_count", "signal_count",
        ]
        for trend in trends:
            for field in required:
                assert field in trend, f"Missing field '{field}' in trend '{trend.get('name')}'"

    def test_trends_with_no_signals_excluded(self):
        trends = normalize(self._make_signals())
        names = [t["name"] for t in trends]
        # Elderberry has no signals in our test set — should not appear
        assert "Elderberry" not in names

    def test_mushroom_coffee_growth_not_inflated(self):
        trends = normalize(self._make_signals())
        mc = next(t for t in trends if t["name"] == "Mushroom Coffee")
        assert mc["growth_rate_pct"] == 8   # IOT only, not 3250

    def test_mushroom_coffee_rising_query_count(self):
        trends = normalize(self._make_signals())
        mc = next(t for t in trends if t["name"] == "Mushroom Coffee")
        assert mc["rising_query_count"] == 1

    def test_lions_mane_two_rising_queries(self):
        trends = normalize(self._make_signals())
        lm = next(t for t in trends if t["name"] == "Lion's Mane Mushroom")
        assert lm["rising_query_count"] == 2

    def test_recency_not_inflated_by_rising(self):
        trends = normalize(self._make_signals())
        mc = next(t for t in trends if t["name"] == "Mushroom Coffee")
        # IOT growth = 8%, recency = (8+100)/300 = 0.36
        assert abs(mc["recency_score"] - 0.36) < 0.01

    def test_peanut_butter_powder_amazon_density(self):
        trends = normalize(self._make_signals())
        pb = next((t for t in trends if t["name"] == "Peanut Butter Powder"), None)
        assert pb is not None
        assert pb["competition_density"] == 0.95  # rank 1 = most crowded

    def test_sorted_by_source_count_then_growth(self):
        trends = normalize(self._make_signals())
        # Verify sort: source_count desc, then growth_rate_pct desc
        for i in range(len(trends) - 1):
            a, b = trends[i], trends[i + 1]
            if a["source_count"] == b["source_count"]:
                assert a["growth_rate_pct"] >= b["growth_rate_pct"]
            else:
                assert a["source_count"] >= b["source_count"]

    def test_evidence_capped_at_five(self):
        # Add many signals for one trend
        signals = [gt_iot("mushroom coffee", i, 61.0) for i in range(10)]
        trends = normalize(signals)
        mc = next(t for t in trends if t["name"] == "Mushroom Coffee")
        assert len(mc["evidence"]) <= 5

    def test_source_count_reflects_distinct_sources(self):
        signals = [
            gt_iot("mushroom coffee", 8, 61.0),
            rss_signal("mushroom coffee article 1"),
            rss_signal("mushroom coffee article 2"),  # same source as above
            amazon_signal("Four Sigmatic Mushroom Coffee", rank=5),
        ]
        trends = normalize(signals)
        mc = next(t for t in trends if t["name"] == "Mushroom Coffee")
        # GT + RSS + AMZ = 3 distinct sources, even though RSS has 2 signals
        assert mc["source_count"] == 3

    def test_empty_signals_returns_empty_list(self):
        assert normalize([]) == []
