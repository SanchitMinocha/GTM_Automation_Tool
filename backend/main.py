from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List
import os
from dotenv import load_dotenv

from .enrichment import enrich_lead
from .pipeline   import run_pipeline
from .storage    import get_lead, list_leads

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
    llm_provider: Optional[str] = "anthropic"     # "anthropic" | "groq"


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


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
