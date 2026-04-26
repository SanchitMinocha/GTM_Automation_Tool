# EliseAI GTM Automation Tool — Pipeline & Architecture

> **Audience:** Engineering, RevOps, anyone who inherits or extends this system.

---

## 1. System Diagram

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
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐   │
│  │   Demand    │ │  Friction   │ │    Scale    │ │ Opportunity │   │
│  │  (0–100)    │ │  (0–100)    │ │  (0–100)    │ │  (0–100)    │   │
│  └──────┬──────┘ └──────┬──────┘ └──────┬──────┘ └──────┬──────┘   │
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
│  Step 2: LLM enrichment (Claude Haiku, fast=True)                  │
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
│  Claude Sonnet (fast=False, max_tokens=900)                         │
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

## 2. API Inventory

| API | Purpose | Data Returned | Free Tier | Rate Limit | Auth |
|-----|---------|---------------|-----------|------------|------|
| **US Census Bureau ACS 5-Year** | Population, median income, renter % | DP05, DP03, DP04 profile variables | Free, no quota enforced | ~500 req/day recommended | Optional API key (improves reliability) |
| **FRED (St. Louis Fed)** | State-level rental vacancy rate | Latest observation for `{STATE}RVAC` series | Free | 1,000 req/day | API key required |
| **WalkScore API** | Walk, transit, bike scores for address | walkscore, transit.score, bike.score (0–100 each) | 5,000 req/day | 5,000/day free; $0.0025/req above | API key required |
| **Intellipins** | Geocoding, parcel data, building type | lat/lon, ipins_id, parcel area, elevation, owner, APN | No free tier | 429 on burst; ~1 req/sec recommended | API key required (`X-API-KEY` header) |
| **Nominatim (OSM)** | Geocoding fallback, building footprint lookup | lat/lon, osm_type, osm_class, bounding box | Free (public instance) | **1 req/sec max** — must not burst | No key — User-Agent header required |
| **Overpass API (OSM)** | Building geometry, amenity counts in 1km radius | Polygon nodes (for area calc), transit/park/retail counts | Free (public instance) | Soft-throttled; avoid >1 req/3 sec | No key — User-Agent header required |
| **Open-Meteo Archive** | Historical climate (2024) | precip days, snowfall cm, temp max/min by day | Free, 10,000 req/day | 10,000/day | No key required |
| **FBI Crime Data Explorer (CDE)** | City-level crime rates | Violent + property crime rates per 100k, by agency/year | Free | No documented limit | API key required |
| **NewsAPI** | Company news, press releases | Article title, snippet, source, date, URL (up to 5) | 100 req/day (developer plan: 1,000/day) | 100/day free | API key required |
| **Wikipedia REST API** | Company/city summary text | Title, extract (first paragraph), page URL | Free | ~200 req/sec globally; practically unlimited for this use | No key — User-Agent header required |
| **Google Places API** | Property/company rating and reviews | Place name, rating (1–5), review count, up to 5 reviews | $200/month free credit (~11,700 text searches) | Quota-based; default 10 QPS | API key required |
| **Anthropic API (Claude Haiku)** | Pain point LLM enrichment | JSON array of ≤2 additional pain points | None | Tier-dependent; 50 req/min on Tier 1 | API key required |
| **Anthropic API (Claude Sonnet)** | Outreach email generation | JSON `{subject, message}` | None | Tier-dependent | Same key as Haiku |

**Fallback behavior when a key is missing:** Every API check starts with `if not api_key or "your_" in api_key`. Missing keys return a structured `{"error": "Key required"}` dict — the pipeline continues and that signal is excluded from scoring rather than crashing.

---

## 3. Data Flow for a Single Lead

Below is a complete trace of what happens to a single lead record from API call to stored JSON.

### Step 1: Request arrives at POST /pipeline

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

`enabled_apis: null` means all 10 APIs run. You can pass a subset (e.g., `["census","walkscore","crime"]`) to restrict scope.

### Step 2: Geocoding (sequential — all subsequent tasks depend on lat/lon)

`_geocode_address("1600 Vine St", "Los Angeles", "CA")` runs Intellipins first. On success, it returns `(lat, lon, "intellipins", ipins_data_dict)`. The `ipins_data_dict` is passed directly to the parcel lookup — Intellipins is only called once, not twice.

### Step 3: 10 async tasks launched simultaneously

`asyncio.create_task()` is called for each API. `asyncio.gather()` awaits all of them. No API waits for another — they run in parallel, capped by I/O latency (typically 1–3 seconds total for the slowest API to respond).

### Step 4: Enrichment dict assembled

After gather completes, results are keyed by API name:
```python
{
  "geocoords": {"lat": 34.097, "lon": -118.326, "source": "intellipins"},
  "census": {"population": "3,967,000", "median_income": "$65,290", "renter_percentage": "61.5%"},
  "fred": {"vacancy_rate": "4.2%", "rent_trend": "Stable"},
  "walkscore": {"walk_score": 95, "transit_score": 88, "bike_score": 72, ...},
  "intellipins": {"lat": ..., "parcel": {"area_sqm": 4200, "elevation_m": 89, ...}, "building_type": "Apartment Complex"},
  "osm": {"osm_type": "apartments", "building_details": {"floors": "12", "calculated_area": "48,000 sq ft", ...}, "amenities_1000m": {"transit": 24, "parks": 3, "retail": 18}},
  "open_meteo": {"annual_precip_days": 34, "annual_snowfall_cm": 0.0, "hottest_day_c": 42.1, "coldest_day_c": 4.2},
  "crime": {"crime_score": 11.2, "violent_crime_rate_per_100k": 520, "above_national_avg_violent": true, ...},
  "news": {"latest_news": [{"title": "Greystar acquires...", ...}]},
  "wikipedia": {"company": {"title": "Greystar Real Estate Partners", "extract": "..."}, "city": {...}},
  "google": {"rating": 3.1, "review_count": 412, "reviews": [...]}
}
```

All `"N/A"`, `""`, `"Data unavailable"` strings are recursively replaced with `null` via `_nullify()` before scoring.

### Step 5: Scoring (pure deterministic functions — no I/O)

`compute_all_scores(enrichment)` calls four sub-scorers in sequence. Each iterates the enrichment dict, extracts numeric values via `_parse_float()`, normalizes them 0–1, and runs `_weighted_score()`. Missing signals are simply not added to `components` — the denominator shrinks, and the `available_weight` reflects this.

### Step 6: Pain point inference

`_rule_based_pain_points()` runs ~10 if-conditions against scores + enrichment values. Each fires independently. Output is a list of tagged dicts. Claude Haiku then receives this list plus raw data context and appends ≤2 LLM-generated points.

### Step 7: Outreach generation

Claude Sonnet receives a structured prompt with lead context, top 5 pain points (sorted by severity), and key enrichment numbers. It returns JSON `{subject, message}`. The function wraps it with `generated_at` timestamp and `provider`.

### Step 8: Storage

`save_lead()` writes the full record to `data/leads/{uuid}.json` and appends a summary row to `data/index.json`.

---

## 4. Scoring Rubric — Full Reference

### Demand Score (final weight: 20%)

| Component | Source API | Weight | Normalization Formula |
|-----------|------------|--------|-----------------------|
| renter_pct | Census `DP04_0047PE` | 0.25 | `min(renter_pct / 70.0, 1.0)` |
| low_vacancy | FRED `{STATE}RVAC` | 0.20 | `max(0, 1.0 - vacancy / 15.0)` |
| walk_score | WalkScore | 0.15 | `walk / 100.0` |
| transit_score | WalkScore | 0.10 | `transit / 100.0` |
| income | Census `DP03_0062E` | 0.10 | `min(income / 150000, 1.0)` |
| nearby_amenities | Overpass API | 0.12 | `min((transit_ct + parks_ct + retail_ct) / 100.0, 1.0)` |
| population | Census `DP05_0001E` | 0.08 | `min(population / 500000, 1.0)` |

### Friction Score (final weight: 35%)

| Component | Source API | Weight | Normalization Formula |
|-----------|------------|--------|-----------------------|
| crime | FBI CDE | 0.25 | `(crime_score - 1.0) / 14.0` (score is 1–15 scale) |
| precip_days | Open-Meteo archive | 0.25 | `min(precip_days / 200.0, 1.0)` |
| snowfall | Open-Meteo archive | 0.20 | `min(snowfall_cm / 200.0, 1.0)` |
| temp_range | Open-Meteo archive | 0.20 | `min((hottest_c - coldest_c) / 80.0, 1.0)` |
| elevation | Intellipins parcel | 0.10 | `min(elevation_m / 2000.0, 1.0)` |

### Scale Score (final weight: 15%)

| Component | Source API | Weight | Normalization Formula |
|-----------|------------|--------|-----------------------|
| building_type | Intellipins + OSM | 0.30 | Lookup table (see below) |
| footprint | Overpass (polygon area) | 0.25 | `min(area_sqft / 100000, 1.0)` |
| lot_area | Intellipins parcel | 0.20 | `min(area_sqm * 10.7639 / 200000, 1.0)` |
| floors | OSM `building:levels` | 0.15 | `min(floors / 30.0, 1.0)` |
| units | OSM `building:units` | 0.10 | `min(units / 500.0, 1.0)` |

**Building type lookup table:**

| Building Type | Normalized Score |
|---------------|-----------------|
| Apartment Complex | 1.00 |
| Hotel | 0.80 |
| Commercial / Industrial | 0.75 |
| Office Building | 0.70 |
| Apartment / Shopping Complex | 0.65 |
| Shopping Complex / Amenity | 0.60 |
| Retail / Shopping | 0.50 |
| Single Family Housing | 0.45 |
| Unknown | 0.20 |

**Building type classification logic** (in priority order):
1. If OSM type is `apartments`, `residential`, or `dormitory` → Apartment Complex
2. If OSM type is `commercial`, `retail`, `industrial` → Commercial / Industrial
3. If OSM type is `office` → Office Building
4. If OSM type is `hotel` → Hotel
5. If OSM class is `amenity` → Shopping Complex / Amenity
6. If OSM class is `shop` → Retail / Shopping
7. If Intellipins `address_type` is `base` or `supplementary` → Apartment / Shopping Complex
8. Default → Single Family Housing

### Opportunity Score (final weight: 30%)

| Component | Source API | Weight | Normalization Formula |
|-----------|------------|--------|-----------------------|
| news_signal | NewsAPI keyword match | 0.30 | growth→0.85, cost_pressure→0.75, trouble→0.65, mixed→0.55, neutral→0.40, none→0.30 |
| low_rating | Google Places | 0.20 | `max(0, 0.90 - (rating - 1.0) / 4.0 * 0.70)` |
| renter_market | Census | 0.15 | `min(renter_pct / 65.0, 1.0)` |
| vacancy_urgency | FRED | 0.15 | `min(0.30 + vacancy / 10.0 * 0.60, 0.90)` |
| walkability | WalkScore | 0.10 | `walk / 100.0` |
| wiki_presence | Wikipedia REST | 0.10 | `0.80` if company page found, else skipped |

**News sentiment keyword matching:**
- Growth keywords: `expand, acquir, growth, new market, scale, portfolio, launch, partner, open, hire, invest`
- Cost pressure keywords: `layoff, restructur, downsize, cost-cut, job cut, budget, deficit, closure, reduce staff`
- Trouble keywords: `lawsuit, fine, penalty, complaint, eviction, fraud, investigation`
- ≥2 growth hits → `growth`; ≥2 cost hits → `cost_pressure`; ≥2 trouble hits → `trouble`; ≥1 any → `mixed`; else `neutral`

### Lead Score Composite

```python
weights = {"demand": 0.20, "friction": 0.35, "scale": 0.15, "opportunity": 0.30}
```

A sub-score is only included if its `available_weight >= 0.30` (i.e., at least 30% of its max-weight signals were available). The denominator is the sum of weights of included sub-scores, not 1.0 — so a lead missing half its signals still gets a fair score, not a penalized one.

---

## 5. Error Handling

| Scenario | Behavior |
|----------|----------|
| API key missing or placeholder | Returns `{"error": "Key required"}` for that source; pipeline continues |
| HTTP non-200 response | Returns `{}` or `{"error": "...status code..."}` for that source |
| Network timeout | `httpx.AsyncClient` has per-API timeouts (10–30s); timeout raises exception caught by `asyncio.gather` |
| `asyncio.gather` exception | Returns the exception object; pipeline checks `isinstance(result, Exception)` and falls back to `{}` |
| Geocoding fails completely | `lat=None, lon=None` — WalkScore, OSM, Open-Meteo, Intellipins parcel are all skipped; Census, FRED, Wikipedia, News, FBI still run |
| Intellipins rate limited (429) | `_geocode_address` catches `RuntimeError("rate_limited")`; falls back to Nominatim; downstream Intellipins parcel is set to `{"error": "Rate limited..."}` |
| LLM (Haiku) error | `_llm_enrich` catches all exceptions; returns rule-based points only |
| LLM (Sonnet) error | `generate_outreach` catches all exceptions; returns `{"error": ..., "subject": "", "message": ""}` — pipeline still saves |
| FBI ORI not found for city | Returns `{"error": "No ORI found for {city}, {state}"}` — crime signal excluded from scoring |
| OSM building not found | `building_details: {}` — footprint and floors signals excluded from scale score |
| News returns no results | Returns `{"latest_news": "No relevant news found..."}` — scored as `"none"` sentiment (0.30) |

---

## 6. Fallback Chain — Geocoding

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

Result when all fail: coordinate-dependent APIs are skipped; non-coordinate
APIs (Census, FRED, Wikipedia, News, FBI) still run.
```

**Fallback chain — Intellipins building type:**
If Intellipins returns no result or an error, `building_type` is classified from OSM signals only (osm_class + osm_type). If OSM is also missing, building type defaults to "Single Family Housing" with normalized score 0.20.

**Fallback chain — news enrichment:**
If NewsAPI returns no articles matching the company name, news sentiment is scored as `"none"` (0.30). If NewsAPI key is missing, news is excluded from scoring entirely (component not added to opportunity dict).

---

## 7. Rate Limit Management

For batches of leads, rate limits are the primary operational constraint. The table below describes behavior per API at volume.

| API | Constraint | Mitigation |
|-----|-----------|------------|
| **Nominatim** | 1 req/sec hard limit | Each lead makes 1–2 Nominatim calls (forward + optional reverse). At 1 req/sec, 50 leads ≈ 100 seconds of Nominatim time minimum. Do not parallelize Nominatim across leads. |
| **Overpass** | Soft throttle; ~3–5 sec between heavy queries | Runs two queries per lead (building geometry + amenity radius). For batches >20 leads, add 2–3 sec sleep between leads. |
| **Intellipins** | Rate limited at burst; no published req/sec | Returns 429 on burst. Current code detects 429, flags, and falls back. For batch processing, add 1 sec delay between leads. |
| **NewsAPI** | 100 req/day (free), 1,000/day (developer) | Each lead = 1 NewsAPI call. Free tier: 100 leads/day max. Developer: 1,000 leads/day. |
| **Google Places** | Quota-based; default 10 QPS | Each lead = 2 calls (Text Search + Place Details). At 10 QPS, effectively unlimited for single-user batch. Watch monthly billing. |
| **WalkScore** | 5,000 req/day free | Each lead = 1 call. 5,000 leads/day before billing kicks in. |
| **Anthropic (Haiku)** | Tier 1: 50 req/min | Haiku call per lead for pain points. At 50 leads/min sustained, you'd hit this. In practice, total pipeline time per lead is 5–10 sec, so this won't bind. |
| **Anthropic (Sonnet)** | Tier 1: 50 req/min | Same — one call per lead. Will not bind at normal processing speeds. |
| **Open-Meteo** | 10,000 req/day | 1 call per lead. 10,000 leads/day max at free tier. |
| **Census, FRED, Wikipedia, FBI** | Generous/none | No material constraint at SDR-scale volumes. |

**Recommended batch strategy for >50 leads:** run the pipeline sequentially per lead with a 2-second inter-lead delay. Total throughput ≈ 25–30 leads/hour, bounded by the slowest API per lead (~5–10 sec) plus the 2-sec buffer.

---

## 8. Output Schema

Every pipeline run produces a record in `data/leads/{id}.json` with this structure:

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
    "walkscore": {"walk_score": int, "transit_score": int, "bike_score": int, ...},
    "intellipins": {"lat", "lon", "ipins_id", "building_type", "parcel": {...}},
    "google": {"rating": float, "review_count": int, "reviews": [...]},
    "osm": {"osm_type", "building_details": {"floors", "calculated_area", ...}, "amenities_1000m": {...}},
    "open_meteo": {"annual_precip_days": int, "annual_snowfall_cm": float, "hottest_day_c": float, ...},
    "crime": {"crime_score": float, "violent_crime_rate_per_100k": float, "above_national_avg_violent": bool, ...}
  },
  "scores": {
    "demand":      {"score": float, "available_weight": float, "max_weight": 1.0, "components": {...}},
    "friction":    {"score": float, "available_weight": float, "max_weight": 1.0, "components": {...}},
    "scale":       {"score": float, "available_weight": float, "max_weight": 1.0, "components": {...}},
    "opportunity": {"score": float, "available_weight": float, "max_weight": 1.0, "news_sentiment": "string", "components": {...}},
    "lead_score":  {"score": float, "grade": "A|B|C|D|F", "available_weight": float, "weights": {...}, "components": {...}}
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

The `index.json` file is a lightweight summary array with only `{id, created_at, name, company, city, state, lead_score, grade}` — used to populate the leads list without loading full records.
