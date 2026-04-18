"""
Tests for Stage 3 — scoring.py + pop_data.py

Run:  venv/bin/pytest tests/test_stage3.py -v
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import tempfile
import pandas as pd

from scoring import (
    check_shelf_life,
    check_fda_ingredients,
    check_trade_risk,
    compute_signal_strength,
    compute_pop_fit,
    compute_market_stage,
    classify_action,
    score,
    export_to_csv,
)
from pop_data import (
    SHELF_LIFE_MIN_MONTHS,
    COUNTRY_RISK_THRESHOLD,
    POP_LINES,
    SIGNAL_STRENGTH_FACTORS,
)


# ---------------------------------------------------------------------------
# Helpers — minimal trend dicts for tests
# ---------------------------------------------------------------------------

def make_trend(
    name="Test Trend",
    category="functional beverage",
    fmt="instant powder",
    key_ingredients=None,
    ingredients=None,
    country="USA",
    growth=10,
    recency=0.5,
    competition=0.5,
    source_count=2,
    sources=None,
    signal_count=4,
    avg_gt_interest=30.0,
    rising_query_count=0,
):
    return {
        "name":                   name,
        "category":               category,
        "format":                 fmt,
        "key_ingredients":        key_ingredients or ["ginger", "wellness shot"],
        "ingredients":            ingredients or ["ginger", "lemon"],
        "primary_source_country": country,
        "growth_rate_pct":        growth,
        "recency_score":          recency,
        "competition_density":    competition,
        "source_count":           source_count,
        "sources":                sources or ["google_trends", "rss"],
        "signal_count":           signal_count,
        "avg_gt_interest":        avg_gt_interest,
        "rising_query_count":     rising_query_count,
        "evidence":               [],
    }


# ===========================================================================
# check_shelf_life
# ===========================================================================

class TestCheckShelfLife:
    def test_instant_powder_passes(self):
        ok, months, note = check_shelf_life(make_trend(fmt="instant powder"))
        assert ok is True
        assert months == 36

    def test_dry_tea_passes(self):
        ok, months, _ = check_shelf_life(make_trend(fmt="dry tea"))
        assert ok is True
        assert months == 36

    def test_chips_crackers_blocked(self):
        ok, months, note = check_shelf_life(make_trend(fmt="chips/crackers"))
        assert ok is False
        assert months == 9
        assert "❌" in note

    def test_kombucha_blocked(self):
        ok, months, _ = check_shelf_life(make_trend(fmt="kombucha"))
        assert ok is False
        assert months == 2

    def test_snack_bar_borderline_passes(self):
        ok, months, _ = check_shelf_life(make_trend(fmt="snack bar"))
        assert ok is True
        assert months == SHELF_LIFE_MIN_MONTHS

    def test_unknown_format_defaults_to_twelve_months(self):
        ok, months, note = check_shelf_life(make_trend(fmt="freeze dried mystery"))
        assert ok is True
        assert months == 12
        assert "review required" in note.lower()

    def test_chewy_candy_passes(self):
        ok, months, _ = check_shelf_life(make_trend(fmt="chewy candy"))
        assert ok is True
        assert months == 24

    def test_shelf_stable_beverage_passes(self):
        ok, months, _ = check_shelf_life(make_trend(fmt="shelf-stable beverage"))
        assert ok is True
        assert months == 18


# ===========================================================================
# check_fda_ingredients
# ===========================================================================

class TestCheckFdaIngredients:
    def test_clean_ingredients_not_blocked(self):
        t = make_trend(ingredients=["ginger", "turmeric", "honey"])
        blocked, watch, note = check_fda_ingredients(t)
        assert blocked is False
        assert watch == []
        assert "✅" in note

    def test_cbd_blocks(self):
        t = make_trend(ingredients=["cbd oil", "hemp extract"])
        blocked, watch, note = check_fda_ingredients(t)
        assert blocked is True
        assert "❌" in note

    def test_ephedra_blocks(self):
        t = make_trend(ingredients=["ephedra sinica", "caffeine"])
        blocked, watch, note = check_fda_ingredients(t)
        assert blocked is True

    def test_kratom_is_watch_not_blocked(self):
        t = make_trend(ingredients=["kratom leaf", "ginger"])
        blocked, watch, note = check_fda_ingredients(t)
        assert blocked is False
        assert "kratom" in watch
        assert "⚠️" in note

    def test_kava_is_watch_not_blocked(self):
        t = make_trend(ingredients=["kava extract"])
        blocked, watch, note = check_fda_ingredients(t)
        assert blocked is False
        assert "kava" in watch

    def test_nmn_is_watch_not_blocked(self):
        t = make_trend(ingredients=["nmn", "resveratrol"])
        blocked, watch, note = check_fda_ingredients(t)
        assert blocked is False
        assert "nmn" in watch

    def test_delta8_blocks(self):
        t = make_trend(ingredients=["delta-8 thc distillate"])
        blocked, watch, _ = check_fda_ingredients(t)
        assert blocked is True

    def test_red_yeast_rice_blocks(self):
        t = make_trend(ingredients=["red yeast rice extract"])
        blocked, watch, _ = check_fda_ingredients(t)
        assert blocked is True

    def test_partial_ingredient_name_matches(self):
        t = make_trend(ingredients=["ephedrine hydrochloride"])
        blocked, _, _ = check_fda_ingredients(t)
        assert blocked is True

    def test_empty_ingredients_is_clean(self):
        t = make_trend(ingredients=[])
        blocked, watch, _ = check_fda_ingredients(t)
        assert blocked is False
        assert watch == []


# ===========================================================================
# check_trade_risk
# ===========================================================================

class TestCheckTradeRisk:
    def test_usa_passes(self):
        ok, risk, _ = check_trade_risk(make_trend(country="USA"))
        assert ok is True
        assert risk == 0.00

    def test_japan_passes(self):
        ok, risk, _ = check_trade_risk(make_trend(country="Japan"))
        assert ok is True
        assert risk == 0.15

    def test_indonesia_passes(self):
        ok, risk, _ = check_trade_risk(make_trend(country="Indonesia"))
        assert ok is True
        assert risk == 0.30

    def test_china_blocked_by_default(self):
        ok, risk, note = check_trade_risk(make_trend(country="China", category="functional beverage"))
        assert ok is False
        assert risk == 0.85
        assert "❌" in note

    def test_china_exempt_for_organic_teas(self):
        ok, risk, note = check_trade_risk(make_trend(country="China", category="organic_teas"))
        assert ok is True
        assert "exempt" in note.lower()

    def test_russia_blocked(self):
        ok, risk, _ = check_trade_risk(make_trend(country="Russia"))
        assert ok is False
        assert risk == 1.00

    def test_unknown_country_defaults_to_moderate(self):
        ok, risk, _ = check_trade_risk(make_trend(country="Atlantis"))
        assert ok is True
        assert risk == 0.30

    def test_vietnam_passes_under_threshold(self):
        ok, risk, _ = check_trade_risk(make_trend(country="Vietnam"))
        assert ok is True
        assert risk == 0.45

    def test_threshold_boundary(self):
        ok, risk, _ = check_trade_risk(make_trend(country="Vietnam"))
        assert risk <= COUNTRY_RISK_THRESHOLD


# ===========================================================================
# compute_signal_strength
# ===========================================================================

class TestComputeSignalStrength:
    def test_perfect_trend_scores_hundred(self):
        t = make_trend(
            growth=200, recency=1.0, competition=0.0, source_count=5,
            avg_gt_interest=100.0, rising_query_count=4,
        )
        assert compute_signal_strength(t) == 100.0

    def test_zero_everything_scores_zero(self):
        t = make_trend(
            growth=0, recency=0.0, competition=1.0, source_count=0,
            avg_gt_interest=0.0, rising_query_count=0,
        )
        assert compute_signal_strength(t) == 0.0

    def test_growth_capped_at_200(self):
        high   = compute_signal_strength(make_trend(growth=500))
        capped = compute_signal_strength(make_trend(growth=200))
        assert high == capped

    def test_negative_growth_treated_as_zero(self):
        negative = compute_signal_strength(make_trend(growth=-50))
        zero     = compute_signal_strength(make_trend(growth=0))
        assert negative == zero

    def test_score_always_0_to_100(self):
        for growth in [-100, 0, 50, 200, 999]:
            for recency in [0.0, 0.5, 1.0]:
                t = make_trend(growth=growth, recency=recency)
                s = compute_signal_strength(t)
                assert 0.0 <= s <= 100.0

    def test_avg_gt_interest_none_defaults_to_neutral(self):
        with_none    = compute_signal_strength(make_trend(avg_gt_interest=None))
        with_fifty   = compute_signal_strength(make_trend(avg_gt_interest=50.0))
        assert with_none == with_fifty

    def test_avg_gt_interest_boosts_score(self):
        low  = compute_signal_strength(make_trend(avg_gt_interest=10.0))
        high = compute_signal_strength(make_trend(avg_gt_interest=90.0))
        assert high > low

    def test_rising_query_count_boosts_score(self):
        no_rising   = compute_signal_strength(make_trend(rising_query_count=0))
        with_rising = compute_signal_strength(make_trend(rising_query_count=4))
        assert with_rising > no_rising

    def test_rising_query_count_capped(self):
        four = compute_signal_strength(make_trend(rising_query_count=4))
        ten  = compute_signal_strength(make_trend(rising_query_count=10))
        assert four == ten

    def test_all_factors_contribute(self):
        # Verify all 6 factors are present in pop_data
        expected = {
            "growth_rate", "recency", "corroboration",
            "competition", "market_size", "rising_boost",
        }
        assert set(SIGNAL_STRENGTH_FACTORS.keys()) == expected

    def test_factors_sum_to_one(self):
        total = sum(SIGNAL_STRENGTH_FACTORS.values())
        assert abs(total - 1.0) < 1e-9


# ===========================================================================
# compute_pop_fit
# ===========================================================================

class TestComputePopFit:
    def test_returns_tuple_of_score_and_lines(self):
        result = compute_pop_fit(make_trend(key_ingredients=["ginger"]))
        assert isinstance(result, tuple)
        assert len(result) == 2

    def test_ginger_matches_two_lines(self):
        score, lines = compute_pop_fit(make_trend(key_ingredients=["ginger", "wellness shot"]))
        assert score == 60
        assert len(lines) == 2

    def test_tea_matches_two_lines(self):
        score, lines = compute_pop_fit(make_trend(key_ingredients=["tea", "herbal"]))
        assert score == 60
        assert len(lines) == 2

    def test_ginseng_matches_one_line(self):
        score, lines = compute_pop_fit(make_trend(key_ingredients=["american ginseng", "adaptogen"]))
        assert score == 30
        assert len(lines) == 1

    def test_no_match_returns_zero_and_empty(self):
        score, lines = compute_pop_fit(make_trend(key_ingredients=["collagen", "beauty"]))
        assert score == 0
        assert lines == []

    def test_score_capped_at_100(self):
        score, lines = compute_pop_fit(make_trend(
            key_ingredients=["ginger", "honey", "ginseng", "tea", "matcha", "adaptogen"]
        ))
        assert score == 100

    def test_no_double_count_within_line(self):
        score, lines = compute_pop_fit(make_trend(key_ingredients=["ginger", "chew", "candy"]))
        # ginger_chews matched once (+30), ginger_honey_crystals matched (+30)
        assert score == 60

    def test_matched_line_names_are_display_names(self):
        _, lines = compute_pop_fit(make_trend(key_ingredients=["ginger"]))
        for line_key, line_data in POP_LINES.items():
            if line_data["display_name"] in lines:
                break
        else:
            assert False, "No display name found in matched lines"

    def test_mushroom_matches_herbal_teas_line(self):
        score, lines = compute_pop_fit(make_trend(key_ingredients=["mushroom", "adaptogen", "nootropic"]))
        assert any("Herbal" in l or "Ginseng" in l for l in lines)
        assert score >= 30


# ===========================================================================
# compute_market_stage
# ===========================================================================

class TestComputeMarketStage:
    def test_high_growth_high_recency_is_emerging(self):
        t = make_trend(growth=50, recency=0.6)
        assert compute_market_stage(t) == "emerging"

    def test_positive_growth_good_recency_is_growing(self):
        t = make_trend(growth=5, recency=0.38)
        assert compute_market_stage(t) == "growing"

    def test_slight_decline_is_peaking(self):
        t = make_trend(growth=-5, recency=0.32)
        assert compute_market_stage(t) == "peaking"

    def test_strong_decline_is_declining(self):
        t = make_trend(growth=-30, recency=0.20)
        assert compute_market_stage(t) == "declining"

    def test_flat_growth_low_recency_is_declining(self):
        t = make_trend(growth=0, recency=0.20)
        assert compute_market_stage(t) == "declining"

    def test_all_stages_are_strings(self):
        stages = {"emerging", "growing", "peaking", "declining"}
        for growth in [50, 5, -5, -30]:
            for recency in [0.2, 0.35, 0.5, 0.7]:
                t = make_trend(growth=growth, recency=recency)
                assert compute_market_stage(t) in stages


# ===========================================================================
# classify_action
# ===========================================================================

class TestClassifyAction:
    def test_blocked_trend_always_pass(self):
        t = make_trend(growth=200, recency=0.9, competition=0.1, source_count=5)
        assert classify_action(t, pop_fit_score=100, compliance_ok=False) == "PASS"

    def test_both_when_high_fit_and_distributable(self):
        t = make_trend(category="functional beverage", growth=50, recency=0.6, competition=0.4)
        assert classify_action(t, pop_fit_score=60, compliance_ok=True) == "BOTH"

    def test_develop_when_high_fit_but_uncategorized(self):
        t = make_trend(category="asian specialty", growth=50, recency=0.6, competition=0.9)
        assert classify_action(t, pop_fit_score=60, compliance_ok=True) == "DEVELOP"

    def test_distribute_when_low_fit_but_growing(self):
        t = make_trend(category="functional beverage", growth=20, recency=0.5, competition=0.4)
        assert classify_action(t, pop_fit_score=0, compliance_ok=True) == "DISTRIBUTE"

    def test_pass_when_declining_and_low_fit(self):
        t = make_trend(category="functional beverage", growth=-30, recency=0.2, competition=0.5)
        assert classify_action(t, pop_fit_score=0, compliance_ok=True) == "PASS"

    def test_pass_when_fit_below_50(self):
        t = make_trend(growth=-10, recency=0.2, competition=0.5)
        assert classify_action(t, pop_fit_score=30, compliance_ok=True) == "PASS"

    def test_low_competition_qualifies_for_distribute(self):
        t = make_trend(category="plant-based snack", growth=20, recency=0.5, competition=0.3)
        assert classify_action(t, pop_fit_score=0, compliance_ok=True) == "DISTRIBUTE"

    def test_recency_below_threshold_blocks_develop(self):
        t = make_trend(category="asian specialty", growth=0, recency=0.25, competition=0.4)
        # recency < 0.30 → can't DEVELOP even with high fit
        assert classify_action(t, pop_fit_score=60, compliance_ok=True) != "DEVELOP"


# ===========================================================================
# score — integration tests
# ===========================================================================

class TestScore:
    def _catalog(self):
        return [
            make_trend("Ginger Shot",        fmt="ready-to-drink bottle",
                       key_ingredients=["ginger", "wellness shot"], country="USA",
                       growth=10, recency=0.4, source_count=2,
                       avg_gt_interest=26.0, rising_query_count=4),
            make_trend("Tempeh",             fmt="chips/crackers",
                       key_ingredients=["tempeh", "fermented soy"], country="Indonesia",
                       growth=28, recency=0.43, source_count=1,
                       avg_gt_interest=11.0, rising_query_count=0),
            make_trend("Reishi Mushroom Tea", category="functional tea", fmt="dry tea",
                       key_ingredients=["reishi", "mushroom", "functional tea"], country="China",
                       growth=0, recency=0.33, source_count=1,
                       avg_gt_interest=22.0, rising_query_count=1),
            make_trend("CBD Energy Shot",    fmt="ready-to-drink bottle",
                       key_ingredients=["cbd", "caffeine"],
                       ingredients=["cbd oil", "caffeine"], country="USA",
                       growth=50, recency=0.6, source_count=3,
                       avg_gt_interest=40.0, rising_query_count=2),
        ]

    def test_returns_list_of_dicts(self):
        assert all(isinstance(t, dict) for t in score(self._catalog()))

    def test_all_scoring_fields_present(self):
        required = [
            "shelf_life_ok", "fda_blocked", "fda_watch", "trade_risk_score",
            "trade_risk_ok", "compliance_ok", "compliance_note",
            "signal_strength", "pop_fit_score", "pop_line_matches",
            "market_stage", "composite_score", "action",
        ]
        for t in score(self._catalog()):
            for field in required:
                assert field in t, f"Missing '{field}' in '{t.get('name')}'"

    def test_sorted_by_composite_descending(self):
        results = score(self._catalog())
        scores = [t["composite_score"] for t in results]
        assert scores == sorted(scores, reverse=True)

    def test_tempeh_fails_shelf_life(self):
        tempeh = next(t for t in score(self._catalog()) if t["name"] == "Tempeh")
        assert tempeh["shelf_life_ok"] is False
        assert tempeh["compliance_ok"] is False
        assert tempeh["composite_score"] == 0.0
        assert tempeh["action"] == "PASS"

    def test_reishi_fails_china_trade_risk(self):
        reishi = next(t for t in score(self._catalog()) if t["name"] == "Reishi Mushroom Tea")
        assert reishi["trade_risk_ok"] is False
        assert reishi["compliance_ok"] is False
        assert reishi["composite_score"] == 0.0

    def test_cbd_product_is_fda_blocked(self):
        cbd = next(t for t in score(self._catalog()) if t["name"] == "CBD Energy Shot")
        assert cbd["fda_blocked"] is True
        assert cbd["composite_score"] == 0.0
        assert cbd["action"] == "PASS"

    def test_compliant_trend_has_nonzero_composite(self):
        ginger = next(t for t in score(self._catalog()) if t["name"] == "Ginger Shot")
        assert ginger["compliance_ok"] is True
        assert ginger["composite_score"] > 0.0

    def test_composite_formula(self):
        results = score(self._catalog())
        for t in results:
            if t["compliance_ok"]:
                expected = round(0.55 * t["signal_strength"] + 0.45 * t["pop_fit_score"], 1)
                assert t["composite_score"] == expected
            else:
                assert t["composite_score"] == 0.0

    def test_blocked_sorted_to_bottom(self):
        results = score(self._catalog())
        nonzero = [t for t in results if t["composite_score"] > 0]
        zeroed  = [t for t in results if t["composite_score"] == 0]
        assert results[:len(nonzero)] == nonzero

    def test_empty_input_returns_empty(self):
        assert score([]) == []

    def test_fda_watch_not_blocked(self):
        t = make_trend("Kava Tea", fmt="dry tea", country="USA",
                       ingredients=["kava extract", "green tea"],
                       key_ingredients=["kava", "tea"])
        result = score([t])[0]
        assert result["fda_blocked"] is False
        assert "kava" in result["fda_watch"]
        assert result["compliance_ok"] is True
        assert result["composite_score"] > 0

    def test_pop_line_matches_is_list(self):
        results = score(self._catalog())
        for t in results:
            assert isinstance(t["pop_line_matches"], list)

    def test_pop_line_matches_populated_for_ginger(self):
        ginger = next(t for t in score(self._catalog()) if t["name"] == "Ginger Shot")
        assert len(ginger["pop_line_matches"]) >= 1

    def test_market_stage_present_and_valid(self):
        valid_stages = {"emerging", "growing", "peaking", "declining"}
        for t in score(self._catalog()):
            assert t["market_stage"] in valid_stages

    def test_rising_queries_affect_signal_strength(self):
        low  = make_trend("Low",  growth=10, recency=0.5, rising_query_count=0)
        high = make_trend("High", growth=10, recency=0.5, rising_query_count=4)
        r_low, r_high = score([low, high])
        # high rising count should have higher signal strength
        # (sorting puts higher composite first, but signal_strength should differ)
        sl = next(t["signal_strength"] for t in score([low])  if t["name"] == "Low")
        sh = next(t["signal_strength"] for t in score([high]) if t["name"] == "High")
        assert sh > sl


# ===========================================================================
# export_to_csv
# ===========================================================================

class TestExportToCsv:
    def _scored(self):
        return score([
            make_trend("Mushroom Coffee", growth=8, recency=0.36,
                       key_ingredients=["mushroom", "adaptogen", "coffee"],
                       avg_gt_interest=61.0, rising_query_count=1),
            make_trend("Tempeh", fmt="chips/crackers",
                       key_ingredients=["tempeh"], country="Indonesia",
                       growth=28, recency=0.43),
        ])

    def test_creates_csv_file(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "test_output.csv")
            export_to_csv(self._scored(), filepath=path)
            assert os.path.exists(path)

    def test_csv_row_count_matches_trends(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "test_output.csv")
            scored = self._scored()
            export_to_csv(scored, filepath=path)
            df = pd.read_csv(path)
            assert len(df) == len(scored)

    def test_csv_has_expected_columns(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "test_output.csv")
            export_to_csv(self._scored(), filepath=path)
            df = pd.read_csv(path)
            for col in ["action", "composite_score", "name", "market_stage",
                        "growth_rate_pct", "pop_fit_score", "compliance_ok"]:
                assert col in df.columns, f"Missing column: {col}"

    def test_pop_line_matches_serialized_as_string(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "test_output.csv")
            export_to_csv(self._scored(), filepath=path)
            df = pd.read_csv(path)
            assert pd.api.types.is_string_dtype(df["pop_line_matches"])  # string column

    def test_export_returns_dataframe(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "test_output.csv")
            result = export_to_csv(self._scored(), filepath=path)
            assert isinstance(result, pd.DataFrame)

    def test_empty_input_creates_empty_csv(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "empty.csv")
            export_to_csv([], filepath=path)
            df = pd.read_csv(path)
            assert len(df) == 0
