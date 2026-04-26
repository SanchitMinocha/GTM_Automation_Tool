"""
Full GTM pipeline: enrich → score → infer pain points → generate outreach → save.
"""
from __future__ import annotations
from typing import Any, Dict

from .enrichment  import enrich_lead
from .scoring     import compute_all_scores
from .pain_points import infer_pain_points
from .outreach    import generate_outreach
from .storage     import save_lead


async def run_pipeline(lead: Any) -> Dict[str, Any]:
    """
    Runs the full pipeline for a lead.
    Uses lead.id (if provided) as the storage key so test-data runs are idempotent.
    Uses lead.llm_provider to select Anthropic or Groq for LLM steps.
    """
    provider = (getattr(lead, "llm_provider", None) or "anthropic").lower()
    lead_id  = getattr(lead, "id", None) or None  # None → generate UUID in storage

    enrichment_result = await enrich_lead(lead)
    lead_info  = enrichment_result["lead_info"]
    enrichment = enrichment_result["enrichment"]

    scores      = compute_all_scores(enrichment)
    pain_points = await infer_pain_points(lead_info, enrichment, scores, provider=provider)
    outreach    = await generate_outreach(lead_info, enrichment, scores, pain_points, provider=provider)
    saved_id    = save_lead(lead_info, enrichment, scores, pain_points, outreach, lead_id=lead_id)

    return {
        "id":          saved_id,
        "lead_info":   lead_info,
        "enrichment":  enrichment,
        "scores":      scores,
        "pain_points": pain_points,
        "outreach":    outreach,
    }
