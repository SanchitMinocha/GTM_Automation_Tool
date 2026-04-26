# EliseAI GTM Automation Tool — Pipeline & Architecture

> **Audience:** Engineering, RevOps, anyone who inherits or extends this system.

---

## How It Works — The Short Version

A lead comes in as a name + address. The system geocodes it, fires ~10 API calls in parallel, scores the results deterministically, runs a rule-based pain point engine (then adds ≤2 LLM-generated insights), and finally generates the outreach email with a quality LLM. The whole thing takes 20–60 seconds and saves a full JSON record.

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
│  PARALLEL ENRICHMENT  (enrichment.py → enrich_lead)                 │
│  All 10 API calls run concurrently via asyncio.gather()             │
│                                                                     │
│  ┌─────────────────┐  ┌────────────────┐  ┌──────────────────────┐  │
│  │ Census (city)   │  │ FRED (state)   │  │ Wikipedia (company)  │  │
│  └─────────────────┘  └────────────────┘  └──────────────────────┘  │
│  ┌─────────────────┐  ┌────────────────┐  ┌──────────────────────┐  │
│  │ NewsAPI (co.)   │  │ WalkScore (*)  │  │ Intellipins parcel(*)│  │
│  └─────────────────┘  └────────────────┘  └──────────────────────┘  │
│  ┌─────────────────┐  ┌────────────────┐  ┌──────────────────────┐  │
│  │ Google Places   │  │ OSM/Overpass(*)│  │ Open-Meteo (*)       │  │
│  └─────────────────┘  └────────────────┘  └──────────────────────┘  │
│  ┌─────────────────┐                                                │
│  │ FBI CDE (city)  │   (*) requires lat/lon from geocoding step     │
│  └─────────────────┘                                                │
│                                                                     │
│  Output: enrichment dict with all 10 API results                    │
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
│  POST /pipeline → full record returned to frontend                  │
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
| **Google Places API** | Property rating and review count | $200/month free credit (~11,700 text searches) | Default 10 QPS | API key required |
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

If Intellipins is rate-limited or unavailable, the chain falls through to Nominatim structured, then Nominatim freeform, then US Census Geocoder. If all four fail, `lat` and `lon` are `None`, and the five coordinate-dependent APIs (WalkScore, OSM, Open-Meteo, Intellipins parcel, FBI) are skipped. The other five (Census, FRED, Wikipedia, News, Google Places) still run.

### Step 2: 10 API calls fire in parallel

`asyncio.create_task()` is called for each API, then `asyncio.gather()` awaits all of them. No API waits for any other. Total enrichment time is typically 1–5 seconds, bounded by the slowest API to respond.

### Step 3: Results are assembled into an enrichment dict

After gather completes, results are keyed by API name. The pipeline then runs `_nullify()` on the whole dict — this recursively converts `"N/A"`, `""`, and `"Data unavailable"` strings to `null` before passing to the scorer.

### Step 4: Scoring runs (deterministic, no I/O)

`compute_all_scores(enrichment)` calls four independent sub-scorers. Each extracts numeric values from the enrichment dict, normalizes them to 0–1 using the formulas below, and runs a partial-weight average. Missing signals shrink the denominator — they don't penalize the score.

### Step 5: Pain points

`_rule_based_pain_points()` evaluates ~10 if-conditions against score values and enrichment data. Each fires independently. Then Claude Haiku (or Groq llama-3.1-8b) receives this initial list plus raw enrichment context and appends up to 2 additional insights grounded in specific numbers.

### Step 6: Email generation

Claude Sonnet (or Groq llama-3.3-70b) receives a structured prompt with the lead context, top 5 pain points sorted by severity, and key enrichment numbers. It returns JSON `{subject, message}`. The function adds a `generated_at` timestamp and `provider` field.

### Step 7: Save

`save_lead()` writes the full record to `data/leads/{uuid}.json` and appends a summary row to `data/index.json`.

---

## Scoring Rubric — Full Reference

These are the exact formulas used. If you're tuning weights or adding new signals, this is the spec.

### Demand Score (final weight: 20%)

| Component | Source | Weight | Normalization |
|-----------|--------|--------|---------------|
| renter_pct | Census `DP04_0047PE` | 0.25 | `min(renter_pct / 70.0, 1.0)` |
| low_vacancy | FRED `{STATE}RVAC` | 0.20 | `max(0, 1.0 - vacancy / 15.0)` |
| walk_score | WalkScore | 0.15 | `walk / 100.0` |
| transit_score | WalkScore | 0.10 | `transit / 100.0` |
| income | Census `DP03_0062E` | 0.10 | `min(income / 150000, 1.0)` |
| nearby_amenities | Overpass API | 0.12 | `min((transit_ct + parks_ct + retail_ct) / 100.0, 1.0)` |
| population | Census `DP05_0001E` | 0.08 | `min(population / 500000, 1.0)` |

### Friction Score (final weight: 35%)

| Component | Source | Weight | Normalization |
|-----------|--------|--------|---------------|
| crime | FBI CDE | 0.25 | `(crime_score - 1.0) / 14.0` (1–15 scale) |
| precip_days | Open-Meteo | 0.25 | `min(precip_days / 200.0, 1.0)` |
| snowfall | Open-Meteo | 0.20 | `min(snowfall_cm / 200.0, 1.0)` |
| temp_range | Open-Meteo | 0.20 | `min((hottest_c - coldest_c) / 80.0, 1.0)` |
| elevation | Intellipins parcel | 0.10 | `min(elevation_m / 2000.0, 1.0)` |

### Scale Score (final weight: 15%)

| Component | Source | Weight | Normalization |
|-----------|--------|--------|---------------|
| building_type | Intellipins + OSM | 0.30 | Lookup table (see below) |
| footprint | Overpass polygon | 0.25 | `min(area_sqft / 100000, 1.0)` |
| lot_area | Intellipins parcel | 0.20 | `min(area_sqm * 10.7639 / 200000, 1.0)` |
| floors | OSM `building:levels` | 0.15 | `min(floors / 30.0, 1.0)` |
| units | OSM `building:units` | 0.10 | `min(units / 500.0, 1.0)` |

**Building type lookup:**

| Type | Score |
|------|-------|
| Apartment Complex | 1.00 |
| Hotel | 0.80 |
| Commercial / Industrial | 0.75 |
| Office Building | 0.70 |
| Apartment / Shopping Complex | 0.65 |
| Shopping Complex / Amenity | 0.60 |
| Retail / Shopping | 0.50 |
| Single Family Housing | 0.45 |
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

| Component | Source | Weight | Normalization |
|-----------|--------|--------|---------------|
| news_signal | NewsAPI keyword match | 0.30 | growth→0.85, cost_pressure→0.75, trouble→0.65, mixed→0.55, neutral→0.40, none→0.30 |
| low_rating | Google Places | 0.20 | `max(0, 0.90 - (rating - 1.0) / 4.0 * 0.70)` |
| renter_market | Census | 0.15 | `min(renter_pct / 65.0, 1.0)` |
| vacancy_urgency | FRED | 0.15 | `min(0.30 + vacancy / 10.0 * 0.60, 0.90)` |
| walkability | WalkScore | 0.10 | `walk / 100.0` |
| wiki_presence | Wikipedia REST | 0.10 | `0.80` if company page found, else excluded |

**News sentiment keyword matching:**
- Growth: `expand, acquir, growth, new market, scale, portfolio, launch, partner, open, hire, invest`
- Cost pressure: `layoff, restructur, downsize, cost-cut, job cut, budget, deficit, closure, reduce staff`
- Trouble: `lawsuit, fine, penalty, complaint, eviction, fraud, investigation`

Logic: ≥2 growth hits → `growth`; ≥2 cost hits → `cost_pressure`; ≥2 trouble hits → `trouble`; ≥1 any → `mixed`; else `neutral`.

### Lead Score Composite

```python
weights = {"demand": 0.20, "friction": 0.35, "scale": 0.15, "opportunity": 0.30}
```

A sub-score is only included in the composite if its `available_weight >= 0.30` — meaning at least 30% of its signals had data. The denominator is the sum of included sub-score weights, not a fixed 1.0. A lead that's missing half its signals still gets a fair score, not a penalized one.

---

## When Things Go Wrong

The pipeline is designed to degrade gracefully — any single API failing should produce a slightly less informed score, not an error page.

| What fails | What happens |
|-----------|-------------|
| API key missing or placeholder | Returns `{"error": "Key required"}` for that source; pipeline continues |
| HTTP non-200 response | Returns `{}` or `{"error": "..."}` for that source; signal excluded from scoring |
| Network timeout | `httpx.AsyncClient` per-API timeouts (10–30s); exception caught by `asyncio.gather` |
| `asyncio.gather` exception | Exception object returned; pipeline checks `isinstance(result, Exception)` and falls back to `{}` |
| Geocoding fails completely | `lat=None, lon=None` — coordinate-dependent APIs skipped; Census, FRED, Wikipedia, News, FBI still run |
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
| **Google Places** | Default 10 QPS; watch monthly billing | Each lead = 2 calls; effectively unlimited for single-user use, but track monthly spend |
| **WalkScore** | 5,000 req/day free | Well above any SDR-scale volume |
| **Anthropic Haiku / Sonnet** | 50 req/min Tier 1 | Won't bind at normal processing speeds (5–10 sec/lead) |
| **Groq free tier** | 30 req/min | Covers both LLM steps comfortably at SDR-scale volumes |
| **Open-Meteo** | 10,000 req/day | Not a realistic constraint |
| **Census, FRED, Wikipedia, FBI** | Generous or undocumented | No material constraint at SDR-scale |

**Recommended batch strategy for >50 leads:** run leads sequentially with a 2-second delay between each. Total throughput ≈ 25–30 leads/hour. Each lead takes 5–10 seconds for the pipeline; the 2-second buffer keeps Nominatim and Overpass within their limits.

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
    "message": "string",
    "generated_at": "ISO 8601 string",
    "provider": "anthropic|groq"
  }
}
```

The `index.json` file stores only `{id, created_at, name, company, city, state, lead_score, grade}` for each lead — used to populate the history list without loading full records.
