"""
LLM-powered personalized outreach email generation.

Story arc is selected deterministically from scores + pain point tags.
The LLM only writes sentences — story selection and data pre-selection happen here.
"""
from __future__ import annotations
from datetime import datetime
from typing import Any, Dict, List, Optional


# ---------------------------------------------------------------------------
# Arc selection — deterministic from scores + pain point tags
# ---------------------------------------------------------------------------

def _select_arc(scores: Dict[str, Any], pain_points: List[Dict[str, Any]]) -> str:
    """
    Returns one of: reputation_gap | operational_friction | growth_strain |
                    premium_expectations | lead_speed

    Priority is ordered by specificity of signal — most concrete data wins.
    """
    tags     = {pp["tag"] for pp in pain_points if pp.get("severity") in ("high", "medium")}
    friction = (scores.get("friction")    or {}).get("score", 0) or 0
    news_tag = (scores.get("opportunity") or {}).get("news_sentiment", "none")

    if "resident_experience" in tags:
        return "reputation_gap"
    if "premium_market" in tags:
        return "premium_expectations"
    if friction >= 50 or "maintenance_request_backlog" in tags or "harsh_conditions" in tags:
        return "operational_friction"
    if "scaling_pains" in tags or news_tag == "growth":
        return "growth_strain"
    return "lead_speed"


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

def _c_to_f(c) -> Optional[int]:
    try:
        return round(float(c) * 9 / 5 + 32)
    except (TypeError, ValueError):
        return None


def _snow_ft(cm) -> Optional[str]:
    if not cm:
        return None
    ft = float(cm) / 30.48
    if ft < 0.5:
        return None
    return f"~{ft:.1f} ft" if ft < 2 else f"~{round(ft)} ft"


# ---------------------------------------------------------------------------
# Arc context builders — each picks only the facts relevant to its story
# ---------------------------------------------------------------------------

def _arc_context(
    arc: str,
    enrichment: Dict[str, Any],
    scores: Dict[str, Any],
) -> str:
    climate = enrichment.get("open_meteo") or {}
    census  = enrichment.get("census") or {}
    fred    = enrichment.get("fred") or {}
    ws      = enrichment.get("walkscore") or {}
    google  = enrichment.get("google") or {}
    news    = enrichment.get("news") or {}
    crime   = enrichment.get("crime") or {}

    parts: List[str] = []

    if arc == "reputation_gap":
        rating = google.get("rating")
        count  = google.get("review_count")
        if rating:
            parts.append(f"Google rating: {rating}/5 ({int(count or 0)} reviews)")
        reviews = google.get("reviews") or []
        # Prefer negative reviews — they anchor the story
        negative = [
            r["text"] for r in reviews
            if r.get("text") and (r.get("rating") or 5) <= 3
        ]
        if negative:
            parts.append(f'Sample negative review: "{negative[0][:200]}"')
        elif reviews:
            excerpt = "; ".join(r["text"] for r in reviews[:2] if r.get("text"))[:250]
            if excerpt:
                parts.append(f"Sample reviews: {excerpt}")

    elif arc == "operational_friction":
        snow      = _snow_ft(climate.get("annual_snowfall_cm"))
        precip    = round(climate["annual_precip_days"]) if climate.get("annual_precip_days") else None
        hottest_f = _c_to_f(climate.get("hottest_day_c"))
        coldest_f = _c_to_f(climate.get("coldest_day_c"))
        if snow:
            parts.append(f"Annual snowfall: {snow}")
        if precip:
            parts.append(f"Precipitation days/year: ~{precip}")
        if hottest_f and coldest_f:
            parts.append(f"Temperature range: {coldest_f}°F (winter low) to {hottest_f}°F (summer high)")
        crime_score = crime.get("crime_score")
        try:
            if crime_score is not None and float(crime_score) > 9:
                parts.append(f"Crime index: {crime_score}/15 (above national average)")
        except (ValueError, TypeError):
            pass

    elif arc == "growth_strain":
        items = (news.get("latest_news") or [])[:2]
        if items:
            headlines = "; ".join(a.get("title", "") for a in items if a.get("title"))
            if headlines:
                parts.append(f"Recent news: {headlines}")
        scale_score = (scores.get("scale") or {}).get("score")
        if scale_score:
            parts.append(f"Scale score: {scale_score}/100")

    elif arc == "premium_expectations":
        walk   = ws.get("walk_score")
        income = census.get("median_income")
        if walk:
            try:
                parts.append(f"Walk Score: {int(float(walk))}")
            except (ValueError, TypeError):
                pass
        if income:
            try:
                val = float(str(income).replace(",", "").replace("$", ""))
                parts.append(f"Median household income: ${val:,.0f}")
            except (ValueError, TypeError):
                parts.append(f"Median household income: {income}")
        if ws.get("description"):
            parts.append(f"Neighborhood: {ws['description']}")
        rating = google.get("rating")
        if rating:
            parts.append(f"Google rating: {rating}/5")

    elif arc == "lead_speed":
        vacancy = fred.get("vacancy_rate")
        renter  = census.get("renter_percentage")
        if vacancy:
            parts.append(f"Vacancy rate: {vacancy}")
        if renter:
            parts.append(f"Renter share: {renter}")

    return "\n".join(f"- {p}" for p in parts)


# ---------------------------------------------------------------------------
# Arc-specific story instructions — the narrative skeleton the LLM fills in
# ---------------------------------------------------------------------------

_ARC_STORY = {
    "reputation_gap": """\
STORY ARC — Reputation Gap:
Their Google reviews are the first thing a prospect sees. A low rating signals slow maintenance response and poor communication — both directly solvable with EliseAI.

WRITE THREE SHORT PARAGRAPHS (~150–200 words total):
- Para 1: Open with a direct observation about their online reputation. State the rating, then say what it signals to a prospective renter before they ever call. 2–3 sentences. Don't start with "With a" or "You're managing".
- Para 2: Start with "At {company}," and describe one concrete moment where this breaks down — a maintenance request that goes unacknowledged for days, a resident who posts a frustrated review before anyone responds. Then one clean sentence: what EliseAI does to fix it (instant ticket acknowledgment, 24/7 automated tenant updates).
- Para 3: One sentence only, 10 words or fewer. A short, curious question. "Worth a 15-minute call?" is a fine template. No fear framing.""",

    "operational_friction": """\
STORY ARC — Operational Friction:
The climate in {city} creates a constant maintenance load — your team is reactive by default, not by choice. EliseAI handles the tenant communication so the team can focus on the actual work.

WRITE THREE SHORT PARAGRAPHS (~150–200 words total):
- Para 1: Open with the conditions reality (from the perspective of property managers) — snowfall, precipitation days, or temperature range. One specific number from the data. What it means for the maintenance team day-to-day. 2–3 sentences. Don't start with "With a" or "You're managing".
- Para 2: Start with "At {company}," and describe one concrete moment for example where this goes wrong — a burst pipe during a cold snap, a flooded lobby, residents calling repeatedly because they haven't heard back on a work order. One clean sentence example: EliseAI keeps residents informed automatically so the team can focus on the fix, not the calls.
- Para 3: One sentence only, 10 words or fewer. A short, curious question. "Worth a 15-minute call?" is a fine template. No fear framing.""",

    "growth_strain": """\
STORY ARC — Growth Strain:
{company} is expanding — but every new property means more leasing calls, maintenance requests, and tenant messages landing on the same team. Headcount doesn't scale as fast as a portfolio does.

WRITE THREE SHORT PARAGRAPHS (~150–200 words total):
- Para 1: Open with the growth signal — reference a headline or the expansion context — and connect it immediately to what that means for the team absorbing the new volume. 2–3 sentences. Don't start with "With a" or "You're managing".
- Para 2: Start with "At {company}," and describe one concrete moment where growth creates friction — a leasing coordinator fielding 40 inquiries for a new property, a maintenance queue that doubled after adding a building. One clean sentence: EliseAI handles the volume without adding headcount.
- Para 3: One sentence only, 10 words or fewer. A short, curious question. "Worth a 15-minute call?" is a fine template. No fear framing.""",

    "premium_expectations": """\
STORY ARC — Premium Expectations:
Renters in {city} have options — high walkability, high incomes, high expectations. In a premium market, slow service doesn't just frustrate residents; it loses leases and renewals.

WRITE THREE SHORT PARAGRAPHS (~150–200 words total):
- Para 1: Open with the neighborhood reality — walkability, income bracket, what kind of renter shops here. One or two specific data points. What that means for how responsive the team needs to be. 2–3 sentences. Don't start with "With a" or "You're managing".
- Para 2: Start with "At {company}," and describe one concrete moment where expectations aren't met — a tour request that sits unanswered for a day, a maintenance ticket that goes quiet, a renewal reminder that never arrives. One clean sentence: EliseAI provides instant response for leasing, maintenance, and renewals, 24/7.
- Para 3: One sentence only, 10 words or fewer. A short, curious question. "Worth a 15-minute call?" is a fine template. No fear framing.""",

    "lead_speed": """\
STORY ARC — Lead Speed:
In {city}, prospects are shopping multiple properties at once. The first team to respond wins the lease — and the teams that respond hours later don't.

WRITE THREE SHORT PARAGRAPHS (~150–200 words total):
- Para 1: Open with the market reality — vacancy rate, renter concentration, how fast prospects move. Ground it in one specific number from the data. 2–3 sentences. Don't start with "With a" or "You're managing".
- Para 2: Start with "At {company}," and describe ONE concrete moment where response speed costs a lease. Pick whichever fits best for this lead — don't use all of them:
  · A prospect who submits at 9pm and doesn't hear back until the next morning
  · A unit that sits vacant two extra weeks because the first follow-up was late
  · A tour request sent over email that gets buried under 30 others in the queue
  · A renter who called twice and left voicemails that were never returned
  Then one clean sentence: EliseAI responds instantly, 24/7, so no lead goes cold.
- Para 3: One sentence only, 10 words or fewer. A short, curious question. "Worth a 15-minute call?" is a fine template. No fear framing.""",
}


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

async def generate_outreach(
    lead_info: Dict[str, Any],
    enrichment: Dict[str, Any],
    pain_points: List[Dict[str, Any]],
    scores: Optional[Dict[str, Any]] = None,
    provider: str = "anthropic",
) -> Dict[str, Any]:
    from .llm import chat_complete

    scores = scores or {}
    recipient_first = (lead_info.get("name") or "").split()[0] or "there"

    arc = _select_arc(scores, pain_points)
    ctx = _arc_context(arc, enrichment, scores)

    story = _ARC_STORY[arc].format(
        company=lead_info.get("company") or "your company",
        city=lead_info.get("city") or "your city",
    )

    prompt = f"""Respond ONLY as JSON: {{"subject": "...", "message": "..."}}

You're an SDR at EliseAI writing a cold email to {lead_info.get('name')} at {lead_info.get('company')} ({lead_info.get('city')}, {lead_info.get('state')}).

EliseAI automates property management — leasing conversations, tour scheduling, maintenance coordination, and 24/7 tenant communication across SMS, email, and chat.

FACTS ABOUT THEIR SITUATION:
{ctx or "No specific data available."}

{story}

WRITING RULES (follow exactly):
- Write in second person throughout: "your team", "you're", "your building" — never refer to the recipient in third person.
- Use only facts stated above — never invent numbers, percentages, or counts not present in the data.
- Write in US units: snowfall in feet, temperature in °F.
- Round numbers naturally: "around 5%" not "4.8%", "3 feet of snow" not "3.0 feet", "~150 rainy days" not "148 days".
- No filler or buzzwords: never write "streamline", "leverage", "seamlessly", "AI-powered solutions", "our platform", "our solutions", "explore", "I'd love to", "as a [role]", "let's schedule", "moving forward", "at scale". Make every word count and write like a human.
- Plain language: "rainy days" not "precipitation", "units sitting empty" not "vacancy rate", "3 feet of snow" not "90 cm of snowfall".
- Confident and direct: avoid "probably", "likely", "may", "might" — hedging sounds weak.
- If a sentence sounds like it came from a brochure, cut it.

No greeting or sign-off (added separately). Start directly with the first sentence.
Subject line: under 8 words. No mention of EliseAI. Write it from the reader's head — the thing they're already quietly worried about, something that can hook them. Not a product description, not a benefit. A tension. Bad examples: "Faster Leasing", "Lease Now", "Missed Opportunities". Good examples: "When the phone rings at midnight", "Units sitting empty this week", "The inquiry you didn't see".
Separate the 3 paragraphs with \\n\\n in the message string."""

    try:
        text = await chat_complete(prompt, provider=provider, max_tokens=600, fast=False)
        import json, re
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if match:
            raw = re.sub(
                r'"(?:[^"\\]|\\.)*"',
                lambda m: m.group(0).replace('\n', '\\n').replace('\r', '\\r').replace('\t', '\\t'),
                match.group(),
            )
            result = json.loads(raw)
            return {
                "subject":      result.get("subject", ""),
                "greeting":     f"Hi {recipient_first},",
                "message":      result.get("message", ""),
                "arc":          arc,
                "generated_at": datetime.utcnow().isoformat() + "Z",
                "provider":     provider,
            }
    except Exception as e:
        print(f"Outreach generation error ({provider}): {e}")
        return {"error": str(e), "subject": "", "message": "", "arc": arc, "provider": provider}

    return {"error": "Failed to parse LLM response", "subject": "", "message": "", "arc": arc, "provider": provider}
