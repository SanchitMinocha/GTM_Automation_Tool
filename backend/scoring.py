"""
Deterministic scoring from enriched lead data.

Each sub-score uses only available features (no imputation):
    score = sum(weight_i * feature_i) / sum(weights of available features)

All component values are normalized 0–1 before weighting.
Final sub-scores are 0–100.

Scoring Philosophy (V6):
    - Calibration: Ceilings set to practical "strong" values (e.g., 80 walk score,
      75 transit score, 250k pop, 40k sqft).
    - Concave Lifting (_lift, power 0.7): Applied to "indicator" signals where
      moderate values already represent meaningful intent (renter %, vacancy,
      income, snowfall, low rating, vacancy urgency).
    - Aggressive Convex Penalization (_crush, power 2.0): Applied to "structural"
      filters (walkability, population, footprint, floors, units) to ensure weak
      leads stay significantly below 50.
    - Ceiling calibration: walk/transit ceilings set so that "very walkable" /
      "excellent transit" scores (80+/75+) max out the component rather than being
      penalized by a needlessly high 100-point ceiling.
    - Decisive Opportunity: Triggers like growth news or established Wikipedia
      presence use high floors to ensure they can push a lead into Grade A.
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
    s = re.sub(r"\s+\S.*$", "", s).strip()  # strip trailing units
    try:
        return float(s)
    except ValueError:
        return None


def _weighted_score(components: Dict[str, Tuple[float, float]]) -> Tuple[float, float]:
    """components: {name: (normalized_0_to_1, weight)} -> (score_0_100, weight)"""
    if not components:
        return 0.0, 0.0
    total_weight = sum(w for _, w in components.values())
    score = sum(v * w for v, w in components.values()) / total_weight * 100
    return round(score, 1), round(total_weight, 3)


def _lift(x: float, power: float = 0.70) -> float:
    """Concave curve: lifts mid-range. For indicator signals where moderate = good."""
    return min(max(x, 0.0), 1.0) ** power


def _crush(x: float, power: float = 2.0) -> float:
    """Convex curve: penalizes low-mid range. For structural signals where low = bad."""
    return min(max(x, 0.0), 1.0) ** power


# ---------------------------------------------------------------------------
# 1. DEMAND SCORE (30%)
# ---------------------------------------------------------------------------

def score_demand(enrichment: Dict[str, Any]) -> Dict[str, Any]:
    census = enrichment.get("census") or {}
    fred   = enrichment.get("fred") or {}
    ws     = enrichment.get("walkscore") or {}
    osm    = enrichment.get("osm") or {}

    components: Dict[str, Tuple[float, float]] = {}

    # Renter %: ceiling 50%; LIFTED
    renter_pct = _parse_float(census.get("renter_percentage"))
    if renter_pct is not None and renter_pct > 0:
        components["renter_pct"] = (_lift(min(renter_pct / 50.0, 1.0)), 0.25)

    # Vacancy: ceiling 10%; LIFTED
    vacancy = _parse_float(fred.get("vacancy_rate"))
    if vacancy is not None:
        components["low_vacancy"] = (_lift(max(0.0, 1.0 - vacancy / 10.0)), 0.20)

    # Structural filters: CONVEX — ceiling at "very walkable" / "excellent transit"
    # so scores at those thresholds max out rather than being penalized by a 100-pt ceiling.
    walk = _parse_float(ws.get("walk_score"))
    if walk is not None:
        components["walk_score"] = (_crush(min(walk / 80.0, 1.0)), 0.15)

    transit = _parse_float(ws.get("transit_score"))
    if transit is not None:
        components["transit_score"] = (_crush(min(transit / 75.0, 1.0)), 0.10)

    income = _parse_float(census.get("median_income"))
    if income is not None and income > 0:
        components["income"] = (_lift(min(income / 85_000.0, 1.0)), 0.10)

    amenities = osm.get("amenities_1000m") or {}
    total_amenities = sum(_parse_float(v) or 0.0 for v in amenities.values())
    if amenities:
        components["nearby_amenities"] = (_lift(min(total_amenities / 40.0, 1.0)), 0.12)

    population = _parse_float(census.get("population"))
    if population is not None and population > 0:
        components["population"] = (_crush(min(population / 250_000.0, 1.0)), 0.08)

    score, avail = _weighted_score(components)
    return {"score": score, "available_weight": avail, "max_weight": 1.0,
            "components": {k: round(v * 100, 1) for k, (v, _) in components.items()}}


# ---------------------------------------------------------------------------
# 2. FRICTION SCORE (20%)
# ---------------------------------------------------------------------------

def score_friction(enrichment: Dict[str, Any]) -> Dict[str, Any]:
    climate = enrichment.get("open_meteo") or {}
    crime   = enrichment.get("crime") or {}
    ipins   = (enrichment.get("intellipins") or {}).get("parcel") or {}

    components: Dict[str, Tuple[float, float]] = {}

    crime_score = _parse_float(crime.get("crime_score"))
    if crime_score is not None:
        components["crime"] = (_crush((crime_score - 1.0) / 14.0), 0.25)

    precip_days = _parse_float(climate.get("annual_precip_days"))
    if precip_days is not None:
        components["precip_days"] = (_crush(min(precip_days / 120.0, 1.0)), 0.25)

    # Snowfall: indicator signal (any meaningful snow = friction), not structural filter
    snowfall = _parse_float(climate.get("annual_snowfall_cm"))
    if snowfall is not None:
        components["snowfall"] = (_lift(min(snowfall / 80.0, 1.0)), 0.20)

    hottest = _parse_float(climate.get("hottest_day_c"))
    coldest = _parse_float(climate.get("coldest_day_c"))
    if hottest is not None and coldest is not None:
        components["temp_range"] = (_crush(min((hottest - coldest) / 55.0, 1.0)), 0.20)

    elev = _parse_float(ipins.get("elevation_m"))
    if elev is not None:
        components["elevation"] = (_crush(min(elev / 800.0, 1.0)), 0.10)

    score, avail = _weighted_score(components)
    return {"score": score, "available_weight": avail, "max_weight": 1.0,
            "components": {k: round(v * 100, 1) for k, (v, _) in components.items()}}


# ---------------------------------------------------------------------------
# 3. SCALE SCORE (20%)
# ---------------------------------------------------------------------------

_BUILDING_TYPE_WEIGHT = {
    "Apartment Complex": 1.00, "Hotel": 0.80, "Commercial / Industrial": 0.75,
    "Office Building": 0.70, "Apartment / Shopping Complex": 0.65,
    "Shopping Complex / Amenity": 0.55, "Retail / Shopping": 0.45,
    "Single Family Housing": 0.20,
}

def score_scale(enrichment: Dict[str, Any]) -> Dict[str, Any]:
    osm = enrichment.get("osm") or {}
    ipins = enrichment.get("intellipins") or {}
    bd = (osm.get("building_details") or {})
    
    components: Dict[str, Tuple[float, float]] = {}
    
    btype = ipins.get("building_type")
    if btype:
        components["building_type"] = (_BUILDING_TYPE_WEIGHT.get(btype, 0.20), 0.30)

    footprint = _parse_float(bd.get("calculated_area"))
    _APT_TYPES = {"Apartment Complex", "Apartment / Shopping Complex"}
    if footprint is not None and footprint > 0:
        # OSM returns the address polygon for one unit in dense cities — tiny footprints
        # (<10k sqft) on apartment-type buildings are unreliable data, not small buildings.
        if not (btype in _APT_TYPES and footprint < 10_000):
            components["footprint"] = (_crush(min(footprint / 40_000.0, 1.0)), 0.25)

    lot_sqm = _parse_float((ipins.get("parcel") or {}).get("area_sqm"))
    if lot_sqm is not None and lot_sqm > 0:
        components["lot_area"] = (_lift(min(lot_sqm * 10.76 / 100_000.0, 1.0)), 0.20)

    floors = _parse_float(bd.get("floors"))
    if floors is not None and floors > 0:
        components["floors"] = (_crush(min(floors / 15.0, 1.0)), 0.15)

    units = _parse_float(bd.get("units"))
    if units is not None and units > 0:
        components["units"] = (_crush(min(units / 250.0, 1.0)), 0.10)

    score, avail = _weighted_score(components)
    return {"score": score, "available_weight": avail, "max_weight": 1.0, "building_type": btype,
            "components": {k: round(v * 100, 1) for k, (v, _) in components.items()}}


# ---------------------------------------------------------------------------
# 4. OPPORTUNITY SCORE (30%)
# ---------------------------------------------------------------------------

_GROWTH_KEYWORDS = ["expand", "acquir", "growth", "new market", "scale", "portfolio", "launch", "partner", "open", "hire", "invest"]
_COST_KEYWORDS = ["layoff", "restructur", "downsize", "cost-cut", "job cut", "budget", "deficit", "closure", "reduce staff"]
_TROUBLE_KEYWORDS = ["lawsuit", "fine", "penalty", "complaint", "eviction", "fraud", "investigation"]

def _analyze_news(news: Dict[str, Any]) -> Tuple[str, float]:
    articles = news.get("latest_news", [])
    if not isinstance(articles, list) or not articles: return "none", 0.30
    combined = " ".join((a.get("title", "") + " " + a.get("snippet", "")).lower() for a in articles[:5])
    growth, cost, trouble = [sum(1 for kw in kws if kw in combined) for kws in [_GROWTH_KEYWORDS, _COST_KEYWORDS, _TROUBLE_KEYWORDS]]
    if growth >= 2: return "growth", 0.95
    if cost >= 2: return "cost_pressure", 0.85
    if trouble >= 2: return "trouble", 0.75
    if growth + cost + trouble >= 1: return "mixed", 0.60
    return "neutral", 0.45

def score_opportunity(enrichment: Dict[str, Any]) -> Dict[str, Any]:
    news, google, wiki = [enrichment.get(k) or {} for k in ["news", "google", "wikipedia"]]
    components: Dict[str, Tuple[float, float]] = {}

    news_tag, news_score = _analyze_news(news)
    if isinstance(news.get("latest_news"), list): components["news_signal"] = (news_score, 0.5)

    rating = _parse_float(google.get("rating"))
    if rating is not None:
        # Linear raw score then _lift: low ratings are indicator signals (moderate pain = moderate signal)
        raw_lr = max(0.0, 1.0 - (rating - 1.0) / 3.5)
        components["low_rating"] = (_lift(raw_lr), 0.35)

    if isinstance(wiki.get("company"), dict): components["wiki_presence"] = (0.90, 0.15)

    score, avail = _weighted_score(components)
    return {"score": score, "available_weight": avail, "max_weight": 1.0, "news_sentiment": news_tag,
            "components": {k: round(v * 100, 1) for k, (v, _) in components.items()}}


# ---------------------------------------------------------------------------
# 5. LEAD SCORE
# ---------------------------------------------------------------------------

_LEAD_WEIGHTS = {"demand": 0.30, "friction": 0.20, "scale": 0.20, "opportunity": 0.30}

def compute_lead_score(sub_scores: Dict[str, Dict]) -> Dict[str, Any]:
    components: Dict[str, Tuple[float, float]] = {}
    for name, weight in _LEAD_WEIGHTS.items():
        sub = sub_scores.get(name, {})
        s, avail = sub.get("score"), sub.get("available_weight", 0)
        if s is not None and avail > 0: components[name] = (s / 100.0, weight * avail)
    
    total = sum(w for _, w in components.values())
    if total == 0: return {"score": 0.0, "grade": "F", "available_weight": 0.0, "weights": _LEAD_WEIGHTS}
    
    score = round(sum(v * w for v, w in components.values()) / total * 100, 1)
    grade = "A" if score >= 80 else "B" if score >= 65 else "C" if score >= 50 else "D" if score >= 35 else "F"
    return {"score": score, "grade": grade, "available_weight": round(total, 3), "weights": _LEAD_WEIGHTS,
            "components": {k: round(v * 100, 1) for k, (v, _) in components.items()}}

def compute_all_scores(enrichment: Dict[str, Any]) -> Dict[str, Any]:
    scores = {k: f(enrichment) for k, f in [("demand", score_demand), ("friction", score_friction), ("scale", score_scale), ("opportunity", score_opportunity)]}
    scores["lead_score"] = compute_lead_score(scores)
    return scores
