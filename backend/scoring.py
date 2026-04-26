"""
Deterministic scoring from enriched lead data.

Each sub-score uses only available features (no imputation):
    score = sum(weight_i * feature_i) / sum(weights of available features)

All component values are normalized 0–1 before weighting.
Final sub-scores are 0–100.
"""
from __future__ import annotations
import re
from typing import Any, Dict, Optional, Tuple


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _parse_float(value: Any) -> Optional[float]:
    """Extract numeric value from formatted strings like '$75,000', '45.2%', '12,345 sq ft'."""
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    s = str(value).strip().replace("$", "").replace(",", "").replace("%", "")
    s = re.sub(r"\s+\S.*$", "", s).strip()  # strip trailing units (sq ft, cm, etc.)
    try:
        return float(s)
    except ValueError:
        return None


def _safe_get(d: Any, *keys, default=None) -> Any:
    """None-safe nested dict get."""
    for key in keys:
        if not isinstance(d, dict):
            return default
        d = d.get(key)
        if d is None:
            return default
    return d


def _weighted_score(components: Dict[str, Tuple[float, float]]) -> Tuple[float, float]:
    """
    components: {name: (normalized_0_to_1, weight)}
    Returns (score_0_to_100, total_available_weight)
    Missing components should be excluded before calling.
    """
    if not components:
        return 0.0, 0.0
    total_weight = sum(w for _, w in components.values())
    score = sum(v * w for v, w in components.values()) / total_weight * 100
    return round(score, 1), round(total_weight, 3)


# ---------------------------------------------------------------------------
# 1. DEMAND SCORE — rental market pressure / how overwhelmed managers are
# ---------------------------------------------------------------------------

def score_demand(enrichment: Dict[str, Any]) -> Dict[str, Any]:
    """
    Weights (max 1.0):
      renter_pct        0.25  — higher % renters = more rental market activity
      low_vacancy       0.20  — lower vacancy = tighter market = more leads
      walk_score        0.15  — walkability drives renter demand
      transit_score     0.10  — transit access expands renter pool
      income            0.10  — higher income = premium renters with high expectations
      nearby_amenities  0.12  — 1000m radius transit+parks+retail density
      population        0.08  — high-pop cities have denser renter concentrations
    """
    census = enrichment.get("census") or {}
    fred   = enrichment.get("fred") or {}
    ws     = enrichment.get("walkscore") or {}
    osm    = enrichment.get("osm") or {}

    components: Dict[str, Tuple[float, float]] = {}

    renter_pct = _parse_float(census.get("renter_percentage"))
    if renter_pct is not None and renter_pct > 0:
        components["renter_pct"] = (min(renter_pct / 70.0, 1.0), 0.25)

    vacancy = _parse_float(fred.get("vacancy_rate"))
    if vacancy is not None:
        components["low_vacancy"] = (max(0.0, 1.0 - vacancy / 15.0), 0.20)

    walk = _parse_float(ws.get("walk_score"))
    if walk is not None:
        components["walk_score"] = (walk / 100.0, 0.15)

    transit = _parse_float(ws.get("transit_score"))
    if transit is not None:
        components["transit_score"] = (transit / 100.0, 0.10)

    income = _parse_float(census.get("median_income"))
    if income is not None and income > 0:
        components["income"] = (min(income / 150_000.0, 1.0), 0.10)

    amenities = osm.get("amenities_1000m") or {}
    transit_ct = _parse_float(amenities.get("transit")) or 0.0
    parks_ct   = _parse_float(amenities.get("parks"))   or 0.0
    retail_ct  = _parse_float(amenities.get("retail"))  or 0.0
    total_amenities = transit_ct + parks_ct + retail_ct
    if amenities:  # only add if amenity data was actually fetched
        components["nearby_amenities"] = (min(total_amenities / 100.0, 1.0), 0.12)

    population = _parse_float(census.get("population"))
    if population is not None and population > 0:
        components["population"] = (min(population / 500_000.0, 1.0), 0.08)

    score, avail = _weighted_score(components)
    return {
        "score": score,
        "available_weight": avail,
        "max_weight": 1.0,
        "components": {k: round(v * 100, 1) for k, (v, _) in components.items()},
    }


# ---------------------------------------------------------------------------
# 2. FRICTION SCORE — operational difficulty (weather, crime, geography)
# ---------------------------------------------------------------------------

def score_friction(enrichment: Dict[str, Any]) -> Dict[str, Any]:
    """
    Weights (max 1.0):
      crime        0.25  — crime score (1–15) → normalized; drives security overhead
      precip_days  0.25  — rain days → virtual/3D tour demand spikes in bad weather
      snowfall     0.20  — annual snowfall → HVAC/plumbing load + in-person tour friction
      temp_range   0.20  — extreme temperature swings → maintenance complexity
      elevation    0.10  — high elevation → harsher winters, infrastructure stress
    """
    climate = enrichment.get("open_meteo") or {}
    crime   = enrichment.get("crime") or {}
    ipins   = enrichment.get("intellipins") or {}

    components: Dict[str, Tuple[float, float]] = {}

    crime_score = _parse_float(crime.get("crime_score"))
    if crime_score is not None:
        components["crime"] = ((crime_score - 1.0) / 14.0, 0.25)  # normalize 1–15 → 0–1

    precip_days = _parse_float(climate.get("annual_precip_days"))
    if precip_days is not None:
        components["precip_days"] = (min(precip_days / 200.0, 1.0), 0.25)

    snowfall = _parse_float(climate.get("annual_snowfall_cm"))
    if snowfall is not None:
        components["snowfall"] = (min(snowfall / 200.0, 1.0), 0.20)

    hottest = _parse_float(climate.get("hottest_day_c"))
    coldest = _parse_float(climate.get("coldest_day_c"))
    if hottest is not None and coldest is not None:
        components["temp_range"] = (min((hottest - coldest) / 80.0, 1.0), 0.20)

    elev = _parse_float(_safe_get(ipins, "parcel", "elevation_m"))
    if elev is not None:
        components["elevation"] = (min(elev / 2000.0, 1.0), 0.10)

    score, avail = _weighted_score(components)
    return {
        "score": score,
        "available_weight": avail,
        "max_weight": 1.0,
        "components": {k: round(v * 100, 1) for k, (v, _) in components.items()},
    }


# ---------------------------------------------------------------------------
# 3. SCALE SCORE — portfolio size & operational complexity
# ---------------------------------------------------------------------------

_BUILDING_TYPE_WEIGHT = {
    "Apartment Complex":            1.00,
    "Hotel":                        0.80,
    "Commercial / Industrial":      0.75,
    "Office Building":              0.70,
    "Apartment / Shopping Complex": 0.65,
    "Shopping Complex / Amenity":   0.60,
    "Retail / Shopping":            0.50,
    "Single Family Housing":        0.45,
}


def score_scale(enrichment: Dict[str, Any]) -> Dict[str, Any]:
    """
    Weights (max 1.0):
      building_type  0.30  — apartment complex = highest automation value
      footprint      0.25  — OSM building area in sq ft
      lot_area       0.20  — Intellipins parcel area
      floors         0.15  — vertical complexity / unit count proxy
      units          0.10  — explicit unit count from OSM tags
    """
    osm   = enrichment.get("osm") or {}
    ipins = enrichment.get("intellipins") or {}
    bd    = (osm.get("building_details") or {})

    components: Dict[str, Tuple[float, float]] = {}

    building_type = ipins.get("building_type")
    if building_type:
        components["building_type"] = (_BUILDING_TYPE_WEIGHT.get(building_type, 0.20), 0.30)

    footprint = _parse_float(bd.get("calculated_area"))
    if footprint is not None and footprint > 0:
        components["footprint"] = (min(footprint / 100_000.0, 1.0), 0.25)

    lot_sqm = _parse_float(_safe_get(ipins, "parcel", "area_sqm"))
    if lot_sqm is not None and lot_sqm > 0:
        components["lot_area"] = (min(lot_sqm * 10.7639 / 200_000.0, 1.0), 0.20)

    floors = _parse_float(bd.get("floors"))
    if floors is not None and floors > 0:
        components["floors"] = (min(floors / 30.0, 1.0), 0.15)

    units = _parse_float(bd.get("units"))
    if units is not None and units > 0:
        components["units"] = (min(units / 500.0, 1.0), 0.10)

    score, avail = _weighted_score(components)
    return {
        "score": score,
        "available_weight": avail,
        "max_weight": 1.0,
        "building_type": building_type,
        "components": {k: round(v * 100, 1) for k, (v, _) in components.items()},
    }


# ---------------------------------------------------------------------------
# 4. OPPORTUNITY SCORE — likelihood they need EliseAI right now
# ---------------------------------------------------------------------------

_GROWTH_KEYWORDS  = ["expand", "acquir", "growth", "new market", "scale", "portfolio",
                      "launch", "partner", "open", "hire", "invest"]
_COST_KEYWORDS    = ["layoff", "restructur", "downsize", "cost-cut", "job cut",
                      "budget", "deficit", "closure", "reduce staff"]
_TROUBLE_KEYWORDS = ["lawsuit", "fine", "penalty", "complaint", "eviction", "fraud", "investigation"]


def _analyze_news(news: Dict[str, Any]) -> Tuple[str, float]:
    """
    Returns (sentiment_tag, opportunity_score_0_to_1).
    growth → 0.85 (scaling = needs automation)
    cost_pressure → 0.75 (efficiency = open to AI)
    trouble → 0.65 (operational pain = addressable)
    mixed → 0.55
    neutral → 0.40
    none → 0.30
    """
    articles = news.get("latest_news", [])
    if not isinstance(articles, list) or not articles:
        return "none", 0.30
    combined = " ".join(
        (a.get("title", "") + " " + a.get("snippet", "")).lower()
        for a in articles[:5]
    )
    growth  = sum(1 for kw in _GROWTH_KEYWORDS  if kw in combined)
    cost    = sum(1 for kw in _COST_KEYWORDS    if kw in combined)
    trouble = sum(1 for kw in _TROUBLE_KEYWORDS if kw in combined)

    if growth >= 2:                        return "growth",        0.85
    if cost >= 2:                          return "cost_pressure", 0.75
    if trouble >= 2:                       return "trouble",       0.65
    if growth + cost + trouble >= 1:       return "mixed",         0.55
    return "neutral", 0.40


def score_opportunity(enrichment: Dict[str, Any]) -> Dict[str, Any]:
    """
    Weights (max 1.0):
      news_signal     0.30  — company growth/struggle signals
      low_rating      0.20  — poor Google rating → operational pain EliseAI solves
      renter_market   0.15  — high renter % → large addressable rental market
      vacancy_urgency 0.15  — higher vacancy → struggling to fill → needs help
      walkability     0.10  — high walk score → premium market with high expectations
      wiki_presence   0.10  — established company worth targeting
    """
    news   = enrichment.get("news") or {}
    census = enrichment.get("census") or {}
    fred   = enrichment.get("fred") or {}
    google = enrichment.get("google") or {}
    wiki   = enrichment.get("wikipedia") or {}
    ws     = enrichment.get("walkscore") or {}

    components: Dict[str, Tuple[float, float]] = {}

    news_tag, news_score = _analyze_news(news)
    if isinstance(news.get("latest_news"), list):
        components["news_signal"] = (news_score, 0.30)

    rating = _parse_float(google.get("rating"))
    if rating is not None:
        # rating 1/5 = 0.90 opportunity, rating 5/5 = 0.20 opportunity; skipped entirely when Google data unavailable
        components["low_rating"] = (max(0.0, 0.90 - (rating - 1.0) / 4.0 * 0.70), 0.20)

    renter_pct = _parse_float(census.get("renter_percentage"))
    if renter_pct is not None and renter_pct > 0:
        components["renter_market"] = (min(renter_pct / 65.0, 1.0), 0.15)

    vacancy = _parse_float(fred.get("vacancy_rate"))
    if vacancy is not None:
        # 0% = 0.30 (stable, low urgency), 10%+ = 0.90 (struggling)
        components["vacancy_urgency"] = (min(0.30 + vacancy / 10.0 * 0.60, 0.90), 0.15)

    walk = _parse_float(ws.get("walk_score"))
    if walk is not None:
        components["walkability"] = (walk / 100.0, 0.10)

    if isinstance(wiki.get("company"), dict):
        components["wiki_presence"] = (0.80, 0.10)

    score, avail = _weighted_score(components)
    return {
        "score": score,
        "available_weight": avail,
        "max_weight": 1.0,
        "news_sentiment": news_tag,
        "components": {k: round(v * 100, 1) for k, (v, _) in components.items()},
    }


# ---------------------------------------------------------------------------
# 5. LEAD SCORE — weighted composite of sub-scores
# ---------------------------------------------------------------------------

_LEAD_WEIGHTS = {
    "demand":      0.20,
    "friction":    0.35,
    "scale":       0.15,
    "opportunity": 0.30,
}


def compute_lead_score(sub_scores: Dict[str, Dict]) -> Dict[str, Any]:
    components: Dict[str, Tuple[float, float]] = {}
    for name, weight in _LEAD_WEIGHTS.items():
        sub = sub_scores.get(name, {})
        s = sub.get("score")
        avail = sub.get("available_weight", 0)
        # Skip sub-score if fewer than 30% of its max weight is available (too little data)
        if s is not None and avail >= 0.30:
            components[name] = (s / 100.0, weight)

    total = sum(w for _, w in components.values())
    if total == 0:
        return {"score": 0.0, "grade": "F", "available_weight": 0.0, "weights": _LEAD_WEIGHTS}

    raw = sum(v * w for v, w in components.values()) / total * 100
    score = round(raw, 1)
    grade = "A" if score >= 75 else "B" if score >= 60 else "C" if score >= 45 else "D" if score >= 30 else "F"

    return {
        "score": score,
        "grade": grade,
        "available_weight": round(total, 3),
        "components": {k: round(v * 100, 1) for k, (v, _) in components.items()},
        "weights": _LEAD_WEIGHTS,
    }


def compute_all_scores(enrichment: Dict[str, Any]) -> Dict[str, Any]:
    scores = {
        "demand":      score_demand(enrichment),
        "friction":    score_friction(enrichment),
        "scale":       score_scale(enrichment),
        "opportunity": score_opportunity(enrichment),
    }
    scores["lead_score"] = compute_lead_score(scores)
    return scores
