"""Convenience entry point for the POP trend pipeline."""

from pop_trend_intelligence import collect_all
from pop_trend_intelligence.pipeline.discovery import TrendNormalizer
from pop_trend_intelligence.pipeline.scoring import TrendScorer


def main() -> None:
    signals = collect_all()
    trends = TrendNormalizer().normalize(signals)
    scorer = TrendScorer()
    scored = scorer.score(trends)
    scorer.export_to_csv(scored)

    print(f"Collected {len(signals)} raw signals")
    print(f"Normalized {len(trends)} trends")
    print(f"Scored {len(scored)} trends")


if __name__ == "__main__":
    main()
