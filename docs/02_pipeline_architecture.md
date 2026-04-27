# EliseAI GTM Automation Tool — Pipeline & Architecture

> **Audience:** Engineering, RevOps, anyone who inherits or extends this system.

---

## How It Works — The Short Version

A lead comes in as a name + address. The system geocodes it, fires 9 API calls in parallel, derives building type from those results, then calls Google Places with the right search strategy for that property type. It then scores everything deterministically, runs a rule-based pain point engine (then adds ≤2 LLM-generated insights), and generates the outreach email. The whole thing takes 20–60 seconds and saves a full JSON record.

Here's the full picture:

```
┌─────────────────────────────────────────────────────────────────────┐
│  INPUT                                                              │
│  Lead record: name, email, company, property_address, city, state   │
└──────────────────────────────┬──────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────────┐
│  GEOCODING  (enrichment.py → _geocode_address)                      │
│                                                                     │
│  1. Intellipins /geocode/forward  ─── success → lat/lon + ipins_id  │
│  2. Nominatim structured search   ─── fallback if Intellipins fails │
│  3. Nominatim freeform search     ─── fallback if structured fails  │
│  4. US Census Geocoder            ─── final fallback                │
│                                                                     │
│  Output: lat, lon, geocode_source                                   │
└──────────────────────────────┬──────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────────┐
│  PHASE 1 ENRICHMENT  (enrichment.py → enrich_lead)                  │
│  9 API calls run concurrently via asyncio.gather()                  │
│                                                                     │
│  ┌─────────────────┐  ┌────────────────┐  ┌──────────────────────┐  │
│  │ Census (city)   │  │ FRED (state)   │  │ Wikipedia (company)  │  │
│  └─────────────────┘  └────────────────┘  └──────────────────────┘  │
│  ┌─────────────────┐  ┌────────────────┐  ┌──────────────────────┐  │
│  │ NewsAPI (co.)   │  │ WalkScore (*)  │  │ Intellipins parcel(*)│  │
│  └─────────────────┘  └────────────────┘  └──────────────────────┘  │
│  ┌─────────────────┐  ┌────────────────┐  ┌──────────────────────┐  │
│  │ OSM/Overpass(*) │  │ Open-Meteo (*) │  │ FBI CDE (city)       │  │
│  └─────────────────┘  └────────────────┘  └──────────────────────┘  │
│                                                                     │
│  (*) requires lat/lon from geocoding step                           │
│  Output: enrichment dict with 9 API results                         │
└──────────────────────────────┬──────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────────┐
│  BUILDING TYPE CLASSIFICATION  (_classify_building_type)            │
│                                                                     │
│  Derived from OSM tags + Intellipins address_type (phase 1 output)  │
│  Result: "Apartment Complex" | "Commercial / Industrial" | etc.     │
└──────────────────────────────┬──────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────────┐
│  PHASE 2 ENRICHMENT  (get_google_places_data)                       │
│                                                                     │
│  Search strategy depends on building type:                          │
│  • Apartment Complex → search by address (finds the complex's own   │
│    Google listing — tenant reviews, star rating for that property)  │
│  • All other types  → search by company name + location bias near   │
│    the property (finds the leasing company's nearest office;        │
│    Walmart reviews on a retail property are irrelevant)             │
│                                                                     │
│  No latency penalty: Google (~1–2 s) finishes well before OSM       │
│  would have anyway — total pipeline time is unchanged.              │
└──────────────────────────────┬──────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────────┐
│  SCORING ENGINE  (scoring.py → compute_all_scores)                  │
│                                                                     │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐    │
│  │   Demand    │ │  Friction   │ │    Scale    │ │ Opportunity │    │
│  │  (0–100)    │ │  (0–100)    │ │  (0–100)    │ │  (0–100)    │    │
│  └──────┬──────┘ └──────┬──────┘ └──────┬──────┘ └──────┬──────┘    │
│         └───────────────┴───────┬───────┴───────────────┘           │
│                                 │                                   │
│         ┌───────────────────────▼───────────────────────┐           │
│         │         Lead Score (0–100, grade A–F)         │           │
│         └───────────────────────────────────────────────┘           │
│                                                                     │
│  Each score: partial-weight formula — missing signals excluded,     │
│  available_weight logged for transparency                           │
└──────────────────────────────┬──────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────────┐
│  PAIN POINT INFERENCE  (pain_points.py → infer_pain_points)         │
│                                                                     │
│  Step 1: Deterministic rule engine fires on score thresholds        │
│          + raw enrichment values → generates tagged pain points     │
│                                                                     │
│  Step 2: LLM enrichment (Claude Haiku or Groq llama-3.1-8b)         │
│          Receives rules output → adds ≤2 additional nuanced points  │
│          grounded in specific data values                           │
│                                                                     │
│  Output: [{tag, label, severity, description, source}]              │
└──────────────────────────────┬──────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────────┐
│  OUTREACH GENERATION  (outreach.py → generate_outreach)             │
│                                                                     │
│  Claude Sonnet or Groq llama-3.3-70b (fast=False, max_tokens=900)  │
│  Prompt includes: lead context, pain points, scores,                │
│  news, wiki extract, Google rating, building type                   │
│                                                                     │
│  Output: {subject, message, generated_at, provider}                 │
└──────────────────────────────┬──────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────────┐
│  PERSISTENCE  (storage.py → save_lead)                              │
│                                                                     │
│  data/leads/{uuid}.json  — full record                              │
│  data/index.json         — lightweight index (id, name, co, score)  │
└──────────────────────────────┬──────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────────┐
│  API RESPONSE                                                       │
│  POST /pipeline      → full record returned to frontend             │
│  POST /dev/rescore/{id} → re-run scoring (+ optionally pain points  │
│       and outreach) on saved enrichment; body: {steps, llm_provider}│
└─────────────────────────────────────────────────────────────────────┘
```

---

## API Inventory

These are the 13 external services the pipeline calls, what each contributes, and what it costs to run them.

| API | What it provides | Free tier | Rate limit | Auth |
|-----|-----------------|-----------|------------|------|
| **US Census Bureau ACS 5-Year** | Population, median income, renter % by city | Free, no quota enforced | ~500 req/day recommended | Optional API key |
| **FRED (St. Louis Fed)** | State-level rental vacancy rate | Free | 1,000 req/day | API key required |
| **WalkScore API** | Walk, transit, bike scores for address | 5,000 req/day free; $0.0025/req above | 5,000/day | API key required |
| **Intellipins** | Geocoding, parcel data, building type, elevation | No free tier | ~1 req/sec | API key (`X-API-KEY` header) |
| **Nominatim (OSM)** | Geocoding fallback, building footprint | Free (public instance) | **1 req/sec max — hard limit** | No key; User-Agent header required |
| **Overpass API (OSM)** | Building geometry, nearby amenity counts | Free (public instance) | Soft-throttled; ~3 sec between queries | No key; User-Agent header required |
| **Open-Meteo Archive** | Historical climate for 2024 (precip, snow, temp) | Free; 10,000 req/day | 10,000/day | No key required |
| **FBI Crime Data Explorer** | City-level crime rates per 100k | Free | No documented limit | API key required |
| **NewsAPI** | Company news and press releases | 100 req/day free; 1,000/day developer plan | 100/day free tier | API key required |
| **Wikipedia REST API** | Company/city summary text | Free | Practically unlimited | No key; User-Agent header required |
| **Google Places API** | Apartment: complex tenant reviews (search by address). Other: leasing company's nearest office rating (search by company name + location bias) | $200/month free credit (~11,700 text searches) | Default 10 QPS | API key required |
| **Anthropic (Claude Haiku)** | Pain point LLM enrichment | None (pay-per-use) | 50 req/min on Tier 1 | API key required |
| **Anthropic (Claude Sonnet)** | Outreach email generation | None (pay-per-use) | 50 req/min on Tier 1 | Same key as Haiku |
| **Groq API** *(alternative)* | Both LLM steps using open-source models | Generous free tier | 30 req/min free tier | API key; set `llm_provider=groq` |

**What happens when a key is missing:** Every API call starts with a check for a valid key. If a key is missing or still set to a placeholder, that API returns a structured error and the pipeline continues — that signal is simply excluded from scoring rather than crashing the whole run.

---

## What Actually Happens for a Single Lead

Here's a full trace from request to saved file. This is the most useful thing to read if you're debugging or extending the pipeline.

### The request arrives at POST /pipeline

```json
{
  "name": "Jordan Lee",
  "email": "jlee@greystar.com",
  "company": "Greystar",
  "property_address": "1600 Vine St",
  "city": "Los Angeles",
  "state": "CA",
  "enabled_apis": null,
  "llm_provider": "anthropic"
}
```

`enabled_apis: null` runs everything. You can pass a list like `["census", "walkscore", "crime"]` to restrict which APIs run — useful for testing or debugging specific signals.

### Step 1: Geocoding (runs first — everything else depends on lat/lon)

`_geocode_address("1600 Vine St", "Los Angeles", "CA")` tries Intellipins first. On success, it returns `(lat, lon, "intellipins", ipins_data_dict)`. The Intellipins data dict is passed directly into the parcel lookup — the service is called only once, not twice.

If Intellipins is rate-limited or unavailable, the chain falls through to Nominatim structured, then Nominatim freeform, then US Census Geocoder. If all four fail, `lat` and `lon` are `None`, and the four coordinate-dependent APIs (WalkScore, OSM, Open-Meteo, Intellipins parcel) are skipped. The other five (Census, FRED, Wikipedia, News, FBI) still run in phase 1. Google Places still runs in phase 2 — for non-apartment properties it only needs city/state for the company search, and building type will default to `"Single Family Housing"` when OSM is skipped.

### Step 2: 9 API calls fire in parallel (Phase 1)

`asyncio.create_task()` is called for each API except Google, then `asyncio.gather()` awaits all of them. Google is intentionally excluded here because its search strategy depends on building type, which isn't known until OSM and Intellipins results come back.

### Step 3: Building type is derived, then Google runs (Phase 2)

After phase 1 completes, `_classify_building_type()` reads the OSM `osm_type`/`osm_class` tags and the Intellipins `address_type` field to classify the property. That result is passed directly into `get_google_places_data()`:

- **Apartment Complex** — searches `{address}, {city}, {state}`. This finds the apartment's own Google listing (e.g., "Rise Apartments at 829 NE 67th St") with tenant reviews and star ratings. The management company name is irrelevant here because the complex has its own branded listing.
- **Any other type** — searches `{company} {city} {state}` with a 50 km location bias centered on the property coordinates. This finds the leasing company's nearest office listing. Searching by address for a retail or commercial property would return irrelevant reviews (e.g., a Walmart's shopper reviews instead of the property manager's reputation).

There is no latency penalty for this sequencing: OSM makes 4–5 chained Overpass queries and takes 5–15 seconds. Google makes 1–2 requests and takes 1–2 seconds. Waiting for phase 1 to finish costs nothing in wall-clock time — Google would have finished long before OSM anyway.

### Step 4: Results are assembled into an enrichment dict

After both phases complete, results are keyed by API name. The pipeline then runs `_nullify()` on the whole dict — this recursively converts `"N/A"`, `""`, and `"Data unavailable"` strings to `null` before passing to the scorer.

### Step 5: Scoring runs (deterministic, no I/O)

`compute_all_scores(enrichment)` calls four independent sub-scorers. Each extracts numeric values from the enrichment dict, normalizes them to 0–1 using the formulas below, and runs a partial-weight average. Missing signals shrink the denominator — they don't penalize the score.

### Step 6: Pain points

`_rule_based_pain_points()` evaluates ~10 if-conditions against score values and enrichment data. Each fires independently. Then Claude Haiku (or Groq llama-3.1-8b) receives this initial list plus raw enrichment context and appends up to 2 additional insights grounded in specific numbers.

### Step 7: Email generation

`outreach.py` first selects a story arc deterministically from scores and pain point tags — one of five: `reputation_gap` (low Google rating), `operational_friction` (high friction + climate/crime data), `growth_strain` (growth news signal), `premium_expectations` (premium_market pain point), or `lead_speed` (default). The arc selection is pure logic — no LLM involved. It then builds an arc-specific context block containing only the facts relevant to that story (e.g., for `reputation_gap`: rating, review count, sample negative review text).

Claude Sonnet (or Groq llama-3.3-70b) receives the arc context, arc-specific narrative instructions, and writing rules (US units, no buzzwords, round numbers naturally). It returns JSON `{subject, message}`. The function adds a `greeting`, `arc`, `generated_at`, and `provider` field.

### Step 8: Save

`save_lead()` writes the full record to `data/leads/{uuid}.json` and appends a summary row to `data/index.json`.

---

## Scoring Rubric — Full Reference

These are the exact formulas used. If you're tuning weights or adding new signals, this is the spec.

### Demand Score (final weight: 30%)

| Signal | Weight | Normalization | Note |
|-----------|--------|---------------|------|
| renter_pct | 0.25 | `lift(min(renter_pct / 50.0, 1.0))` | City-level from Census ACS `for=place:*` |
| low_vacancy | 0.20 | `lift(max(0, 1.0 - vacancy / 10.0))` | |
| walk_score | 0.15 | `crush(min(walk / 80.0, 1.0))` | Ceiling 80 = "Very Walkable"; score ≥80 maxes out |
| transit_score | 0.10 | `crush(min(transit / 75.0, 1.0))` | Ceiling 75 = "Excellent Transit" |
| income | 0.10 | `lift(min(income / 85000, 1.0))` | |
| nearby_amenities | 0.12 | `lift(min(total_amenities / 40.0, 1.0))` | Sum of OSM transit + parks + retail within 1km |
| population | 0.08 | `crush(min(population / 250000, 1.0))` | City-level; any city ≥250k maxes out |

### Friction Score (final weight: 20%)

| Signal | Weight | Normalization | Note |
|-----------|--------|---------------|------|
| crime | 0.25 | `crush((crime_score - 1.0) / 14.0)` | Structural filter: low crime = near-zero friction |
| precip_days | 0.25 | `crush(min(precip_days / 120.0, 1.0))` | Structural: mild weather leads score near zero |
| snowfall | 0.20 | `lift(min(snowfall_cm / 80.0, 1.0))` | **Indicator** (not structural): any meaningful snow signals friction; moderate NYC snowfall (~38 cm) scores ~59 |
| temp_range | 0.20 | `crush(min(temp_range / 55.0, 1.0))` | hottest_day - coldest_day |
| elevation | 0.10 | `crush(min(elevation_m / 800.0, 1.0))` | |

### Scale Score (final weight: 20%)

| Signal | Weight | Normalization | Note |
|-----------|--------|---------------|------|
| building_type | 0.30 | Lookup table (SFH = 0.20) | |
| footprint | 0.25 | `crush(min(area_sqft / 40000, 1.0))` | **Skipped** for Apartment Complex / Apartment / Shopping Complex types when footprint < 10,000 sq ft — OSM returns the single-address polygon, not the complex footprint, for dense urban addresses |
| lot_area | 0.20 | `lift(min(area_sqft / 100000, 1.0))` | From Intellipins parcel data |
| floors | 0.15 | `crush(min(floors / 15.0, 1.0))` | |
| units | 0.10 | `crush(min(units / 250.0, 1.0))` | |

**Building type lookup:**

| Type | Score |
|------|-------|
| Apartment Complex | 1.00 |
| Hotel | 0.80 |
| Commercial / Industrial | 0.75 |
| Office Building | 0.70 |
| Apartment / Shopping Complex | 0.65 |
| Shopping Complex / Amenity | 0.55 |
| Retail / Shopping | 0.45 |
| Single Family Housing | 0.20 |
| Unknown | 0.20 |

**Building type classification (priority order):**
1. OSM type `apartments`, `residential`, or `dormitory` → Apartment Complex
2. OSM type `commercial`, `retail`, or `industrial` → Commercial / Industrial
3. OSM type `office` → Office Building
4. OSM type `hotel` → Hotel
5. OSM class `amenity` → Shopping Complex / Amenity
6. OSM class `shop` → Retail / Shopping
7. Intellipins `address_type` is `base` or `supplementary` → Apartment / Shopping Complex
8. Default → Single Family Housing

### Opportunity Score (final weight: 30%)

Captures behavioral and reputational signals only — renter %, vacancy, and walkability are excluded here to avoid double-counting with Demand.

| Signal | Weight | Normalization | Note |
|-----------|--------|---------------|------|
| news_signal | 0.54 | growth→0.95, cost_pressure→0.85, neutral→0.45, none→0.30 | Only included when `latest_news` is a list (real articles found) |
| low_rating | 0.31 | `lift(max(0, 1.0 - (rating - 1.0) / 3.5))` | Linear raw score then `_lift`; indicator signal — moderate bad reviews should score ~55, not ~43 |
| wiki_presence | 0.15 | `0.90` if found | |

**News sentiment keyword matching:**
- Growth: `expand, acquir, growth, new market, scale, portfolio, launch, partner, open, hire, invest`
- Cost pressure: `layoff, restructur, downsize, cost-cut, job cut, budget, deficit, closure, reduce staff`
- Trouble: `lawsuit, fine, penalty, complaint, eviction, fraud, investigation`

Logic: ≥2 growth hits → `growth`; ≥2 cost hits → `cost_pressure`; ≥2 trouble hits → `trouble`; ≥1 any → `mixed`; else `neutral`.

### Lead Score Composite

```python
weights = {"demand": 0.30, "friction": 0.20, "scale": 0.20, "opportunity": 0.30}
```

Each sub-score's contribution to the composite is scaled by its `available_weight` (the fraction of max signals that returned data). A sub-score with sparse data contributes proportionally less rather than receiving full weight or being dropped entirely. The denominator is the sum of scaled weights, so the result is always a valid 0–100 score.

### Engineering Defense: High-Dynamic-Range Scoring Strategy (V6)

To ensure clear prioritization and push weak leads below 50, we employ a three-part calibration strategy:

1.  **Ceiling Calibration**: Ceilings are set at realistic "strong" thresholds rather than theoretical maximums. Walk score ceiling = 80 ("Very Walkable"), transit ceiling = 75 ("Excellent Transit"). This prevents elite urban properties from being silently penalized by a ceiling no real lead ever hits.
2.  **Concave Lifting (_lift, power 0.70)**: Applied to indicator signals (renter%, vacancy, snowfall, low_rating, vacancy_urgency). These signals represent intent — moderate values already mean something, and they deserve a boost. `lift(0.5) = 0.5^0.7 = 0.615`.
3.  **Aggressive Convex Penalization (_crush, power 2.0)**: Applied to structural filters (walk score, population, footprint, floors, units). These are pass/fail signals where low values should score near zero. `crush(0.5) = 0.5^2 = 0.25`.
4.  **Decisive Opportunity Floors**: Qualitative triggers (news, wiki) use high floors (0.90+) so a single strong sales signal can push a lead into Grade A.

---

## When Things Go Wrong

The pipeline is designed to degrade gracefully — any single API failing should produce a slightly less informed score, not an error page.

| What fails | What happens |
|-----------|-------------|
| API key missing or placeholder | Returns `{"error": "Key required"}` for that source; pipeline continues |
| HTTP non-200 response | Returns `{}` or `{"error": "..."}` for that source; signal excluded from scoring |
| Network timeout | `httpx.AsyncClient` per-API timeouts (10–30s); exception caught by `asyncio.gather` |
| `asyncio.gather` exception | Exception object returned; pipeline checks `isinstance(result, Exception)` and falls back to `{}` |
| Geocoding fails completely | `lat=None, lon=None` — coordinate-dependent APIs (WalkScore, OSM, Open-Meteo, Intellipins) skipped; Census, FRED, Wikipedia, News, FBI, and Google Places still run |
| Intellipins rate limited (429) | Falls back to Nominatim; downstream parcel call returns `{"error": "Rate limited..."}` |
| LLM (Haiku) error | Returns rule-based pain points only; no LLM augmentation |
| LLM (Sonnet) error | Returns `{"error": ..., "subject": "", "message": ""}` — pipeline still saves the full record |
| FBI ORI not found for city | `{"error": "No ORI found for {city}, {state}"}` — crime excluded from friction score |
| OSM building not found | `building_details: {}` — footprint and floors excluded from scale score |
| No news results | Scored as `"none"` sentiment (0.30); pipeline continues normally |

---

## Geocoding Fallback Chain

```
Primary:   Intellipins /geocode/forward
              ↓ 429 (rate limited): flag, continue to Nominatim
              ↓ non-200 or no result: continue to Nominatim

Fallback 1: Nominatim structured search (street + city + state params)
              ↓ non-200 or empty: continue

Fallback 2: Nominatim freeform search (single q= param)
              ↓ non-200 or empty: continue

Fallback 3: US Census Geocoder (free, no key)
              ↓ fails: lat=None, lon=None

When all fail: coordinate-dependent APIs are skipped;
non-coordinate APIs (Census, FRED, Wikipedia, News, FBI) still run.
```

If Intellipins returns no result, building type is classified from OSM signals only. If OSM is also missing, building type defaults to "Single Family Housing" with score 0.20.

---

## Rate Limits at Volume

For single leads this doesn't matter much. For batches, rate limits become the binding constraint. Here's what to know before running 50+ leads.

| API | The constraint | What to do |
|-----|---------------|------------|
| **Nominatim** | 1 req/sec hard limit; violations can get you blocked | Do not parallelize Nominatim across leads. 50 leads ≈ 100 seconds minimum |
| **Overpass** | Soft-throttled; ~3–5 sec between heavy queries | Add 2–3 sec sleep between leads for batches >20 |
| **Intellipins** | Returns 429 on burst | Add 1 sec delay between leads for batch processing |
| **NewsAPI** | 100 req/day free; 1,000/day developer plan | Free tier: hard cap at 100 leads/day |
| **Google Places** | Default 10 QPS; watch monthly billing | Each lead = 2 calls (1 text search + 1 details); runs after phase 1 completes — effectively unlimited for single-user use, but track monthly spend |
| **WalkScore** | 5,000 req/day free | Well above any SDR-scale volume |
| **Anthropic Haiku / Sonnet** | 50 req/min Tier 1 | Won't bind at normal processing speeds (5–10 sec/lead) |
| **Groq free tier** | 30 req/min | Covers both LLM steps comfortably at SDR-scale volumes |
| **Open-Meteo** | 10,000 req/day | Not a realistic constraint |
| **Census, FRED, Wikipedia, FBI** | Generous or undocumented | No material constraint at SDR-scale |

**Recommended batch strategy for >50 leads:** run leads sequentially with a 2-second delay between each. Total throughput ≈ 25–30 leads/hour. Each lead takes 5–10 seconds for the pipeline; the 2-second buffer keeps Nominatim and Overpass within their limits.

---

## Batch Processing at Scale

### Daily Capacity on Free Tiers

The pipeline itself runs in 10–15 seconds per lead. Adding a random 5–7 second inter-lead pause keeps Nominatim and Overpass safely within rate limits and prevents burst detection on any API. That gives the following throughput profile:

| Scenario | Pipeline time | Pause | Cycle time | Leads/min | Leads/day (4-hr run) |
|----------|--------------|-------|------------|-----------|----------------------|
| Fast (cached geocode, no OSM miss) | ~8s | 5s | ~13s | ~4.6 | ~1,100 |
| Typical | ~12s | 6s | ~18s | ~3.3 | ~800 |
| Slow (Overpass timeout, retry) | ~18s | 7s | ~25s | ~2.4 | ~580 |

**Practical target: 1,000 leads per processing run**, achievable in 4–5 hours on the developer NewsAPI plan (1,000 req/day). On the free NewsAPI tier (100 req/day), run batch without news for scoring, then do a second pass pulling news only for Grade A/B leads (typically 15–25% of a list).

```python
import asyncio, random

async def run_batch(leads: list[dict], llm_provider="groq"):
    results = []
    for lead in leads:
        result = await pipeline(lead, llm_provider=llm_provider)
        results.append(result)
        await asyncio.sleep(random.uniform(5, 7))  # jitter prevents burst detection
    return results
```

### From 1,000 Scored Leads to 60 Outreach Emails Per Day

Once you have lead scores, the operational flow is:

```
1,000 leads scored
       │
       ▼
  Sort by Lead Score desc
       │
       ▼
  Take top 60 (Grade A first, then B)
       │
       ▼
  Outreach window: 9:00 AM – 3:00 PM (6 hours)
  10 emails/hour × 6 hours = 60 emails/day
       │
       ▼
  Within each hour: send 10 emails at random intervals
  (uniform random: 2–8 min apart, avg ~6 min)
       │
       ▼
  Log: {lead_id, arc, subject, sent_at}
  Track: open_at, reply_at
```

**Why 10 emails/hour with random spacing:** Sending in bursts (10 emails in 5 minutes, then 50 minutes idle) is the pattern spam filters flag. Random spacing within a window — sometimes 2 minutes apart, sometimes 8 — looks exactly like a human SDR working through their list. The 9am–3pm window targets business hours in the recipient's likely timezone and avoids early-morning and end-of-day slots with lower open rates.

**Why 60 leads/day:** An SDR can realistically follow up on ~60 conversations. Sending more emails than you can track dilutes the whole workflow. The 60-lead/day cap is a quality gate, not a technical limit.

---

## Semi-Automated Outreach (Weeks 1–3)

Before turning on fully automated sending, run a semi-automated phase where the tool generates the email but a human reviews and clicks Send. This serves two purposes: catching bad emails before they damage deliverability, and building a quality signal dataset.

```
Tool generates email
        │
        ▼
SDR review dashboard
  ├── "Looks good — Send" → sent, logged as approved
  ├── "Needs edit" → SDR rewrites, sends, logged as edited
  └── "Skip" → logged as rejected with reason tag
        │
        ▼
Quality signal: edit_distance(original, final) → how much did SDR change it?
                rejection_reason → which arc / data point was wrong?
```

After 2–3 weeks you'll have enough signal to know which email arcs consistently get approved without edits, and which ones SDRs rewrite every time. Fix the weak arcs before turning on auto-send.

---

## A/B Testing Email Performance

The pipeline already assigns each email a `story_arc` field. Use that to run passive A/B tests:

| What to track | How |
|---------------|-----|
| **Arc vs. reply rate** | Group replies by `arc` — which story hook gets the most responses? |
| **Subject line length** | Short (≤6 words) vs. long (≥10 words) |
| **Data-heavy vs. narrative** | Emails that lead with specific numbers vs. ones that lead with a question |
| **Send time within window** | Does 9am outperform 1pm? |

Minimum viable tracking schema:

```json
{
  "lead_id": "uuid",
  "arc": "reputation_gap",
  "subject_word_count": 7,
  "sent_at": "2026-04-26T09:14:33Z",
  "opened_at": null,
  "replied_at": "2026-04-26T11:02:14Z",
  "outcome": "booked_meeting | replied_not_interested | no_reply"
}
```

After 200–300 sends you'll have enough data to see whether, say, `reputation_gap` emails get 3× the reply rate of `lead_speed` emails — and to feed that signal back into the arc selection logic.

---

## Output Schema

Every pipeline run saves a full record to `data/leads/{id}.json`.

```json
{
  "id": "uuid-or-custom-id",
  "created_at": "2026-04-25T18:45:47.782619Z",
  "lead_info": {
    "name": "string",
    "email": "string",
    "company": "string",
    "address": "string",
    "city": "string",
    "state": "string (2-letter)"
  },
  "enrichment": {
    "geocoords": {"lat": float, "lon": float, "source": "intellipins|nominatim|census|none"},
    "census": {"population": "string", "median_income": "string", "renter_percentage": "string"},
    "fred": {"vacancy_rate": "string", "rent_trend": "string"},
    "wikipedia": {"company": null | {"title", "extract", "url"}, "city": {"title", "extract"}},
    "news": {"latest_news": [] | "No relevant news..."},
    "walkscore": {"walk_score": int, "transit_score": int, "bike_score": int},
    "intellipins": {"lat", "lon", "ipins_id", "building_type", "parcel": {...}},
    "google": {"rating": float, "review_count": int, "reviews": [...]},
    "osm": {"osm_type", "building_details": {"floors", "calculated_area"}, "amenities_1000m": {...}},
    "open_meteo": {"annual_precip_days": int, "annual_snowfall_cm": float, "hottest_day_c": float},
    "crime": {"crime_score": float, "violent_crime_rate_per_100k": float, "above_national_avg_violent": bool}
  },
  "scores": {
    "demand":      {"score": float, "available_weight": float, "components": {...}},
    "friction":    {"score": float, "available_weight": float, "components": {...}},
    "scale":       {"score": float, "available_weight": float, "components": {...}},
    "opportunity": {"score": float, "available_weight": float, "news_sentiment": "string", "components": {...}},
    "lead_score":  {"score": float, "grade": "A|B|C|D|F", "available_weight": float, "weights": {...}}
  },
  "pain_points": [
    {"tag": "string", "label": "string", "severity": "high|medium|low", "description": "string", "source": "rule|llm"}
  ],
  "outreach": {
    "subject": "string",
    "greeting": "Hi {first_name},",
    "message": "string",
    "arc": "reputation_gap|operational_friction|growth_strain|premium_expectations|lead_speed",
    "generated_at": "ISO 8601 string",
    "provider": "anthropic|groq"
  }
}
```

The `index.json` file stores only `{id, created_at, name, company, city, state, lead_score, grade}` for each lead — used to populate the history list without loading full records.
