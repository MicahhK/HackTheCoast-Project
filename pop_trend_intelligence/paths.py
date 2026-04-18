"""Workspace-relative paths for generated project artifacts."""

from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parent.parent
ARTIFACTS_DIR = ROOT_DIR / "artifacts"
CACHE_DIR = ARTIFACTS_DIR / "cache"
EXPORTS_DIR = ARTIFACTS_DIR / "exports"

GT_CACHE_FILE = CACHE_DIR / "gt_cache.json"
DEFAULT_REPORT_FILE = EXPORTS_DIR / "pop_trend_report.csv"
