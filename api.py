"""FastAPI backend for the POP Trend Intelligence frontend.

Serves the scored trend data produced by the Stage 1-3 pipeline
(collectors -> discovery -> scoring) and lets the frontend trigger a
fresh collection run. Row shape matches TrendScorer.export_to_csv
exactly, since that's the contract the frontend already reads against.
"""

from __future__ import annotations

import json

import pandas as pd
from fastapi import FastAPI

from pop_trend_intelligence.paths import DEFAULT_REPORT_FILE
from pop_trend_intelligence.pipeline.collectors import collect_all
from pop_trend_intelligence.pipeline.discovery import TrendNormalizer
from pop_trend_intelligence.pipeline.scoring import TrendScorer

app = FastAPI()

_scorer = TrendScorer()
_trends: list[dict] = []


def _records_from_df(df: pd.DataFrame) -> list[dict]:
    return json.loads(df.to_json(orient="records"))


def _run_pipeline() -> list[dict]:
    signals = collect_all()
    trends = TrendNormalizer().normalize(signals)
    scored = _scorer.score(trends)
    df = _scorer.export_to_csv(scored)
    return _records_from_df(df)


@app.on_event("startup")
def load_cached_trends() -> None:
    global _trends
    if DEFAULT_REPORT_FILE.exists():
        _trends = _records_from_df(pd.read_csv(DEFAULT_REPORT_FILE))
    else:
        _trends = _run_pipeline()


@app.get("/api/trends")
def get_trends() -> list[dict]:
    return _trends


@app.post("/api/refresh")
def refresh_trends() -> dict:
    global _trends
    _trends = _run_pipeline()
    return {"count": len(_trends)}
