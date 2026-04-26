# GTM Automation Tool

> Turns a property address into a scored lead, named pain points, and a personalized cold email — in under 60 seconds.

---

An SDR prospecting a property management company spends 25–45 minutes per lead on research that should be automated: what's the local rental market like, how large is this property, is the company growing or struggling, and what do residents actually think of them? This tool replaces that lookup work entirely. Given a name, company, and property address, it fires 10 enrichment APIs in parallel — US Census, FRED vacancy rates, WalkScore, FBI crime data, Open-Meteo climate, OpenStreetMap building geometry, Intellipins parcel data, Google Places reviews, Wikipedia, and NewsAPI — then scores the lead across four dimensions: **Demand** (rental market pressure), **Friction** (operational difficulty that drives automation value), **Scale** (property footprint), and **Opportunity** (growth signals and urgency triggers). The composite 0–100 Lead Score with A–F grade tells an SDR in one number whether to prioritize, sequence, or skip a lead.

The scoring engine is fully deterministic — no LLM decides what a property scores. Signals are normalized, weighted, and composed using a partial-weight formula that excludes missing data rather than imputing it, so every score ships with an `available_weight` field that tells you exactly how much data it was built on. A rule engine then fires pain points from score thresholds and raw enrichment values (e.g., a 2.8-star Google rating fires `resident_experience`; a sub-5% vacancy with 48%+ renter share fires `tight_market`). Only after deterministic rules run does an LLM (Claude Haiku) add up to two additional nuanced insights grounded in the specific numbers. A second LLM call (Claude Sonnet) then generates a cold email that references real data — Walk Score, vacancy rate, recent news — not generic templates. Every lead is persisted to JSON with a full component breakdown of every sub-score.

The FastAPI backend is organized as a five-step sequential pipeline (`enrich → score → pain_points → outreach → save`) with a Vite vanilla-JS frontend for one-at-a-time lead runs, and a REST API that accepts batch POST requests for programmatic use. All APIs degrade gracefully: missing keys return structured error dicts, network failures are caught per-task in `asyncio.gather`, and geocoding has a four-level fallback chain (Intellipins → Nominatim structured → Nominatim freeform → US Census geocoder). The tool is production-ready in the sense that it never crashes on bad data — it tells you what it couldn't retrieve and scores on what it has.

---

## Quick Start

```bash
cp .env.example .env          # fill in your API keys
pip install -r requirements.txt
uvicorn backend.main:app --reload
# then open frontend/index.html in your browser
```

The backend runs at `http://localhost:8000`. Full pipeline: `POST /pipeline`. Raw enrichment only: `POST /enrich`. Saved leads: `GET /leads`.

---

## Documentation

| Doc | Audience | What's inside |
|-----|----------|---------------|
| [Business Overview](docs/01_business_overview.md) | CEO, Sales Leadership | Problem statement, scoring logic with all assumptions, example lead profiles, limitations, future roadmap |
| [Pipeline & Architecture](docs/02_pipeline_architecture.md) | Engineering, RevOps | System diagram, API inventory, data flow trace, full scoring rubric, error handling, rate limit management |
| [User Guide](docs/03_user_guide.md) | SDRs, SDR Managers | Step-by-step setup, input format, reading the output, FAQ and troubleshooting |
| [Rollout & Project Plan](docs/04_rollout_plan.md) | Revenue Leadership | MVP test plan, pilot structure, 16-week timeline, success metrics, cost analysis at scale |
