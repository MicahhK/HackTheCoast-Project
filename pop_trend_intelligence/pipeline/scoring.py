"""
Stage 3 — Scoring & Ranking (scoring.py)

Takes normalized trend objects from core_discovery.TrendNormalizer.normalize() and:
  1. Applies POP's hard constraints (shelf life, FDA ingredients, country trade risk)
  2. Computes signal strength score (0–100) from Stage 2 metrics
  3. Computes POP-Fit score (0–100) from adjacency to POP's product lines
  4. Derives market_stage label (emerging / growing / peaking / declining)
  5. Combines into composite score (zeroed if compliance fails)
  6. Classifies each trend: DISTRIBUTE / DEVELOP / BOTH / PASS
  7. Returns list sorted by composite_score descending

Export:
  export_to_csv(scored_trends, filepath)  — flattens output for Excel/Google Sheets
"""

from pop_trend_intelligence.data.pop_data import (
    SHELF_LIFE_TABLE,
    SHELF_LIFE_MIN_MONTHS,
    FDA_STATUS,
    FDA_BLOCK_STATUSES,
    COUNTRY_RISK,
    COUNTRY_RISK_THRESHOLD,
    CHINA_EXEMPT_CATEGORIES,
    POP_LINES,
    POP_FIT_POINTS_PER_LINE,
    POP_FIT_MAX,
    POP_DISTRIBUTED_CATEGORIES,
    SIGNAL_STRENGTH_WEIGHT,
    POP_FIT_WEIGHT,
    SIGNAL_STRENGTH_FACTORS,
    MAX_SOURCES,
    MAX_GROWTH_PCT,
    MAX_RISING_QUERIES,
    MARKET_STAGE_THRESHOLDS,
)
from pop_trend_intelligence.paths import DEFAULT_REPORT_FILE, EXPORTS_DIR


# ---------------------------------------------------------------------------
# TREND SCORER
# ---------------------------------------------------------------------------

class TrendScorer:
    """
    Stage 3 scoring engine. Groups all compliance checks, metric computations,
    action classification, and export into one cohesive class.
    """

    # -- Compliance checks --

    def check_shelf_life(self, trend: dict) -> tuple[bool, int, str]:
        """
        Returns (ok, months, note).
        Unknown formats default to 12 months (borderline — flagged for review).
        """
        fmt    = trend.get("format", "").lower()
        months = SHELF_LIFE_TABLE.get(fmt)

        if months is None:
            return True, 12, f"Unknown format '{fmt}' — assumed 12mo (review required)"

        ok   = months >= SHELF_LIFE_MIN_MONTHS
        note = (f"Shelf life {months}mo ✅" if ok
                else f"Shelf life {months}mo < {SHELF_LIFE_MIN_MONTHS}mo minimum ❌")
        return ok, months, note

    def check_fda_ingredients(self, trend: dict) -> tuple[bool, list, str]:
        """
        Returns (blocked, watch_list, note).
        Banned/restricted -> blocked. Watch-list -> flagged, not blocked.
        """
        ingredients = [i.lower() for i in trend.get("ingredients", [])]
        blocked_by  = []
        watch_hits  = []

        for ing in ingredients:
            for flagged, status in FDA_STATUS.items():
                if flagged in ing:
                    if status in FDA_BLOCK_STATUSES:
                        blocked_by.append(flagged)
                    else:
                        watch_hits.append(flagged)

        blocked_by = list(set(blocked_by))
        watch_hits = list(set(watch_hits))

        if blocked_by:
            note = f"FDA blocked: {', '.join(sorted(blocked_by))} ❌"
        elif watch_hits:
            note = f"FDA watch: {', '.join(sorted(watch_hits))} ⚠️"
        else:
            note = "FDA clear ✅"

        return bool(blocked_by), watch_hits, note

    def check_trade_risk(self, trend: dict) -> tuple[bool, float, str]:
        """
        Returns (ok, risk_score, note).
        China exemption applies for categories with existing POP supply chains.
        """
        country  = trend.get("primary_source_country", "").lower()
        category = trend.get("category", "").lower().replace(" ", "_").replace("&", "and")
        risk     = COUNTRY_RISK.get(country, 0.30)

        if country == "china" and category in CHINA_EXEMPT_CATEGORIES:
            return True, risk, f"China risk {risk} — exempt (existing POP supply chain) ✅"

        ok   = risk <= COUNTRY_RISK_THRESHOLD
        note = (f"Trade risk {risk:.2f} ✅" if ok
                else f"Trade risk {risk:.2f} > {COUNTRY_RISK_THRESHOLD} threshold ❌")
        return ok, risk, note

    # -- Signal strength score --

    def compute_signal_strength(self, trend: dict) -> float:
        """
        Weighted score (0–100) from six Stage 2 metrics.

        Weights (SIGNAL_STRENGTH_FACTORS):
          35% growth rate, 30% recency, 15% corroboration,
          10% competition (inverse), 5% market size, 5% rising boost
        """
        growth_normalized   = min(max(trend.get("growth_rate_pct", 0), 0), MAX_GROWTH_PCT) / MAX_GROWTH_PCT
        recency             = trend.get("recency_score", 0.5)
        corroboration       = min(trend.get("source_count", 1), MAX_SOURCES) / MAX_SOURCES
        competition_inverse = 1.0 - trend.get("competition_density", 0.5)

        avg_interest_raw = trend.get("avg_gt_interest")
        market_size      = (avg_interest_raw / 100.0) if avg_interest_raw is not None else 0.5

        rising_count = trend.get("rising_query_count", 0)
        rising_boost = min(rising_count, MAX_RISING_QUERIES) / MAX_RISING_QUERIES

        score = (
            SIGNAL_STRENGTH_FACTORS["growth_rate"]   * growth_normalized   * 100 +
            SIGNAL_STRENGTH_FACTORS["recency"]        * recency             * 100 +
            SIGNAL_STRENGTH_FACTORS["corroboration"]  * corroboration       * 100 +
            SIGNAL_STRENGTH_FACTORS["competition"]    * competition_inverse * 100 +
            SIGNAL_STRENGTH_FACTORS["market_size"]    * market_size         * 100 +
            SIGNAL_STRENGTH_FACTORS["rising_boost"]   * rising_boost        * 100
        )
        return round(score, 1)

    # -- POP-Fit score --

    def compute_pop_fit(self, trend: dict) -> tuple[int, list]:
        """
        Returns (score, matched_lines).
        +30 points per POP line whose keywords overlap with trend["key_ingredients"].
        Capped at 100.
        """
        key_ings      = [k.lower() for k in trend.get("key_ingredients", [])]
        score         = 0
        matched_lines = []

        for line_key, line in POP_LINES.items():
            for kw in line["keywords"]:
                if any(kw.lower() in ing or ing in kw.lower() for ing in key_ings):
                    score += POP_FIT_POINTS_PER_LINE
                    matched_lines.append(line["display_name"])
                    break

        return min(score, POP_FIT_MAX), matched_lines

    # -- Market stage --

    def compute_market_stage(self, trend: dict) -> str:
        """
        Derives lifecycle label from growth_rate_pct and recency_score.
        emerging / growing / peaking / declining
        """
        growth  = trend.get("growth_rate_pct", 0)
        recency = trend.get("recency_score", 0.5)

        for stage, thresholds in MARKET_STAGE_THRESHOLDS.items():
            if growth >= thresholds["min_growth"] and recency >= thresholds["min_recency"]:
                return stage
        return "declining"

    # -- Action classifier --

    def classify_action(self, trend: dict, pop_fit_score: int, compliance_ok: bool) -> str:
        """
        DEVELOP    — high POP adjacency (pop_fit >= 50), window still open
        DISTRIBUTE — proven demand in POP's distributed categories or open shelf
        BOTH       — qualifies for both
        PASS       — compliance failed, weak fit, or window closed
        """
        if not compliance_ok:
            return "PASS"

        recency_ok = trend.get("recency_score", 0) >= 0.30
        growth_ok  = trend.get("growth_rate_pct", 0) >= 0

        can_develop = pop_fit_score >= 50 and recency_ok
        can_distribute = (
            (
                trend.get("category", "") in POP_DISTRIBUTED_CATEGORIES
                or trend.get("competition_density", 1.0) < 0.6
            )
            and growth_ok
        )

        if can_develop and can_distribute:
            return "BOTH"
        if can_develop:
            return "DEVELOP"
        if can_distribute:
            return "DISTRIBUTE"
        return "PASS"

    # -- Main scoring method --

    def score(self, trends: list[dict]) -> list[dict]:
        """
        Main Stage 3 method.
        Input:  list of normalized trend objects from TrendNormalizer.normalize()
        Output: same list with all scoring fields added, sorted by composite_score desc
        """
        results = []

        for trend in trends:
            t = dict(trend)

            shelf_ok,    shelf_months, shelf_note = self.check_shelf_life(t)
            fda_blocked, fda_watch,   fda_note   = self.check_fda_ingredients(t)
            risk_ok,     risk_score,  risk_note  = self.check_trade_risk(t)

            compliance_ok   = shelf_ok and not fda_blocked and risk_ok
            compliance_note = " | ".join([shelf_note, fda_note, risk_note])

            signal_strength           = self.compute_signal_strength(t)
            pop_fit, pop_line_matches = self.compute_pop_fit(t)
            market_stage              = self.compute_market_stage(t)

            composite = round(
                SIGNAL_STRENGTH_WEIGHT * signal_strength + POP_FIT_WEIGHT * pop_fit, 1
            ) if compliance_ok else 0.0

            action = self.classify_action(t, pop_fit, compliance_ok)

            t.update({
                "shelf_life_months": shelf_months,
                "shelf_life_ok":     shelf_ok,
                "fda_blocked":       fda_blocked,
                "fda_watch":         fda_watch,
                "trade_risk_score":  risk_score,
                "trade_risk_ok":     risk_ok,
                "compliance_ok":     compliance_ok,
                "compliance_note":   compliance_note,
                "signal_strength":   signal_strength,
                "pop_fit_score":     pop_fit,
                "pop_line_matches":  pop_line_matches,
                "market_stage":      market_stage,
                "composite_score":   composite,
                "action":            action,
            })
            results.append(t)

        results.sort(key=lambda t: t["composite_score"], reverse=True)
        return results

    # -- CSV export --

    def export_to_csv(self, scored_trends: list[dict], filepath: str = str(DEFAULT_REPORT_FILE)):
        """
        Flattens scored trend objects into a CSV/Excel-compatible file.
        23 columns ordered for buyer readability.
        """
        import pandas as pd

        COLUMNS = [
            "action", "composite_score", "name", "category", "market_stage",
            "growth_rate_pct", "recency_score", "competition_density",
            "signal_strength", "pop_fit_score", "pop_line_matches",
            "compliance_ok", "shelf_life_months", "fda_watch", "trade_risk_score",
            "sources", "source_count", "avg_gt_interest", "rising_query_count",
            "primary_source_country", "format", "compliance_note", "top_evidence",
        ]

        rows = []
        for t in scored_trends:
            top_evidence = " || ".join(
                e["snippet"][:100] for e in t.get("evidence", [])[:3]
            )
            rows.append({
                "action":               t.get("action"),
                "composite_score":      t.get("composite_score"),
                "name":                 t.get("name"),
                "category":             t.get("category"),
                "market_stage":         t.get("market_stage"),
                "growth_rate_pct":      t.get("growth_rate_pct"),
                "recency_score":        t.get("recency_score"),
                "competition_density":  t.get("competition_density"),
                "signal_strength":      t.get("signal_strength"),
                "pop_fit_score":        t.get("pop_fit_score"),
                "pop_line_matches":     ", ".join(t.get("pop_line_matches", [])),
                "compliance_ok":        t.get("compliance_ok"),
                "shelf_life_months":    t.get("shelf_life_months"),
                "fda_watch":            ", ".join(t.get("fda_watch", [])),
                "trade_risk_score":     t.get("trade_risk_score"),
                "sources":              ", ".join(t.get("sources", [])),
                "source_count":         t.get("source_count"),
                "avg_gt_interest":      t.get("avg_gt_interest"),
                "rising_query_count":   t.get("rising_query_count"),
                "primary_source_country": t.get("primary_source_country"),
                "format":               t.get("format"),
                "compliance_note":      t.get("compliance_note"),
                "top_evidence":         top_evidence,
            })

        EXPORTS_DIR.mkdir(parents=True, exist_ok=True)
        df = pd.DataFrame(rows, columns=COLUMNS)
        df.to_csv(filepath, index=False)
        print(f"[scoring] Exported {len(df)} trends to {filepath}")
        return df


# ---------------------------------------------------------------------------
# Module-level convenience functions — preserve public API for tests + scripts
# ---------------------------------------------------------------------------

_scorer = TrendScorer()

def check_shelf_life(trend):                              return _scorer.check_shelf_life(trend)
def check_fda_ingredients(trend):                        return _scorer.check_fda_ingredients(trend)
def check_trade_risk(trend):                             return _scorer.check_trade_risk(trend)
def compute_signal_strength(trend):                      return _scorer.compute_signal_strength(trend)
def compute_pop_fit(trend):                              return _scorer.compute_pop_fit(trend)
def compute_market_stage(trend):                         return _scorer.compute_market_stage(trend)
def classify_action(trend, pop_fit_score, compliance_ok): return _scorer.classify_action(trend, pop_fit_score, compliance_ok)
def score(trends):                                       return _scorer.score(trends)
def export_to_csv(scored_trends, filepath=str(DEFAULT_REPORT_FILE)): return _scorer.export_to_csv(scored_trends, filepath)


# ---------------------------------------------------------------------------
# Quick test — python scoring.py
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    from pop_trend_intelligence.pipeline.collectors import collect_all
    from pop_trend_intelligence.pipeline.discovery import TrendNormalizer

    print("Running Stage 1 + 2...")
    signals = collect_all()
    trends  = TrendNormalizer().normalize(signals)
    print(f"{len(trends)} trends normalized\n")

    print("Running Stage 3 scoring...")
    scorer = TrendScorer()
    scored = scorer.score(trends)

    ACTION_ICONS = {"BOTH": "🌟", "DEVELOP": "🔨", "DISTRIBUTE": "📦", "PASS": "—"}

    print(f"\n{'Trend':<28} {'Score':>6} {'Stage':<11} {'Action':<12} Compliance")
    print("─" * 100)
    for t in scored:
        icon   = ACTION_ICONS.get(t["action"], "")
        comply = "✅" if t["compliance_ok"] else "❌"
        print(
            f"{t['name']:<28} {t['composite_score']:>5.1f}  "
            f"{t['market_stage']:<11} "
            f"{icon} {t['action']:<10}  "
            f"{comply}  {t['compliance_note']}"
        )

    print("\n--- TOP OPPORTUNITIES ---")
    top = [t for t in scored if t["action"] in ("BOTH", "DEVELOP", "DISTRIBUTE")][:5]
    for t in top:
        print(f"\n{t['name']} [{t['action']}]  composite={t['composite_score']}  stage={t['market_stage']}")
        print(f"  Signal: {t['signal_strength']}  POP-Fit: {t['pop_fit_score']}  "
              f"Lines: {', '.join(t['pop_line_matches']) or 'none'}")
        print(f"  Growth: {t['growth_rate_pct']}%  GT Interest: {t['avg_gt_interest']}  "
              f"Rising queries: {t['rising_query_count']}  Sources: {t['source_count']}")
        for e in t["evidence"][:2]:
            print(f"  [{e['source']}] {e['snippet'][:85]}")

    scorer.export_to_csv(scored)
