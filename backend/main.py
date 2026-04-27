from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List
import os
from dotenv import load_dotenv

from .enrichment  import enrich_lead
from .pipeline    import run_pipeline
from .scoring     import compute_all_scores
from .pain_points import infer_pain_points
from .outreach    import generate_outreach
from .storage     import get_lead, list_leads, save_lead

load_dotenv()

app = FastAPI(title="EliseAI GTM Enrichment API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class LeadInbound(BaseModel):
    id: Optional[str] = None                      # test-data id → used as storage key
    name: str
    email: str
    company: str
    property_address: str
    city: str
    state: str
    enabled_apis: Optional[List[str]] = None
    llm_provider: Optional[str] = "anthropic"     # "anthropic" | "groq" | "gemini"


@app.get("/")
async def root():
    return {"message": "EliseAI GTM Automation Backend is running"}


@app.post("/enrich")
async def enrich_lead_endpoint(lead: LeadInbound):
    """Raw enrichment only — no scoring or outreach."""
    try:
        return await enrich_lead(lead)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/pipeline")
async def pipeline_endpoint(lead: LeadInbound):
    """Full GTM pipeline: enrich → score → pain points → outreach → save."""
    try:
        return await run_pipeline(lead)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/leads")
async def list_leads_endpoint():
    """List all saved leads (lightweight index)."""
    return list_leads()


@app.get("/leads/{lead_id}")
async def get_lead_endpoint(lead_id: str):
    """Retrieve the full record for a saved lead."""
    record = get_lead(lead_id)
    if not record:
        raise HTTPException(status_code=404, detail="Lead not found")
    return record


class DevRescoreRequest(BaseModel):
    steps: Optional[str] = "scoring"          # "scoring" | "scoring,pain_points" | "scoring,pain_points,outreach"
    llm_provider: Optional[str] = "anthropic"


@app.post("/dev/rescore/{lead_id}")
async def dev_rescore(lead_id: str, req: DevRescoreRequest = None):
    """Dev tool: re-run scoring (and optionally pain points / outreach) on saved enrichment data."""
    if req is None:
        req = DevRescoreRequest()
    record = get_lead(lead_id)
    if not record:
        raise HTTPException(status_code=404, detail="Lead not found")

    enrichment  = record["enrichment"]
    lead_info   = record["lead_info"]
    step_set    = {s.strip() for s in (req.steps or "scoring").split(",")}
    provider    = (req.llm_provider or "anthropic").lower()

    scores      = compute_all_scores(enrichment)
    pain_points = record.get("pain_points", [])
    outreach    = record.get("outreach", {})

    if "pain_points" in step_set or "outreach" in step_set:
        pain_points = await infer_pain_points(lead_info, enrichment, scores, provider=provider)

    if "outreach" in step_set:
        outreach = await generate_outreach(lead_info, enrichment, pain_points, scores=scores, provider=provider)

    save_lead(lead_info, enrichment, scores, pain_points, outreach, lead_id=lead_id)

    return {
        "id":          lead_id,
        "lead_info":   lead_info,
        "enrichment":  enrichment,
        "scores":      scores,
        "pain_points": pain_points,
        "outreach":    outreach,
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
