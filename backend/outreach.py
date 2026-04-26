"""
LLM-powered personalized outreach email generation.
Uses pain points, scores, and enrichment context to craft a targeted email from EliseAI.
quality model (Sonnet / llama-3.3-70b) — language quality matters here.
"""
from __future__ import annotations
from datetime import datetime
from typing import Any, Dict, List


async def generate_outreach(
    lead_info: Dict[str, Any],
    enrichment: Dict[str, Any],
    scores: Dict[str, Any],
    pain_points: List[Dict[str, Any]],
    provider: str = "anthropic",
) -> Dict[str, Any]:
    from .llm import chat_complete

    census = enrichment.get("census") or {}
    fred   = enrichment.get("fred") or {}
    ws     = enrichment.get("walkscore") or {}
    wiki   = enrichment.get("wikipedia") or {}
    news   = enrichment.get("news") or {}
    google = enrichment.get("google") or {}
    ipins  = enrichment.get("intellipins") or {}

    wiki_extract = ((wiki.get("company") or {}).get("extract") or "")[:300]
    news_items = news.get("latest_news") or []
    news_context = ""
    if isinstance(news_items, list) and news_items:
        news_context = "; ".join(a.get("title", "") for a in news_items[:2])

    _sev = {"high": 0, "medium": 1, "low": 2}
    sorted_pain = sorted(pain_points, key=lambda x: _sev.get(x.get("severity", "low"), 2))
    pain_context = "\n".join(
        f"- [{pp['severity'].upper()}] {pp['label']}: {pp['description']}"
        for pp in sorted_pain[:5]
    )

    def _v(val):
        return val if val is not None else "N/A"

    ls = scores.get("lead_score", {})
    prompt = f"""Write a cold outreach email FROM EliseAI TO {lead_info.get('name')} at {lead_info.get('company')}.

EliseAI automates property management: leasing conversations, maintenance coordination, and tenant communication — 24/7 across SMS, email, and chat.

Lead context:
- Company: {lead_info.get('company')} | Location: {lead_info.get('city')}, {lead_info.get('state')}
- Property type: {_v(ipins.get('building_type'))}
- Lead Score: {_v(ls.get('score'))}/100 (Grade {_v(ls.get('grade'))})
- Median income: {_v(census.get('median_income'))} | Renter %: {_v(census.get('renter_percentage'))}
- Vacancy rate: {_v(fred.get('vacancy_rate'))} | Walk Score: {_v(ws.get('walk_score'))}
- Google rating: {_v(google.get('rating'))} ({google.get('review_count') or 0} reviews)
{f"- Company background: {wiki_extract}" if wiki_extract else ""}
{f"- Recent news: {news_context}" if news_context else ""}

Pain points (highest priority first):
{pain_context or "No specific pain points identified."}

Rules:
1. Subject line: specific to this company/location — never generic
2. Opening: reference something real (city, company, news, building type) — NOT "I noticed your company"
3. Body: weave in 2–3 specific pain points with real numbers from the data above
4. Length: 150–220 words for the body only
5. Tone: confident, direct, peer-to-peer — not salesy
6. CTA: one clear ask (15-min call or demo link)
7. Sign off as: Alex Chen, Account Executive, EliseAI

Respond ONLY as JSON: {{"subject": "...", "message": "..."}}"""

    try:
        text = await chat_complete(prompt, provider=provider, max_tokens=900, fast=False)
        import json, re
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if match:
            result = json.loads(match.group())
            return {
                "subject":      result.get("subject", ""),
                "message":      result.get("message", ""),
                "generated_at": datetime.utcnow().isoformat() + "Z",
                "provider":     provider,
            }
    except Exception as e:
        print(f"Outreach generation error ({provider}): {e}")
        return {"error": str(e), "subject": "", "message": "", "provider": provider}

    return {"error": "Failed to parse LLM response", "subject": "", "message": "", "provider": provider}
