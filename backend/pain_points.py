"""
Pain point inference: deterministic rules first, then LLM for nuance.

Rule engine fires on score thresholds + raw enrichment values.
LLM receives rules output and adds up to 2 additional insights grounded in data.
"""
from __future__ import annotations
from typing import Any, Dict, List
from .scoring import _parse_float


# ---------------------------------------------------------------------------
# Rule-based engine
# ---------------------------------------------------------------------------

def _rule_based_pain_points(
    enrichment: Dict[str, Any], scores: Dict[str, Any]
) -> List[Dict[str, Any]]:
    demand_score   = scores.get("demand", {}).get("score") or 0
    friction_score = scores.get("friction", {}).get("score") or 0
    scale_score    = scores.get("scale", {}).get("score") or 0
    news_sentiment = scores.get("opportunity", {}).get("news_sentiment", "none")

    census  = enrichment.get("census") or {}
    fred    = enrichment.get("fred") or {}
    ws      = enrichment.get("walkscore") or {}
    crime   = enrichment.get("crime") or {}
    climate = enrichment.get("open_meteo") or {}
    google  = enrichment.get("google") or {}
    ipins   = enrichment.get("intellipins") or {}

    vacancy      = _parse_float(fred.get("vacancy_rate"))
    renter_pct   = _parse_float(census.get("renter_percentage"))
    income       = _parse_float(census.get("median_income"))
    walk         = _parse_float(ws.get("walk_score"))
    transit      = _parse_float(ws.get("transit_score"))
    crime_score  = _parse_float(crime.get("crime_score"))
    crime_above  = crime.get("above_national_avg_violent", False)
    snowfall     = _parse_float(climate.get("annual_snowfall_cm"))
    precip_days  = _parse_float(climate.get("annual_precip_days"))
    rating       = _parse_float(google.get("rating"))
    review_count = _parse_float(google.get("review_count"))
    building_type = ipins.get("building_type")

    pps: List[Dict[str, Any]] = []

    # ── Core ICP: Apartment Complex ───────────────────────────────────────────
    if building_type == "Apartment Complex":
        pps.append({
            "tag": "core_icp",
            "label": "Core ICP — Multifamily Property",
            "severity": "high",
            "description": (
                "This is an apartment complex — EliseAI's primary ICP. Multifamily operators "
                "gain the most from AI-powered leasing (instant lead response, tour scheduling, "
                "renewal reminders) and maintenance coordination at scale."
            ),
            "source": "rule",
        })

    # ── Volume Overload ───────────────────────────────────────────────────────
    if demand_score >= 65 and scale_score >= 50:
        pps.append({
            "tag": "volume_overload",
            "label": "High Lead Volume Overload",
            "severity": "high",
            "description": (
                "High rental demand combined with a large property footprint likely floods "
                "property managers with inquiries. Manual handling causes slow response times "
                "and lost leases — precisely where EliseAI's automated engagement wins."
            ),
            "source": "rule",
        })

    # ── Premium Market Signal ─────────────────────────────────────────────────
    if walk is not None and walk >= 70 and income is not None and income >= 90_000:
        pps.append({
            "tag": "premium_market",
            "label": "Premium Market — Instant Response Required",
            "severity": "high",
            "description": (
                f"Walk Score {walk:.0f} and median household income ${income:,.0f} signal "
                "a quality renter base with high service expectations. Delayed responses directly "
                "cost leases; EliseAI provides 24/7 instant engagement."
            ),
            "source": "rule",
        })

    # ── Tight Market Competition ──────────────────────────────────────────────
    if vacancy is not None and vacancy < 5 and renter_pct is not None and renter_pct >= 45:
        pps.append({
            "tag": "tight_market",
            "label": "Tight Market — Speed Wins Leases",
            "severity": "high",
            "description": (
                f"A {vacancy:.1f}% vacancy rate with {renter_pct:.0f}% renters means fierce "
                "competition for units. The first team to respond wins the lease. "
                "EliseAI's instant AI engagement converts leads before competitors do."
            ),
            "source": "rule",
        })

    # ── Harsh Operating Conditions ────────────────────────────────────────────
    if friction_score >= 60:
        reasons = []
        if snowfall and snowfall > 50:
            reasons.append(f"heavy snowfall ({snowfall:.0f} cm/yr)")
        if precip_days and precip_days > 120:
            reasons.append(f"frequent precipitation ({precip_days:.0f} days/yr)")
        if crime_score and crime_score > 8:
            reasons.append("above-average crime")
        desc = (
            "Challenging conditions"
            + (f" ({', '.join(reasons)})" if reasons else "")
            + " increase maintenance coordination load and incident management. "
            "Automated tenant communication keeps residents informed without burdening staff."
        )
        pps.append({
            "tag": "harsh_conditions",
            "label": "Harsh Operating Conditions",
            "severity": "high" if friction_score >= 75 else "medium",
            "description": desc,
            "source": "rule",
        })

    # ── Rapid Portfolio Growth ────────────────────────────────────────────────
    if news_sentiment == "growth" and scale_score >= 35:
        pps.append({
            "tag": "scaling_pains",
            "label": "Rapid Portfolio Growth",
            "severity": "high",
            "description": (
                "Recent news indicates the company is actively expanding. Growth strains manual "
                "leasing and maintenance workflows. EliseAI scales instantly — no headcount needed."
            ),
            "source": "rule",
        })

    # ── Operational Cost Pressure ─────────────────────────────────────────────
    if news_sentiment == "cost_pressure":
        pps.append({
            "tag": "cost_pressure",
            "label": "Operational Cost Pressure",
            "severity": "medium",
            "description": (
                "News signals operational cost pressure. EliseAI reduces staffing costs for "
                "leasing and maintenance coordination while maintaining 24/7 response quality."
            ),
            "source": "rule",
        })

    # ── Resident Experience Gap ───────────────────────────────────────────────
    if rating is not None and review_count is not None and rating < 3.5 and review_count >= 15:
        pps.append({
            "tag": "resident_experience",
            "label": "Resident Experience Issues",
            "severity": "medium",
            "description": (
                f"A {rating}/5 Google rating across {int(review_count)} reviews often reflects "
                "slow response times and unresolved maintenance requests — both directly solvable "
                "with EliseAI's automated tenant communication workflows."
            ),
            "source": "rule",
        })

    # ── High Crime — Tenant Retention Risk ───────────────────────────────────
    if crime_above and crime_score is not None and crime_score > 9 \
            and vacancy is not None and vacancy > 5:
        pps.append({
            "tag": "retention_risk",
            "label": "High Crime — Tenant Retention Risk",
            "severity": "medium",
            "description": (
                "Above-average crime with elevated vacancy suggests higher tenant turnover. "
                "Proactive automated communication (maintenance updates, community alerts) "
                "can improve retention and reduce costly vacancy cycles."
            ),
            "source": "rule",
        })

    # ── Transit-Driven High Tenant Mobility ───────────────────────────────────
    if transit is not None and transit >= 70 and renter_pct is not None and renter_pct >= 50:
        pps.append({
            "tag": "high_mobility",
            "label": "High Tenant Mobility",
            "severity": "medium",
            "description": (
                f"Excellent transit access (Transit Score {transit:.0f}) in a renter-majority "
                f"area ({renter_pct:.0f}% renters) drives high turnover and a constant stream "
                "of new leads. Automating inquiry handling ensures none slip through."
            ),
            "source": "rule",
        })

    # Deduplicate by tag (preserve order)
    seen, unique = set(), []
    for pp in pps:
        if pp["tag"] not in seen:
            seen.add(pp["tag"])
            unique.append(pp)
    return unique


# ---------------------------------------------------------------------------
# LLM enrichment
# ---------------------------------------------------------------------------

async def _llm_enrich(
    lead_info: Dict[str, Any],
    enrichment: Dict[str, Any],
    scores: Dict[str, Any],
    rule_points: List[Dict[str, Any]],
    provider: str = "anthropic",
) -> List[Dict[str, Any]]:
    from .llm import chat_complete

    census  = enrichment.get("census") or {}
    fred    = enrichment.get("fred") or {}
    ws      = enrichment.get("walkscore") or {}
    wiki    = enrichment.get("wikipedia") or {}
    news    = enrichment.get("news") or {}
    crime   = enrichment.get("crime") or {}
    climate = enrichment.get("open_meteo") or {}
    google  = enrichment.get("google") or {}
    ipins   = enrichment.get("intellipins") or {}

    news_list = news.get("latest_news")
    news_list = news_list if isinstance(news_list, list) else []
    news_titles = [a.get("title", "") for a in news_list[:3]]
    reviews_summary = "; ".join(
        f"[{r.get('rating')}/5] {(r.get('text') or '')[:100]}"
        for r in (google.get("reviews") or [])[:3]
    ) or "None"

    existing_tags = {pp["tag"] for pp in rule_points}

    def _v(val):
        return val if val is not None else "N/A"

    prompt = f"""You are a B2B sales analyst for EliseAI (AI-powered property management automation: leasing, maintenance coordination, tenant communication, tour scheduling for multifamily housing operators).

Lead: {lead_info.get('name')} at {lead_info.get('company')} ({lead_info.get('city')}, {lead_info.get('state')})
Building type: {_v(ipins.get('building_type'))}

Data:
- Population: {_v(census.get('population'))} | Median income: {_v(census.get('median_income'))} | Renter %: {_v(census.get('renter_percentage'))}
- Vacancy rate: {_v(fred.get('vacancy_rate'))}
- Walk: {_v(ws.get('walk_score'))} | Transit: {_v(ws.get('transit_score'))} | Bike: {_v(ws.get('bike_score'))}
- Crime score (1-15): {_v(crime.get('crime_score'))} | Above national avg: {_v(crime.get('above_national_avg_violent'))}
- Precip days: {_v(climate.get('annual_precip_days'))} | Snowfall: {_v(climate.get('annual_snowfall_cm'))} cm | Temp: {_v(climate.get('coldest_day_c'))}–{_v(climate.get('hottest_day_c'))} °C
- Google rating: {_v(google.get('rating'))} ({google.get('review_count') or 0} reviews){f" | Google summary: {google.get('editorial_summary')}" if google.get('editorial_summary') else ""}
- Wikipedia company page: {'Yes' if isinstance(wiki.get('company'), dict) else 'No'}
- Recent news: {news_titles or ['None']}
- Sample reviews: {reviews_summary}

Scores — Demand: {_v(scores.get('demand', {}).get('score'))}/100 | Friction: {_v(scores.get('friction', {}).get('score'))}/100 | Scale: {_v(scores.get('scale', {}).get('score'))}/100 | Opportunity: {_v(scores.get('opportunity', {}).get('score'))}/100 | Lead: {_v(scores.get('lead_score', {}).get('score'))}/100

Already detected: {', '.join(existing_tags) or 'none'}

Add up to 2 additional pain points NOT already listed. Each must reference specific numbers from the data above and be addressable by EliseAI (leasing AI, maintenance coordination, tenant comms).

Respond ONLY as a JSON array. Each item: {{"tag": "snake_case", "label": "Short Label", "severity": "high|medium|low", "description": "1-2 sentences with specific data."}}
If no additional pain points, return []."""

    try:
        text = await chat_complete(prompt, provider=provider, max_tokens=500, fast=True)
        import json, re
        match = re.search(r"\[.*\]", text, re.DOTALL)
        if match:
            llm_points = json.loads(match.group())
            current_tags = {pp["tag"] for pp in rule_points}
            for pp in llm_points:
                if isinstance(pp, dict) and pp.get("tag") not in current_tags:
                    pp["source"] = "llm"
                    rule_points.append(pp)
                    current_tags.add(pp["tag"])
    except Exception as e:
        print(f"LLM pain point enrichment error ({provider}): {e}")

    return rule_points


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

async def infer_pain_points(
    lead_info: Dict[str, Any],
    enrichment: Dict[str, Any],
    scores: Dict[str, Any],
    provider: str = "anthropic",
) -> List[Dict[str, Any]]:
    rule_points = _rule_based_pain_points(enrichment, scores)
    return await _llm_enrich(lead_info, enrichment, scores, rule_points, provider=provider)
