# GTM Automation Tool

> Turns a property address into a scored lead, named pain points, and a personalized cold email — in under 60 seconds.

---

An SDR prospecting a property management company spends 25–45 minutes per lead on research that should be automated: what's the local rental market like, how large is this property, is the company growing or struggling, and what do residents actually think of them? This tool replaces that lookup work entirely. Given a name, company, and property address, it runs a two-phase enrichment pipeline. Phase 1 fires 9 APIs in parallel — US Census, FRED vacancy rates, WalkScore, FBI crime data, Open-Meteo climate, OpenStreetMap building geometry, Intellipins parcel data, Wikipedia, and NewsAPI. Phase 2 uses the building type derived from OSM and Intellipins to call Google Places with the right search strategy: apartment complexes get searched by address (finding tenant reviews of that specific property), while commercial or non-residential properties get searched by company name near the property (finding the leasing company's own Google rating — not the tenant business's reviews). The pipeline then scores leads across four dimensions — **Demand** (rental market pressure, 30%), **Opportunity** (growth signals and urgency triggers, 35%), **Scale** (property footprint, 20%), and **Friction** (operational difficulty, 15%) — and the composite 0–100 Lead Score with A–F grade tells an SDR in one number whether to prioritize, sequence, or skip a lead. Opportunity and Demand carry the most weight because they predict whether a company will buy; Friction is a supporting signal that sharpens the email angle.

The scoring engine is fully deterministic — no LLM decides what a property scores. The engine uses a **High-Dynamic-Range Calibration Strategy** designed to maximize lead differentiation. Three principles govern how signals are shaped: (1) **Ceiling Calibration** — ceilings are set at realistic "strong" values rather than theoretical maximums (e.g., walk score ceiling is 80 so that "Very Walkable" properties max out the component, not penalized against a 100-point ceiling that no real lead ever hits); (2) **Concave Lifting** (_lift, power 0.70) applied to "indicator" signals (renter share, vacancy, snowfall, low Google rating, vacancy urgency) — moderate values already represent meaningful intent, so they deserve a boost, not a penalty; (3) **Aggressive Convex Penalization** (_crush, power 2.0) applied to "structural" filters (walkability, population, building footprint) — these are pass/fail signals where weak values should score near zero. This combination ensures weak leads consistently fall below 50 while elite leads reach 80–90. Signals are composed using a partial-weight formula that excludes missing data rather than imputing it, so every score ships with an `available_weight` field. A rule engine then fires pain points from score thresholds and raw enrichment values. Only after deterministic rules run does an LLM (Claude Haiku by default, or Groq's llama-3.1-8b as a free-tier alternative) add up to two additional nuanced insights grounded in the specific numbers. A second LLM call (Claude Sonnet, or llama-3.3-70b on Groq) then generates a cold email in one of five story arcs selected deterministically from scores and pain points.

The FastAPI backend is organized as a five-step sequential pipeline (`enrich → score → pain_points → outreach → save`) with a Vite vanilla-JS frontend for one-at-a-time lead runs, and a REST API that accepts batch POST requests for programmatic use. All APIs degrade gracefully: missing keys return structured error dicts, network failures are caught per-task in `asyncio.gather`, and geocoding has a four-level fallback chain (Intellipins → Nominatim structured → Nominatim freeform → US Census geocoder). The tool is production-ready in the sense that it never crashes on bad data — it tells you what it couldn't retrieve and scores on what it has.

For batch runs, a 5–7 second random inter-lead pause keeps Nominatim and Overpass within rate limits and prevents burst detection. At typical pipeline speeds (10–15 seconds per lead), that yields 3–6 leads per minute — enough to score 1,000 leads in a single 4-hour run. The recommended workflow: score 1,000 leads overnight, pick the top 60 by Lead Score, then send emails across a 9am–3pm window at 10/hour with random spacing. The outreach pacing mimics a human SDR and avoids spam-filter triggers.

---

## Quick Start

```bash
cp .env.example .env          # fill in your API keys
pip install -r requirements.txt
uvicorn backend.main:app --reload
# then open frontend/index.html in your browser
```

The backend runs at `http://localhost:8000`. Full pipeline: `POST /pipeline`. Raw enrichment only: `POST /enrich`. Saved leads: `GET /leads`. Re-score saved lead without re-enriching: `POST /dev/rescore/{lead_id}` (body: `{"steps": "scoring,pain_points,outreach", "llm_provider": "anthropic"}`).

---

## Documentation

| Doc | Audience | What's inside |
|-----|----------|---------------|
| [Business Overview](docs/01_business_overview.md) | CEO, Sales Leadership | Problem statement, scoring logic with all assumptions, example lead profiles, limitations, future roadmap |
| [Pipeline & Architecture](docs/02_pipeline_architecture.md) | Engineering, RevOps | System diagram, API inventory, data flow trace, full scoring rubric, batch processing strategy, outreach scheduling, A/B testing framework |
| [User Guide](docs/03_user_guide.md) | SDRs, SDR Managers | Step-by-step setup, input format, reading the output, FAQ and troubleshooting |
| [Rollout & Project Plan](docs/04_rollout_plan.md) | Revenue Leadership | 4-phase rollout (validate → semi-auto → full team → automated), A/B testing program, success metrics, cost breakdown |

An interactive visual version of all three docs is available at `frontend/docs.html` — open it in a browser for animated pipeline diagrams, scoring pie charts, and hover-detail API cards.

---

## Real Examples

Two actual pipeline runs from the test dataset, showing what the tool outputs end-to-end.

### Grade A — 84/100 · Christopher Gonzalez · Inland American Real Estate · Chicago, IL

**Property:** 40 E Oak St — 20-floor apartment complex, Gold Coast neighborhood
**Key signals:** Walk Score 99 (Walker's Paradise) · Transit Score 92 · 54.4% renter share · City pop. 2.74M · 62.7 cm snow/yr · 178 rain days · -24°C winter lows · 5.7% vacancy

| Sub-score | Score | What's driving it |
|-----------|-------|-------------------|
| Demand | 89/100 | Near-perfect walkability, transit, and renter density in the third-largest US city |
| Friction | 90/100 | Heavy Chicago winters (snowfall, 60°C temp swing, 178 precip days) = constant maintenance load |
| Scale | 100/100 | Apartment Complex · 20 floors · 102,536 sq ft parcel |
| Opportunity | 64/100 | No news signal, but tight market with vacancy urgency and strong walkability |

**Pain points identified:** Core ICP multifamily property · High lead volume overload (99 Walk Score drives constant inquiry) · Harsh operating conditions (2 ft snow/yr) · High tenant mobility (Transit 92 in renter-majority market)

**Generated email** *(arc: operational\_friction)*
> **Subject:** Midnight Maintenance Calls
>
> Your team deals with around 2 feet of snow and ~178 rainy days per year, which means constant maintenance issues. This creates a reactive environment where your team is always on call to fix something. Your building's temperature can drop to -12°F, putting a strain on your maintenance team.
>
> At Inland American Real Estate, a burst pipe during a cold snap can lead to a flooded lobby and numerous resident calls, taking your team away from the actual fix. EliseAI keeps residents informed automatically so your team can focus on the fix, not the calls.
>
> Worth a call?

---

### Grade D — 49.9/100 · Tyler Morales · Scottsdale Property Group · Scottsdale, AZ

**Property:** 6839 E Montecito Ave — Single-family house, 3,686 sq ft
**Key signals:** Walk Score 69 (Somewhat Walkable) · Transit Score 46 · 33.4% renter share · City pop. 238k · 0.3 cm snow/yr · 49 rain days · Google 4.8★ (100 reviews)

| Sub-score | Score | What's driving it |
|-----------|-------|-------------------|
| Demand | 69/100 | Decent walkability and income, but below-50% renter share and thin transit drag it down |
| Friction | 39/100 | Scottsdale is easy to operate — sunny climate, minimal snow, low maintenance load |
| Scale | 35/100 | Single-family house (type score 0.20) and tiny 3,686 sq ft footprint |
| Opportunity | 48/100 | 8.4% vacancy is the only hook — no news, no rating pain (4.8★ means happy residents) |

**Why it scores low:** The building type alone disqualifies this from EliseAI's ICP. A single-family house has no meaningful leasing volume to automate. And a 4.8-star Google rating with 100 reviews means this operator is handling service well without automation — there's no pain to sell into.

**Generated email** *(arc: lead\_speed)*
> **Subject:** Units sitting empty this week
>
> Your vacancy rate is around 8%. In Scottsdale, renters make quick decisions, often shopping multiple properties at once. Prospects are 33.4% of the population, and they're moving fast.
>
> At Scottsdale Property Group, a prospect who submits at 9pm and doesn't hear back until the next morning often signs a lease somewhere else. EliseAI responds instantly, 24/7, so no lead goes cold.
>
> Worth a call?
