"""
POP Reference Data — used by scoring.py (Stage 3).

All business rules, thresholds, and catalog data for Prince of Peace Enterprises.
Edit this file to update POP's sourcing criteria without touching scoring logic.
"""

# ---------------------------------------------------------------------------
# SHELF LIFE TABLE
# Format string (from INGREDIENT_CATALOG) -> shelf life in months
# POP minimum: 12 months. Anything below is auto-disqualified.
# ---------------------------------------------------------------------------

SHELF_LIFE_TABLE = {
    "kombucha":               2,
    "fresh/refrigerated":     1,
    "chips/crackers":         9,
    "snack bar":              12,
    "chewy candy":            24,
    "chocolate":              18,
    "dry tea":                36,
    "instant powder":         36,
    "supplement / capsule":   36,
    "shelf-stable beverage":  18,
    "ready-to-drink bottle":  18,
    "topical ointment":       60,
    "dried fruit":            18,
}

SHELF_LIFE_MIN_MONTHS = 12


# ---------------------------------------------------------------------------
# FDA RESTRICTED / WATCH-LIST INGREDIENTS
# "banned"     -> fda_blocked = True, composite zeroed
# "restricted" -> fda_blocked = True, composite zeroed
# "watch"      -> added to fda_watch list, NOT blocked — buyer judgment call
# ---------------------------------------------------------------------------

FDA_STATUS = {
    "cbd":                              "restricted",
    "cannabidiol":                      "restricted",
    "kratom":                           "watch",
    "mitragyna speciosa":               "watch",
    "kava":                             "watch",
    "piper methysticum":                "watch",
    "ephedra":                          "banned",
    "ephedrine":                        "banned",
    "red yeast rice":                   "restricted",
    "monacolin k":                      "restricted",
    "delta-8 thc":                      "restricted",
    "delta-8":                          "restricted",
    "cannabis":                         "restricted",
    "thc":                              "restricted",
    "psilocybin":                       "banned",
    "nmn":                              "watch",
    "nicotinamide mononucleotide":      "watch",
    "tianeptine":                       "banned",
    "raw milk":                         "restricted",
    "colloidal silver":                 "watch",
}

FDA_BLOCK_STATUSES = {"banned", "restricted"}


# ---------------------------------------------------------------------------
# COUNTRY TRADE RISK SCORES (0.0 = no risk, 1.0 = sanctioned/blocked)
# POP threshold: > 0.60 blocks NEW categories.
# Exception: China is allowed for organic_teas (existing supply chain).
# ---------------------------------------------------------------------------

COUNTRY_RISK = {
    "usa":              0.00,
    "united states":    0.00,
    "italy":            0.05,   # Loacker
    "poland":           0.05,   # Ferrero Rocher
    "japan":            0.15,
    "south korea":      0.15,
    "korea":            0.15,
    "taiwan":           0.15,   # Tiger Balm patches
    "new zealand":      0.20,
    "australia":        0.20,
    "malaysia":         0.20,   # Tiger Balm patches
    "indonesia":        0.30,   # Ginger Chews co-packers
    "philippines":      0.30,
    "thailand":         0.35,
    "india":            0.35,
    "peru":             0.40,
    "vietnam":          0.45,
    "mexico":           0.45,
    "china":            0.85,
    "russia":           1.00,
    "iran":             1.00,
    "north korea":      1.00,
}

COUNTRY_RISK_THRESHOLD  = 0.60
CHINA_EXEMPT_CATEGORIES = {
    "organic_teas",        # D-13206/14206/15206/18206 — existing China supply chain
    "functional_confection",  # D-04011..D-04061 Ginger Honey Crystals — all China-sourced
}


# ---------------------------------------------------------------------------
# POP PROPRIETARY LINES
# Used for POP-Fit scoring: +30 points per line whose keywords overlap
# with a trend's key_ingredients. Capped at 100.
# ---------------------------------------------------------------------------

POP_LINES = {
    "ginger_chews": {
        "display_name": "POP Ginger Chews",
        "keywords":     ["ginger", "chew", "candy", "chewy"],
        "dev_angle":    "Add functional ingredients (adaptogens, turmeric, mushroom) to chew format",
        "skus":         17,
    },
    "ginger_honey_crystals": {
        "display_name": "POP Ginger Honey Crystals",
        "keywords":     ["ginger", "honey", "turmeric", "wellness shot", "manuka"],
        "dev_angle":    "Expand into wellness shots (elderberry, manuka, ACV)",
        "skus":         6,
    },
    "american_ginseng": {
        "display_name": "American Ginseng",
        "keywords":     ["ginseng", "american ginseng", "adaptogen", "nootropic"],
        "dev_angle":    "Every adaptogen trend is a potential co-formulation",
        "skus":         13,
    },
    "functional_herbal_teas": {
        "display_name": "POP Herbal Teas",
        "keywords":     ["herbal", "tea", "functional tea", "reishi", "mushroom", "elderberry", "immunity"],
        "dev_angle":    "Extend into trending health concerns (metabolic, sleep, cognitive)",
        "skus":         3,
    },
    "organic_teas": {
        "display_name": "POP Organic Teas",
        "keywords":     ["tea", "matcha", "latte powder", "green tea", "oolong"],
        "dev_angle":    "Latte powders and flavored teas via existing China supply chain",
        "skus":         4,
    },
}

POP_FIT_POINTS_PER_LINE = 30
POP_FIT_MAX             = 100

# ---------------------------------------------------------------------------
# DISTRIBUTED BRAND CATEGORIES
# Used in action classifier: if a trend's category matches one of these,
# it qualifies for DISTRIBUTE consideration.
# ---------------------------------------------------------------------------

POP_DISTRIBUTED_CATEGORIES = {
    "functional beverage",
    "functional food",
    "functional confection",
    "health & wellness",
    "personal care",
    "topical",
    "chocolate",       # Ferrero Rocher — active distributed brand
    "snack",           # Loacker wafers — active distributed brand
    "asian grocery",   # Totole bouillon, Mazola oil — existing distribution infrastructure
}

# ---------------------------------------------------------------------------
# COMPOSITE SCORE WEIGHTS
# ---------------------------------------------------------------------------

SIGNAL_STRENGTH_WEIGHT = 0.55
POP_FIT_WEIGHT         = 0.45

SIGNAL_STRENGTH_FACTORS = {
    "growth_rate":   0.35,   # velocity — is the window still open?
    "recency":       0.30,   # timing — early vs late in the trend cycle
    "corroboration": 0.15,   # cross-source confirmation reduces false signals
    "competition":   0.10,   # shelf opportunity (low weight — alone not actionable)
    "market_size":   0.05,   # absolute GT interest — market viability floor
    "rising_boost":  0.05,   # breakout sub-queries — trend spawning sub-categories
}

MAX_SOURCES         = 5    # GT + Reddit + RSS + Amazon + FDA
MAX_GROWTH_PCT      = 200  # cap before normalizing growth to 0–100
MAX_RISING_QUERIES  = 4    # cap for rising_query_count normalization

# market_stage thresholds — derived from growth_rate_pct and recency_score
MARKET_STAGE_THRESHOLDS = {
    "emerging":  {"min_growth": 10,   "min_recency": 0.45},
    "growing":   {"min_growth": 0,    "min_recency": 0.35},
    "peaking":   {"min_growth": -10,  "min_recency": 0.30},
    # "declining" is the fallback when none of the above match
}
