import httpx
import os
import csv
import asyncio
import pathlib
from datetime import datetime
from urllib.parse import quote, urlparse
from typing import Dict, Any
from .constants import STATE_FIPS, FULL_STATE_NAMES

# ---------------------------------------------------------------------------
# FBI ORI lookup — built once with build_ori_lookup(), used at runtime
# ---------------------------------------------------------------------------

_ORI_LOOKUP_PATH = pathlib.Path(__file__).parent / "fbi_ori_lookup.csv"
_ori_cache: dict | None = None


def _load_ori_lookup() -> dict:
    """
    Load fbi_ori_lookup.csv into memory keyed by (city_lower, state_upper).
    Prefers city/local police departments when multiple agencies share a city.
    """
    global _ori_cache
    if _ori_cache is not None:
        return _ori_cache
    _ori_cache = {}
    if not _ORI_LOOKUP_PATH.exists():
        return _ori_cache
    with open(_ORI_LOOKUP_PATH, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            key = (row["city"].lower().strip(), row["state"].upper().strip())
            agency_type = (row.get("agency_type") or "").lower()
            existing = _ori_cache.get(key)
            if existing is None or (
                "city" in agency_type and "city" not in existing.get("agency_type", "").lower()
            ):
                _ori_cache[key] = {"ori": row["ori"], "agency_type": agency_type}
    return _ori_cache


def city_to_ori(city: str, state: str) -> str | None:
    lookup = _load_ori_lookup()
    state_up   = state.upper().strip()
    city_lower = city.lower().strip()

    # 1. Exact match (state already scopes the key, so no cross-state ambiguity)
    entry = lookup.get((city_lower, state_up))
    if entry:
        return entry["ori"]

    # 2. Word-suffix fallback: "East Falmouth" → try "Falmouth", then each
    #    subsequent suffix so compound prefixes (North, East, West, …) are dropped.
    words = city_lower.split()
    for i in range(1, len(words)):
        suffix = " ".join(words[i:])
        entry = lookup.get((suffix, state_up))
        if entry:
            return entry["ori"]

    # 3. Substring fallback (state-scoped): lookup city is a whole-word substring
    #    of the input, e.g. lookup="falmouth" matches input="east falmouth".
    #    Uses word-boundary regex to avoid "art" matching "hartford".
    for (lc, ls), e in lookup.items():
        if ls == state_up and lc != city_lower:
            if _re.search(r'\b' + _re.escape(lc) + r'\b', city_lower):
                return e["ori"]

    # 4. Reverse substring (state-scoped): input city appears as whole words inside
    #    a lookup entry, e.g. "new hartford" matches "new hartford town and village".
    #    State is already guaranteed to match by the ls == state_up filter.
    for (lc, ls), e in lookup.items():
        if ls == state_up and lc != city_lower:
            if _re.search(r'\b' + _re.escape(city_lower) + r'\b', lc):
                return e["ori"]

    return None


import re as _re
_CITY_STRIP = _re.compile(
    r"\s+(?:Police\s+(?:Department|Dept\.?)|P\.?D\.?|Public\s+Safety(?:\s+(?:Department|Dept\.?))?)$",
    _re.IGNORECASE,
)


def _extract_city(agency_name: str) -> str:
    """Pull city name from strings like 'Bellevue Police Department' → 'bellevue'."""
    return _CITY_STRIP.sub("", agency_name).lower().strip()


def build_ori_lookup(api_key: str, states: list[str] | None = None) -> None:
    """
    One-time utility: download all FBI agency records and save to fbi_ori_lookup.csv.
    Run from the project root:
        python -c "from backend.enrichment import build_ori_lookup; build_ori_lookup('<key>')"
    Only City-type agencies are stored — they're the ones with usable crime data.
    """
    if states is None:
        states = [
            "AL","AK","AZ","AR","CA","CO","CT","DE","FL","GA",
            "HI","ID","IL","IN","IA","KS","KY","LA","ME","MD",
            "MA","MI","MN","MS","MO","MT","NE","NV","NH","NJ",
            "NM","NY","NC","ND","OH","OK","OR","PA","RI","SC",
            "SD","TN","TX","UT","VT","VA","WA","WV","WI","WY",
        ]

    all_agencies: list[dict] = []
    with httpx.Client(timeout=15.0) as client:
        for state in states:
            url = f"https://api.usa.gov/crime/fbi/cde/agency/byStateAbbr/{state}"
            r = client.get(url, params={"API_KEY": api_key})
            if r.status_code != 200:
                print(f"Warning: {state} returned {r.status_code}")
                continue
            data = r.json()
            count = 0
            # Response is keyed by county name; values are lists of agencies
            for county_agencies in data.values():
                for a in county_agencies:
                    agency_type = (a.get("agency_type_name") or "").strip()
                    if agency_type != "City":
                        continue
                    city = _extract_city(a.get("agency_name", ""))
                    if not city:
                        continue
                    all_agencies.append({
                        "ori":         a.get("ori"),
                        "agency_name": a.get("agency_name"),
                        "city":        city,
                        "state":       (a.get("state_abbr") or "").upper(),
                        "agency_type": agency_type,
                    })
                    count += 1
            print(f"Done: {state} ({count} city agencies)")

    fieldnames = ["ori", "agency_name", "city", "state", "agency_type"]
    with open(_ORI_LOOKUP_PATH, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(all_agencies)

    global _ori_cache
    _ori_cache = None  # force reload on next lookup
    print(f"Saved {len(all_agencies)} city agencies to {_ORI_LOOKUP_PATH}")

async def get_census_data(city: str, state: str) -> Dict[str, Any]:
    state_code = STATE_FIPS.get(state.upper())
    if not state_code:
        return {"error": "Invalid state code"}

    api_key = os.getenv("CENSUS_API_KEY")
    key_param = f"&key={api_key}" if api_key and "your_" not in api_key else ""
    
    url = f"https://api.census.gov/data/2021/acs/acs5/profile?get=NAME,DP05_0001E,DP03_0062E,DP04_0047PE&for=place:*&in=state:{state_code}{key_param}"
    
    # Increase timeout for large census requests
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            print(f"Fetching Census data for {city}, {state}...")
            response = await client.get(url)
            if response.status_code == 200:
                data = response.json()
                city_lower = city.lower()
                best_row, best_pop = None, -1
                for row in data[1:]:
                    # Match against place name only (before first comma) to avoid
                    # matching the state suffix — e.g. "new york" must not match
                    # "Albany city, New York" via the ", New York" state suffix.
                    place_name = row[0].split(",")[0].lower()
                    if not place_name.startswith(city_lower):
                        continue
                    # Pick the highest-population result to break ties like
                    # "New York city" vs "New York Mills village".
                    try:
                        pop = int(row[1]) if row[1] else 0
                    except (ValueError, TypeError):
                        pop = 0
                    if pop > best_pop:
                        best_pop, best_row = pop, row
                if best_row:
                    row = best_row
                    print(f"Found Census match: {row[0]}")
                    return {
                        "population": f"{int(row[1]):,}" if row[1] and int(row[1]) > 0 else "N/A",
                        "median_income": f"${int(row[2]):,}" if row[2] and int(row[2]) > 0 else "N/A",
                        "renter_percentage": f"{row[3]}%" if row[3] and float(row[3]) > 0 else "N/A"
                    }
            else:
                print(f"Census API error: {response.status_code}")
        except Exception as e:
            print(f"Census exception: {e}")
    
    return {
        "population": "Data unavailable",
        "median_income": "Data unavailable",
        "renter_percentage": "Data unavailable"
    }

async def get_fred_data(city: str, state: str) -> Dict[str, Any]:
    api_key = os.getenv("FRED_API_KEY")
    if not api_key or "your_" in api_key:
        return {"vacancy_rate": "Key required", "rent_trend": "Key required"}

    series_id = f"{state.upper()}RVAC" # State-level rental vacancy
    url = f"https://api.stlouisfed.org/fred/series/observations?series_id={series_id}&api_key={api_key}&file_type=json&sort_order=desc&limit=1"
    
    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            response = await client.get(url)
            if response.status_code == 200:
                data = response.json()
                obs = data.get("observations", [])
                if obs:
                    return {
                        "vacancy_rate": f"{obs[0]['value']}%",
                        "rent_trend": "Stable"
                    }
        except Exception:
            pass
    return {"vacancy_rate": "N/A", "rent_trend": "N/A"}

_WIKI_HEADERS = {
    "User-Agent": "GTM-Automation-Tool/1.0 (educational project; contact: msanchit@uw.edu)"
}

async def _wiki_fetch(slug: str, client: httpx.AsyncClient) -> Dict[str, Any] | None:
    """Fetch a Wikipedia summary page. Returns the JSON dict or None on failure."""
    url = f"https://en.wikipedia.org/api/rest_v1/page/summary/{slug}"
    try:
        r = await client.get(url, headers=_WIKI_HEADERS)
        if r.status_code == 200:
            data = r.json()
            if data.get("type") != "disambiguation" and data.get("extract"):
                return data
    except Exception:
        pass
    return None

async def get_wikipedia_data(company: str, city: str, state: str) -> Dict[str, Any]:
    full_state = FULL_STATE_NAMES.get(state.upper(), state)

    async with httpx.AsyncClient(timeout=12.0, follow_redirects=True) as client:
        # Try company lookup — works for large/public companies (Greystar, AvalonBay, etc.)
        company_slug = quote(company.replace(" ", "_"))
        company_data = await _wiki_fetch(company_slug, client)

        # City lookup — try "City,_Full_State" then plain city name
        city_slug = quote(f"{city},_{full_state}".replace(" ", "_"))
        city_data = await _wiki_fetch(city_slug, client)
        if not city_data:
            city_data = await _wiki_fetch(quote(city.replace(" ", "_")), client)

    return {
        "company": {
            "title":   company_data["title"],
            "extract": company_data["extract"],
            "url":     company_data.get("content_urls", {}).get("desktop", {}).get("page", ""),
        } if company_data else None,
        "city": {
            "title":   city_data["title"],
            "extract": city_data["extract"],
        } if city_data else {"title": city, "extract": ""},
    }

_RE_TERMS = '("real estate" OR "property management" OR "apartments" OR "multifamily" OR "housing" OR "rental" OR "leasing" OR "property")'
_BAD_DOMAINS = {"removed.com", "content.removed.com", "consent.yahoo.com"}

def _usable_url(url: str) -> bool:
    """Require https and exclude known placeholder domains."""
    if not url:
        return False
    try:
        p = urlparse(url.strip())
        return p.scheme == "https" and p.netloc not in _BAD_DOMAINS
    except Exception:
        return False

async def get_news_data(company: str, city: str) -> Dict[str, Any]:
    api_key = os.getenv("NEWS_API_KEY")
    if not api_key or "your_" in api_key:
        return {"latest_news": "API Key required."}

    q = quote(f'"{company}" AND {_RE_TERMS}')
    url = f"https://newsapi.org/v2/everything?q={q}&language=en&sortBy=relevancy&pageSize=15&apiKey={api_key}"

    articles: list = []
    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            r = await client.get(url)
            print(f"News API status: {r.status_code}, query: {company}")
            if r.status_code == 200:
                raw = r.json().get("articles", [])
                company_lower = company.lower()
                city_lower = city.lower()

                candidates = []
                for a in raw:
                    title = a.get("title") or ""
                    desc  = a.get("description") or ""
                    art_url = a.get("url", "")

                    if title == "[Removed]" or not _usable_url(art_url):
                        continue
                    # Company name must appear in title or description
                    if company_lower not in (title + " " + desc).lower():
                        continue

                    candidates.append({
                        "title":      title,
                        "snippet":    desc.strip()[:220],
                        "date":       _fmt_date(a.get("publishedAt", "")),
                        "url":        art_url.strip(),
                        "source":     a.get("source", {}).get("name", ""),
                        "city_match": city_lower in (title + " " + desc).lower(),
                    })

                # City-mentioning articles first
                articles = sorted(candidates, key=lambda x: 0 if x["city_match"] else 1)
        except Exception as e:
            print(f"News API error: {e}")

    if not articles:
        return {"latest_news": f"No relevant news found for \"{company}\" in real estate or property management."}

    return {"latest_news": articles[:5]}

def _fmt_date(iso_str: str) -> str:
    try:
        return datetime.fromisoformat(iso_str.replace("Z", "+00:00")).strftime("%b %Y")
    except Exception:
        return ""

# ---------------------------------------------------------------------------
# Intellipins — two private helpers so /geocode/forward is called exactly
# once (inside _geocode_address) and the result is reused by the parcel
# lookup task in enrich_lead — no API called twice.
# ---------------------------------------------------------------------------

async def _intellipins_forward_geocode(address: str, city: str, state: str) -> Dict[str, Any] | None:
    """
    Call Intellipins /geocode/forward once. Returns a result dict on success or
    None on failure. Dict keys: lat, lon, ipins_id, address_type, building_type,
    formatted_address, geocode_score.
    """
    api_key = os.getenv("INTELLIPINS_KEY")
    if not api_key or "your_" in api_key:
        return None
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            r = await client.post(
                "https://api.intellipins.com/v1/address/geocode/forward",
                headers={"Accept": "application/json", "Content-Type": "application/json",
                         "X-API-KEY": api_key},
                json={"address": f"{address}, {city}, {state}", "candidates": 1, "country": "USA"},
            )
            print(f"Intellipins geocode status: {r.status_code}")
            if r.status_code == 429:
                raise RuntimeError("rate_limited")
            if r.status_code != 200:
                return None
            results = r.json()
            if not results:
                return None
            first     = results[0]
            doc       = first.get("document", {})
            loc       = doc.get("location", {})
            lat, lon  = loc.get("lat"), loc.get("lon")
            if lat is None or lon is None:
                return None
            ipins_id  = doc.get("ipins_id")
            addr_type = doc.get("address_type")
            fmt_parts = doc.get("formatted_address", [])
            score     = first.get("score")
            print(f"Intellipins geocoded {address}: lat={lat}, lon={lon}")
            return {
                "lat":               float(lat),
                "lon":               float(lon),
                "ipins_id":          ipins_id or "N/A",
                "address_type":      addr_type or "N/A",
                "formatted_address": ", ".join(fmt_parts) if fmt_parts else "N/A",
                "geocode_score":     score,
            }
    except RuntimeError as e:
        if str(e) == "rate_limited":
            print("Intellipins geocode: rate limited (429)")
            raise
        return None
    except Exception as e:
        print(f"Intellipins geocode error: {e}")
        return None


async def _intellipins_parcel_lookup(geocode_result: Dict[str, Any]) -> Dict[str, Any]:
    """
    Call Intellipins /parcel-lookup using the ipins_id from a pre-fetched geocode
    result. Adds a 'parcel' key to the dict and returns it — no re-geocode.
    """
    api_key  = os.getenv("INTELLIPINS_KEY")
    ipins_id = geocode_result.get("ipins_id")
    if not api_key or "your_" in api_key or not ipins_id or ipins_id == "N/A":
        return geocode_result
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            r = await client.post(
                "https://api.intellipins.com/v1/address/parcel-lookup",
                headers={"Accept": "application/json", "Content-Type": "application/json",
                         "X-API-KEY": api_key},
                json={"country": "usa", "ipins_id": ipins_id, "return_geometry": True},
            )
            print(f"Intellipins parcel-lookup status: {r.status_code}")
            if r.status_code == 200:
                parcel_raw = r.json()
                if parcel_raw and parcel_raw[0]:
                    pdoc     = parcel_raw[0].get("document", {})
                    addendum = pdoc.get("addendum", {})
                    area_sqm = addendum.get("area")
                    elev     = addendum.get("elevation")
                    geocode_result["parcel"] = {
                        "area_sqm":     area_sqm,
                        "area_sqft":    f"{int(area_sqm * 10.7639):,} sq ft" if area_sqm else "N/A",
                        "elevation_m":  elev if elev is not None else "N/A",
                        "parcel_owner": pdoc.get("parcel_owner") or "N/A",
                        "apn":          pdoc.get("apn") or "N/A",
                        "iparcel_id":   pdoc.get("iparcel_id") or "N/A",
                        "geometry":     pdoc.get("geometry"),
                    }
    except Exception as e:
        print(f"Intellipins parcel-lookup error: {e}")
    return geocode_result


_OSM_HEADERS = {"User-Agent": "GTM-Automation-Tool/1.0 (educational project; contact: msanchit@uw.edu)"}


def _classify_building_type(
    address_type: str | None,
    osm_class: str | None,
    osm_type: str | None,
    osm_building_tag: str | None = None,
    walk_score: int | float | None = None,
) -> str | None:
    osm_class_lc    = (osm_class or "").lower()
    osm_type_lc     = (osm_type or "").lower()
    addr_type_lc    = (address_type or "").lower()
    building_tag_lc = (osm_building_tag or "").lower()

    _APARTMENT_TAGS = {"apartments", "residential", "dormitory", "property_management", "flat", "housing"}
    if osm_type_lc in _APARTMENT_TAGS or building_tag_lc in _APARTMENT_TAGS:
        return "Apartment Complex"
    if osm_type_lc in ("commercial", "retail", "supermarket", "warehouse", "industrial"):
        return "Commercial / Industrial"
    if osm_type_lc == "office" or osm_class_lc == "office":
        return "Office Building"
    if osm_type_lc == "hotel":
        return "Hotel"
    if osm_class_lc == "amenity":
        return "Shopping Complex / Amenity"
    if osm_class_lc == "shop":
        return "Retail / Shopping"
    if addr_type_lc in ("base", "supplementary"):
        return "Apartment / Shopping Complex"
    # Only call it Single Family if OSM explicitly tags it as such.
    # Nominatim type="house" just means an interpolated road address — not a building type.
    _SINGLE_FAMILY_TAGS = {"house", "detached", "semidetached_house", "bungalow", "terrace"}
    if building_tag_lc in _SINGLE_FAMILY_TAGS:
        return "Single Family Housing"
    # Walk score fallback: car-dependent areas (< 50) skew single family;
    # walkable areas (>= 50) skew apartment/shopping complex.
    if walk_score is not None:
        return "Single Family Housing" if walk_score < 50 else "Apartment / Shopping Complex"
    return "Unknown"


async def _geocode_address(
    address: str, city: str, state: str
) -> tuple[float | None, float | None, str, Dict[str, Any] | None]:
    """
    Geocode a US address. Order: Intellipins → Nominatim structured → Nominatim freeform → US Census.
    Returns (lat, lon, source, intellipins_data).
    intellipins_data is the _intellipins_forward_geocode result when Intellipins
    succeeds — enrich_lead passes it directly to _intellipins_parcel_lookup so the
    forward geocode is never called a second time.
    """
    ipins_rate_limited = False
    try:
        ipins_data = await _intellipins_forward_geocode(address, city, state)
    except RuntimeError:
        ipins_data = None
        ipins_rate_limited = True
    if ipins_data:
        return ipins_data["lat"], ipins_data["lon"], "intellipins", ipins_data

    async with httpx.AsyncClient(timeout=15.0) as client:
        # Fallback 1: Nominatim structured search (separate params — more reliable)
        try:
            r = await client.get(
                "https://nominatim.openstreetmap.org/search",
                headers=_OSM_HEADERS,
                params={"street": address, "city": city, "state": state,
                        "country": "US", "format": "json", "limit": 1},
            )
            if r.status_code == 200:
                data = r.json()
                if data:
                    lat, lon = float(data[0]["lat"]), float(data[0]["lon"])
                    print(f"Nominatim structured geocoded {address}: lat={lat}, lon={lon}")
                    return lat, lon, "nominatim_structured", "rate_limited" if ipins_rate_limited else None
        except Exception as e:
            print(f"Nominatim structured geocoding error: {e}")

        # Fallback 2: Nominatim freeform search
        try:
            r = await client.get(
                "https://nominatim.openstreetmap.org/search",
                headers=_OSM_HEADERS,
                params={"q": f"{address}, {city}, {state}", "format": "json", "limit": 1},
            )
            if r.status_code == 200:
                data = r.json()
                if data:
                    lat, lon = float(data[0]["lat"]), float(data[0]["lon"])
                    print(f"Nominatim freeform geocoded {address}: lat={lat}, lon={lon}")
                    return lat, lon, "nominatim", "rate_limited" if ipins_rate_limited else None
        except Exception as e:
            print(f"Nominatim freeform geocoding error: {e}")

        # Fallback 3: US Census Geocoder
        census_url = (
            f"https://geocoding.geo.census.gov/geocoder/locations/address"
            f"?street={address.replace(' ', '+')}&city={city.replace(' ', '+')}&state={state}"
            f"&benchmark=Public_AR_Current&format=json"
        )
        try:
            r = await client.get(census_url)
            if r.status_code == 200:
                matches = r.json().get("result", {}).get("addressMatches", [])
                if matches:
                    coords = matches[0].get("coordinates", {})
                    lat, lon = coords.get("y"), coords.get("x")
                    print(f"Census geocoded {address}: lat={lat}, lon={lon}")
                    return float(lat), float(lon), "census", "rate_limited" if ipins_rate_limited else None
        except Exception as e:
            print(f"Census geocoding error: {e}")

    return None, None, "none", "rate_limited" if ipins_rate_limited else None


async def get_walkscore_data(address: str, city: str, state: str, lat: float, lon: float) -> Dict[str, Any]:
    api_key = os.getenv("WALKSCORE_API_KEY")
    if not api_key or "your_" in api_key:
        return {"walk_score": "Key required", "description": "N/A"}

    # Step 2: Call WalkScore JSON API from the backend (no browser referer check)
    full_address = f"{address}, {city}, {state}".replace(" ", "+")
    ws_url = (
        f"https://api.walkscore.com/score?format=json"
        f"&address={full_address}&lat={lat}&lon={lon}"
        f"&transit=1&bike=1&wsapikey={api_key}"
    )
    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            resp = await client.get(ws_url)
            print(f"WalkScore status: {resp.status_code}, body: {resp.text[:200]}")
            if resp.status_code == 200:
                data = resp.json()
                if data.get("status") == 1:
                    result = {
                        "walk_score": data.get("walkscore", "N/A"),
                        "description": data.get("description", ""),
                    }
                    if "transit" in data:
                        result["transit_score"] = data["transit"].get("score", "N/A")
                        result["transit_description"] = data["transit"].get("description", "")
                    if "bike" in data:
                        result["bike_score"] = data["bike"].get("score", "N/A")
                        result["bike_description"] = data["bike"].get("description", "")
                    return result
                else:
                    print(f"WalkScore API status code in response: {data.get('status')}")
        except Exception as e:
            print(f"WalkScore exception: {e}")

    return {"walk_score": "N/A", "description": "Walk Score unavailable"}


_GP_STOP_WORDS = frozenset({"the", "of", "and", "a", "an", "at", "in", "for", "co", "inc", "llc", "ltd", "corp", "lp"})


def _company_name_matches(company: str, place_name: str) -> bool:
    """Return True if any significant word from company appears in place_name."""
    sig_words = {w.lower() for w in company.split() if w.lower() not in _GP_STOP_WORDS and len(w) > 2}
    place_lower = place_name.lower()
    return any(w in place_lower for w in sig_words)


async def get_google_places_data(
    company: str,
    address: str,
    city: str,
    state: str,
    building_type: str | None = None,
    lat: float | None = None,
    lon: float | None = None,
) -> Dict[str, Any]:
    api_key = os.getenv("GOOGLE_PLACES_API_KEY")
    if not api_key or "your_" in (api_key or ""):
        return {"error": "Key required"}

    base = "https://maps.googleapis.com/maps/api/place"

    location_params: dict = {}
    if lat is not None and lon is not None:
        location_params = {"location": f"{lat},{lon}", "radius": 50000}

    _SKIP_TYPES   = {"locality", "political", "country", "route",
                     "administrative_area_level_1", "administrative_area_level_2"}
    _ACCEPT_TYPES = {"establishment", "point_of_interest", "apartment_complex"}

    _no_match_result = {
        "place_name":        None,
        "matched_via":       None,
        "place_types":       [],
        "rating":            None,
        "review_count":      None,
        "editorial_summary": None,
        "reviews":           [],
        "note":              "No matching place found in nearby area",
    }

    async with httpx.AsyncClient(timeout=15.0) as client:
        place_id = None
        matched_name = None
        matched_query_type = None
        place_types: list = []

        # ── Search 1: address text search (always) ────────────────────────────
        # Google's own 'apartment_complex' type is the authoritative building
        # classifier — more reliable than OSM tags. One call gets both the
        # place_id and the types; place_types is stored in the enrichment result
        # so callers can derive building_type without a second API call.
        #
        # For apartment-like buildings, append "apartments" so Google resolves
        # the named complex rather than a raw street premise. We pin to
        # location+radius=500 so only things at the actual address come back.
        _APT_TYPES = {"Apartment Complex", "Apartment / Shopping Complex"}
        # Street number extracted for address-match guard (e.g. "5959" from "5959 Broadway")
        _addr_parts = address.strip().split()
        _street_num = _addr_parts[0] if _addr_parts and _addr_parts[0].isdigit() else ""
        # Types that indicate the result is clearly NOT a residential building —
        # used to reject false positives when accepting on street-number match alone.
        _NON_RESIDENTIAL = {
            "food", "restaurant", "cafe", "bar", "bakery",
            "store", "shopping_mall", "clothing_store", "grocery_or_supermarket",
            "school", "university", "hospital", "gym", "gas_station", "parking",
        }
        try:
            query_suffix = " apartments" if building_type in _APT_TYPES else ""
            params: dict = {"query": f"{address}{query_suffix}, {city}, {state}", "key": api_key}
            if lat is not None and lon is not None:
                params.update({"location": f"{lat},{lon}", "radius": 500})
            r = await client.get(f"{base}/textsearch/json", params=params)
            results = r.json().get("results", [])
            if results:
                c       = results[0]
                c_types = set(c.get("types", []))
                c_name  = c.get("name", "")
                is_google_apartment = "apartment_complex" in c_types
                has_useful_type     = bool(_ACCEPT_TYPES & c_types) and not (c_types & _SKIP_TYPES)
                is_non_residential  = bool(c_types & _NON_RESIDENTIAL)
                name_matches        = _company_name_matches(company, c_name)
                result_addr         = (c.get("formatted_address") or "").lower()
                street_num_ok       = not _street_num or _street_num in result_addr

                # apt_ok: we searched "{address} apartments" with a 500 m pin,
                # result is at the right street number, and it's not obviously a
                # restaurant/store/school — street-number match is sufficient here
                # because Google doesn't always tag residential buildings as
                # apartment_complex even when they clearly are.
                apt_ok   = (building_type in _APT_TYPES and _street_num
                            and street_num_ok and has_useful_type and not is_non_residential)
                other_ok = name_matches or (is_google_apartment and street_num_ok)
                if apt_ok or (other_ok and has_useful_type):
                    place_id           = c["place_id"]
                    matched_name       = c_name
                    matched_query_type = "address"
                    place_types        = sorted(c_types)
                    print(f"Google Places: '{matched_name}' via address search (types={place_types})")
        except Exception as e:
            print(f"Google Text Search (address) error: {e}")

        # ── Search 1b: apartment retry when building type was unknown ────────────
        # OSM often lacks building tags for dense urban addresses (e.g. NYC), so
        # building_type may be "Unknown" even for a clear apartment building. If the
        # plain address search found nothing, try again with the "apartments" suffix
        # and accept on street-number match + non-residential type check.
        if not place_id and _street_num and building_type not in _APT_TYPES:
            try:
                params = {"query": f"{address} apartments, {city}, {state}", "key": api_key}
                if lat is not None and lon is not None:
                    params.update({"location": f"{lat},{lon}", "radius": 500})
                r = await client.get(f"{base}/textsearch/json", params=params)
                results = r.json().get("results", [])
                if results:
                    c       = results[0]
                    c_types = set(c.get("types", []))
                    c_name  = c.get("name", "")
                    has_useful_type    = bool(_ACCEPT_TYPES & c_types) and not (c_types & _SKIP_TYPES)
                    is_non_residential = bool(c_types & _NON_RESIDENTIAL)
                    result_addr        = (c.get("formatted_address") or "").lower()
                    if has_useful_type and not is_non_residential and _street_num in result_addr:
                        place_id           = c["place_id"]
                        matched_name       = c_name
                        matched_query_type = "address"
                        place_types        = sorted(c_types)
                        print(f"Google Places: '{matched_name}' via apt retry (types={place_types})")
            except Exception as e:
                print(f"Google Text Search (apt retry) error: {e}")

        # ── Search 2: company name fallback ───────────────────────────────────
        # Runs whenever the address search found nothing useful.
        if not place_id:
            try:
                params = {"query": f"{company} {city} {state}", "key": api_key}
                params.update(location_params)
                r = await client.get(f"{base}/textsearch/json", params=params)
                results = r.json().get("results", [])
                if results:
                    c_name = results[0].get("name", "")
                    if _company_name_matches(company, c_name):
                        place_id           = results[0]["place_id"]
                        matched_name       = c_name
                        matched_query_type = "company"
                        place_types        = sorted(results[0].get("types", []))
                        print(f"Google Places: '{matched_name}' via company search")
                    else:
                        print(f"Google Places: '{c_name}' doesn't match company '{company}', skipping")
            except Exception as e:
                print(f"Google Text Search (company) error: {e}")

        if not place_id:
            return _no_match_result

        # ── Place Details ─────────────────────────────────────────────────────
        try:
            r = await client.get(
                f"{base}/details/json",
                params={
                    "place_id": place_id,
                    "fields": "name,rating,user_ratings_total,reviews,editorial_summary",
                    "key": api_key,
                },
            )
            detail = r.json().get("result", {})
        except Exception as e:
            print(f"Google Place Details error: {e}")
            return {"error": "Details fetch failed"}

    raw_reviews = detail.get("reviews", [])
    reviews = [
        {
            "author":   rv.get("author_name", "Anonymous"),
            "rating":   rv.get("rating", 0),
            "time":     rv.get("relative_time_description", ""),
            "text":     (rv.get("text") or "").strip()[:300],
        }
        for rv in raw_reviews[:5]
    ]

    editorial_summary = (detail.get("editorial_summary") or {}).get("overview") or None

    return {
        "place_name":        detail.get("name", matched_name),
        "matched_via":       matched_query_type,
        "place_types":       place_types,
        "rating":            detail.get("rating"),
        "review_count":      detail.get("user_ratings_total"),
        "editorial_summary": editorial_summary,
        "reviews":           reviews,
    }

async def get_climate_data(lat: float, lon: float) -> Dict[str, Any]:
    async with httpx.AsyncClient(timeout=15.0) as client:
        try:
            params = {
                "latitude": lat,
                "longitude": lon,
                "start_date": "2024-01-01",
                "end_date": "2024-12-31",
                "daily": [
                    "temperature_2m_max",
                    "temperature_2m_min",
                    "precipitation_sum",
                    "snowfall_sum",
                    "precipitation_hours",
                ],
                "timezone": "auto",
            }
            r = await client.get("https://archive-api.open-meteo.com/v1/archive", params=params)
            if r.status_code == 200:
                data = r.json().get("daily", {})
                if data:
                    precip_hours = data.get("precipitation_hours", [])
                    snowfall     = data.get("snowfall_sum", [])
                    precip       = data.get("precipitation_sum", [])
                    tmax_clean   = [x for x in data.get("temperature_2m_max", []) if x is not None]
                    tmin_clean   = [x for x in data.get("temperature_2m_min", []) if x is not None]
                    return {
                        "annual_precip_days":      sum(1 for x in precip_hours if x is not None and x > 0),
                        "annual_snowfall_cm":      round(sum(x for x in snowfall if x is not None), 1),
                        "annual_precipitation_mm": round(sum(x for x in precip if x is not None), 1),
                        "hottest_day_c":           round(max(tmax_clean), 1) if tmax_clean else "N/A",
                        "coldest_day_c":           round(min(tmin_clean), 1) if tmin_clean else "N/A",
                    }
        except Exception as e:
            print(f"Climate API error: {e}")
    return {}

async def get_crime_data(city: str, state: str) -> Dict[str, Any]:
    fbi_api_key = os.getenv("FBI_API_KEY")
    if not fbi_api_key:
        return {"error": "FBI_API_KEY not set"}

    if not _ORI_LOOKUP_PATH.exists():
        return {"error": "ORI lookup CSV not found — run build_ori_lookup() once to generate it."}

    ori = city_to_ori(city, state)
    if not ori:
        return {"error": f"No ORI found for {city}, {state}"}

    params = {"from": "01-2020", "to": "12-2025", "API_KEY": fbi_api_key}
    base_url = "https://api.usa.gov/crime/fbi/cde/summarized/agency"

    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            rv = await client.get(f"{base_url}/{ori}/violent-crime", params=params)
            rp = await client.get(f"{base_url}/{ori}/property-crime", params=params)
            if rv.status_code != 200:
                return {"error": f"FBI API returned {rv.status_code}: {rv.text[:200]}"}
            violent_data   = rv.json()
            property_data  = rp.json() if rp.status_code == 200 else {}
        except Exception as e:
            return {"error": str(e)}

    def _pick_agency_key(rates_by_entity: dict, city: str) -> str | None:
        city_lower = city.lower()
        # Prefer: key contains city name, has "Offenses", not "Clearances"
        for k in rates_by_entity:
            if "Offenses" in k and "Clearances" not in k and city_lower in k.lower():
                return k
        
        # Fallback: exclude US-level and state-level keys
        state_name = FULL_STATE_NAMES.get(state, "").replace("_", " ")
        for k in rates_by_entity:
            if "Offenses" in k and "Clearances" not in k:
                if "United States" not in k and state_name.lower() not in k.lower():
                    return k
        return None

    def _annual_rate(rates_by_entity: dict, city: str) -> tuple[float | None, int | None]:
        key = _pick_agency_key(rates_by_entity, city)
        if not key:
            return None, None
        monthly = rates_by_entity[key]
        years = sorted({k.split("-")[1] for k in monthly}, reverse=True)
        for yr in years:
            vals = [v for k, v in monthly.items() if k.endswith(f"-{yr}") and v is not None]
            if len(vals) >= 12:
                return round(sum(vals), 1), int(yr)
        return None, None

    violent_rates  = violent_data.get("offenses", {}).get("rates", {})
    property_rates = property_data.get("offenses", {}).get("rates", {})

    violent_annual, data_year     = _annual_rate(violent_rates, city)
    property_annual, prop_year    = _annual_rate(property_rates, city)

    if violent_annual is None and property_annual is None:
        return {"error": "No agency offense rate data in response"}

    national_avg_violent  = 380
    national_avg_property = 2110

    def _crime_score(rate: float, national_avg: float) -> float:
        # Below average: linear 1.0 → 5.0
        if rate <= national_avg:
            return 1.0 + (rate / national_avg) * 4.0
        # Above average: sqrt curve 5.0 → 15.0, saturating at 3× national avg
        excess = rate - national_avg
        normalized = min(1.0, excess / (2.0 * national_avg))
        return 5.0 + 10.0 * (normalized ** 0.5)

    score_v = _crime_score(violent_annual, national_avg_violent) if violent_annual is not None else None
    score_p = _crime_score(property_annual, national_avg_property) if property_annual is not None else None

    if score_v is not None and score_p is not None:
        score = round(0.6 * score_v + 0.4 * score_p, 1)
    elif score_v is not None:
        score = round(score_v, 1)
    else:
        score = round(score_p, 1)

    result = {
        "city":                           city,
        "state":                          state,
        "ori":                            ori,
        "violent_crime_rate_per_100k":    violent_annual,
        "national_avg_violent_per_100k":  national_avg_violent,
        "above_national_avg_violent":     violent_annual > national_avg_violent,
        "crime_score":                    score,
        "data_year":                      data_year,
        "source":                         "FBI CDE",
    }
    if score_v is not None:
        result["violent_crime_score"] = round(score_v, 1)
    if property_annual is not None:
        result["property_crime_rate_per_100k"]   = property_annual
        result["national_avg_property_per_100k"] = national_avg_property
        result["above_national_avg_property"]    = property_annual > national_avg_property
        result["property_data_year"]             = prop_year
    if score_p is not None:
        result["property_crime_score"] = round(score_p, 1)
    return result


async def get_osm_data(address: str, city: str, state: str, lat: float, lon: float) -> Dict[str, Any]:
    import math

    result = {
        "osm_type": "N/A", "osm_class": "N/A", "display_name": "N/A",
        "lat": str(lat), "lon": str(lon), "boundingbox": "N/A", "osm_id": "N/A",
        "building_details": {},
        "amenities_1000m": {}
    }
    query_lat, query_lon = lat, lon
    osm_type, osm_id = "node", None

    async with httpx.AsyncClient(timeout=20.0) as client:

        # ── Step 1a: Nominatim structured forward search ───────────────────────
        # Returns exact OSM object + precise parcel centroid when the address
        # exists in OSM (more accurate than Census street interpolation).
        _structured_hit = None
        try:
            r = await client.get(
                "https://nominatim.openstreetmap.org/search",
                headers=_OSM_HEADERS,
                params={"street": address, "city": city, "state": state,
                        "country": "US", "format": "json", "limit": 1},
            )
            if r.status_code == 200:
                hits = r.json()
                if hits:
                    _structured_hit = hits[0]
        except Exception as e:
            print(f"Nominatim structured search error: {e}")

        # If the structured result is only a road segment, try freeform first —
        # it resolves house numbers to the actual building polygon.
        _freeform_hit = None
        if not _structured_hit or _structured_hit.get("class") == "highway":
            try:
                r = await client.get(
                    "https://nominatim.openstreetmap.org/search",
                    headers=_OSM_HEADERS,
                    params={"q": f"{address}, {city}, {state}", "format": "json", "limit": 1},
                )
                if r.status_code == 200:
                    hits = r.json()
                    if hits:
                        _freeform_hit = hits[0]
            except Exception as e:
                print(f"Nominatim freeform search error: {e}")

        # Pick the best hit: prefer non-highway over highway
        _best = _freeform_hit or _structured_hit
        if _best:
            hit = _best
            query_lat = float(hit["lat"])
            query_lon = float(hit["lon"])
            result["lat"]          = hit["lat"]
            result["lon"]          = hit["lon"]
            result["osm_type"]     = hit.get("type", "N/A")
            result["osm_class"]    = hit.get("class", "N/A")
            result["display_name"] = hit.get("display_name", "N/A")
            result["boundingbox"]  = hit.get("boundingbox", "N/A")
            osm_type = hit.get("osm_type", "node").lower()
            # Discard the osm_id when Nominatim resolved to a road segment — the
            # geometry we'd fetch is a polyline, not a building polygon. The radius
            # search in Step 2b will find the actual building at these coordinates.
            if hit.get("class") == "highway":
                osm_id = None
            else:
                osm_id = hit.get("osm_id")
            if osm_id:
                result["osm_id"] = f"{osm_type}/{osm_id}"
            src = "freeform" if hit is _freeform_hit else "structured"
            print(f"Nominatim forward ({src}): {result['display_name']} at {query_lat},{query_lon}")

        # ── Step 1b: Reverse geocode fallback at Census/Intellipins coords ─────────────────
        # Used when the address isn't in OSM as a named object.
        # Does not update query_lat/query_lon — Census coords stay for radius queries.
        if not osm_id:
            try:
                r = await client.get(
                    "https://nominatim.openstreetmap.org/reverse",
                    headers=_OSM_HEADERS,
                    params={"lat": lat, "lon": lon, "format": "json", "zoom": 18},
                )
                if r.status_code == 200:
                    rev = r.json()
                    result["osm_type"]     = rev.get("type", "N/A")
                    result["osm_class"]    = rev.get("class", "N/A")
                    result["display_name"] = rev.get("display_name", "N/A")
                    result["boundingbox"]  = rev.get("boundingbox", "N/A")
                    osm_type = rev.get("osm_type", "node").lower()
                    osm_id   = rev.get("osm_id")
                    if osm_id:
                        result["osm_id"] = f"{osm_type}/{osm_id}"
                    print(f"Nominatim reverse: {result['display_name']} ({result['osm_id']})")
            except Exception as e:
                print(f"Nominatim reverse geocode error: {e}")

        # ── Step 2a: Fetch geometry for the specific OSM way/relation ──────────
        # A way or relation can carry polygon geometry; a node cannot.
        building_el = None
        if osm_id and osm_type in ("way", "relation"):
            try:
                r = await client.get(
                    "https://overpass-api.de/api/interpreter",
                    headers=_OSM_HEADERS,
                    params={"data": f"[out:json];{osm_type}({osm_id});out geom;"},
                )
                if r.status_code == 200:
                    els = r.json().get("elements", [])
                    if els:
                        el   = els[0]
                        geom = el.get("geometry", [])
                        if not geom and el.get("type") == "relation":
                            for m in el.get("members", []):
                                if m.get("role") == "outer" and "geometry" in m:
                                    geom = m["geometry"]
                                    break
                        # Require a building tag — prevents road ways or park
                        # boundaries from being accepted as building geometry.
                        if len(geom) >= 3 and el.get("tags", {}).get("building"):
                            building_el = el
                            print(f"OSM ID geometry found: {osm_type}/{osm_id}")
            except Exception as e:
                print(f"Overpass osm_id lookup error: {e}")

        # ── Step 2b: Radius fallback — nearest way/relation tagged building=* ──
        # Runs when the osm_id has no polygon (it's a node or untagged way),
        # or when no osm_id was found at all.
        def _closest_element(els: list, lat: float, lon: float) -> dict | None:
            def _element_center(el: dict) -> tuple[float, float] | None:
                geom = el.get("geometry", [])
                if geom and len(geom) > 0:
                    first = geom[0]
                    return float(first.get("lat", 0)), float(first.get("lon", 0))
                return None
            closest, min_dist = None, float("inf")
            for el in els:
                center = _element_center(el)
                if center:
                    dlat, dlon = center[0] - lat, center[1] - lon
                    dist_m = (dlat ** 2 + dlon ** 2) ** 0.5 * 111139
                    if dist_m < min_dist:
                        min_dist, closest = dist_m, el
            return closest

        if not building_el:
            for radius in (30, 80, 200):
                q = (
                    f"[out:json];"
                    f"(way[\"building\"](around:{radius},{query_lat},{query_lon});"
                    f"relation[\"building\"](around:{radius},{query_lat},{query_lon}););"
                    f"out geom;"
                )
                try:
                    op = await client.get(
                        "https://overpass-api.de/api/interpreter",
                        params={"data": q}, headers=_OSM_HEADERS,
                    )
                    if op.status_code == 200:
                        els = op.json().get("elements", [])
                        if els:
                            building_el = _closest_element(els, query_lat, query_lon)
                            if building_el:
                                b_type = building_el.get("type", "way")
                                b_id   = building_el.get("id")
                                if b_id:
                                    result["osm_id"] = f"{b_type}/{b_id}"
                                print(f"Nearest building found at radius={radius}m: {result['osm_id']}")
                                break
                except Exception as e:
                    print(f"Overpass radius building error (r={radius}m): {e}")
                    break

        # ── Step 3: Amenity counts within 1 km ───────────────────────────────
        amenity_q = f"""
        [out:json];
        (
          nwr["public_transport"](around:1000,{query_lat},{query_lon});
          nwr["highway"="bus_stop"](around:1000,{query_lat},{query_lon});
          nwr["railway"="station"](around:1000,{query_lat},{query_lon});
        )->.transit;
        .transit out count;
        (nwr["leisure"="park"](around:1000,{query_lat},{query_lon});)->.parks;
        .parks out count;
        (
          nwr["amenity"~"restaurant|cafe|fast_food|bar"](around:1000,{query_lat},{query_lon});
          nwr["shop"~"supermarket|convenience|mall|clothes|grocery"](around:1000,{query_lat},{query_lon});
        )->.retail;
        .retail out count;
        """
        try:
            op = await client.get(
                "https://overpass-api.de/api/interpreter",
                params={"data": amenity_q}, headers=_OSM_HEADERS,
            )
            if op.status_code == 200:
                count_els = [el for el in op.json().get("elements", []) if el.get("type") == "count"]
                if len(count_els) >= 3:
                    result["amenities_1000m"] = {
                        "transit": count_els[0].get("tags", {}).get("total", "0"),
                        "parks":   count_els[1].get("tags", {}).get("total", "0"),
                        "retail":  count_els[2].get("tags", {}).get("total", "0"),
                    }
        except Exception as e:
            print(f"Overpass amenities error: {e}")

        # ── Step 4: Parse building geometry ──────────────────────────────────
        if building_el:
            tags = building_el.get("tags", {})
            geom = building_el.get("geometry", [])
            if not geom and building_el.get("type") == "relation":
                for m in building_el.get("members", []):
                    if m.get("role") == "outer" and "geometry" in m:
                        geom = m["geometry"]
                        break

            area_sqft = "N/A"
            if geom and len(geom) >= 3:
                ref_lat   = geom[0].get("lat", 0)
                m_per_lat = 111139.0
                m_per_lon = 111139.0 * math.cos(math.radians(ref_lat))
                area_sqm  = 0.0
                for i in range(len(geom)):
                    p1 = geom[i]
                    p2 = geom[(i + 1) % len(geom)]
                    area_sqm += (p1.get("lon", 0) * m_per_lon) * (p2.get("lat", 0) * m_per_lat)
                    area_sqm -= (p2.get("lon", 0) * m_per_lon) * (p1.get("lat", 0) * m_per_lat)
                area_sqft = f"{int(abs(area_sqm) / 2.0 * 10.7639):,} sq ft"

            shapely_wkt = "N/A"
            if geom and len(geom) >= 3:
                try:
                    from shapely.geometry import Polygon
                    shapely_wkt = Polygon([(p.get("lon", 0), p.get("lat", 0)) for p in geom]).wkt
                except Exception as e:
                    print(f"Shapely error: {e}")

            result["building_details"] = {
                "building_type":   tags.get("building", "N/A"),
                "floors":          tags.get("building:levels", "N/A"),
                "units":           tags.get("building:units", "N/A"),
                "name":            tags.get("name", "N/A"),
                "operator":        tags.get("operator", "N/A"),
                "height":          tags.get("height", "N/A"),
                "calculated_area": area_sqft,
                "geometry_wkt":    shapely_wkt,
            }

    return result


# ---------------------------------------------------------------------------
# Null normalisation — replace N/A placeholder strings with None recursively
# ---------------------------------------------------------------------------

_NA_STRINGS = frozenset({
    "", "n/a", "na", "none", "null", "data unavailable", "unavailable",
    "-", "--", "not available", "no data", "walk score unavailable", "unknown",
})


def _nullify(obj: Any) -> Any:
    """Replace N/A / empty placeholder strings with None recursively."""
    if isinstance(obj, str) and obj.strip().lower() in _NA_STRINGS:
        return None
    if isinstance(obj, dict):
        return {k: _nullify(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_nullify(v) for v in obj]
    return obj


_ALL_APIS = {"census", "fred", "wikipedia", "news", "walkscore", "intellipins", "google", "osm", "open_meteo", "crime"}

async def enrich_lead(lead: Any) -> Dict[str, Any]:
    enabled = set(lead.enabled_apis) if lead.enabled_apis is not None else _ALL_APIS

    # Geocode once — Intellipins → Nominatim → Census.
    # _geocode_address returns the full Intellipins forward-geocode result when it
    # succeeds, so the parcel-lookup task can reuse it without a second API call.
    lat, lon, geo_source, ipins_geocode = await _geocode_address(
        lead.property_address, lead.city, lead.state
    )
    geocoords = {"lat": lat, "lon": lon, "source": geo_source} if lat is not None else {}

    # ── Phase 1: all APIs except Google ──────────────────────────────────
    # Google runs in phase 2 because its search strategy depends on building type,
    # which is derived from OSM + Intellipins results. OSM is already one of the
    # slowest tasks, so phase 2 adds zero wall-clock time to total pipeline time.
    phase1: Dict[str, Any] = {}
    _ipins_error: Dict[str, Any] | None = None

    if "census" in enabled:
        phase1["census"] = asyncio.create_task(get_census_data(lead.city, lead.state))
    if "fred" in enabled:
        phase1["fred"] = asyncio.create_task(get_fred_data(lead.city, lead.state))
    if "wikipedia" in enabled:
        phase1["wikipedia"] = asyncio.create_task(get_wikipedia_data(lead.company, lead.city, lead.state))
    if "news" in enabled:
        phase1["news"] = asyncio.create_task(get_news_data(lead.company, lead.city))
    if "walkscore" in enabled and lat is not None:
        phase1["walkscore"] = asyncio.create_task(get_walkscore_data(lead.property_address, lead.city, lead.state, lat, lon))
    if "intellipins" in enabled:
        if isinstance(ipins_geocode, dict):
            # Forward geocode already done — only run parcel lookup (no second API call)
            phase1["intellipins"] = asyncio.create_task(_intellipins_parcel_lookup(ipins_geocode))
        else:
            key_ok = bool(os.getenv("INTELLIPINS_KEY")) and "your_" not in (os.getenv("INTELLIPINS_KEY") or "")
            if ipins_geocode == "rate_limited":
                _ipins_error = {"error": "Rate limited — too many requests. Wait a minute and try again."}
            else:
                _ipins_error = {"error": "Key required" if not key_ok else "Geocode unavailable — check address"}
    if "osm" in enabled and lat is not None:
        phase1["osm"] = asyncio.create_task(get_osm_data(lead.property_address, lead.city, lead.state, lat, lon))
    if "open_meteo" in enabled and lat is not None:
        phase1["open_meteo"] = asyncio.create_task(get_climate_data(lat, lon))
    if "crime" in enabled:
        phase1["crime"] = asyncio.create_task(get_crime_data(lead.city, lead.state))

    enrichment: Dict[str, Any] = {}
    if phase1:
        p1_results = await asyncio.gather(*phase1.values(), return_exceptions=True)
        for key, result in zip(phase1.keys(), p1_results):
            enrichment[key] = result if not isinstance(result, Exception) else {}
    if _ipins_error is not None:
        enrichment["intellipins"] = _ipins_error

    # ── Derive building type (needed for Google search strategy) ─────────
    ipins_result = enrichment.get("intellipins", {})
    osm_result   = enrichment.get("osm", {})
    ipins_ok = isinstance(ipins_result, dict) and "_disabled" not in ipins_result and "error" not in ipins_result
    _osm_building_tag = (
        osm_result.get("building_details", {}).get("building_type")
        if isinstance(osm_result, dict) else None
    )
    _ws = enrichment.get("walkscore", {})
    _walk_score_val = _ws.get("walk_score") if isinstance(_ws, dict) else None
    _walk_score_num = _walk_score_val if isinstance(_walk_score_val, (int, float)) else None
    building_type = _classify_building_type(
        ipins_result.get("address_type") if ipins_ok else None,
        osm_result.get("osm_class") if isinstance(osm_result, dict) else None,
        osm_result.get("osm_type")  if isinstance(osm_result, dict) else None,
        osm_building_tag=_osm_building_tag,
        walk_score=_walk_score_num,
    )
    if ipins_ok:
        ipins_result["building_type"] = building_type

    # ── Phase 2: Google Places ────────────────────────────────────────────
    # Always searches by address first; Google's 'apartment_complex' type is
    # the authoritative classifier. place_types is stored in the enrichment
    # result so no second call is needed to determine building type.
    if "google" in enabled:
        enrichment["google"] = await get_google_places_data(
            lead.company, lead.property_address, lead.city, lead.state,
            building_type=building_type, lat=lat, lon=lon,
        )
        # Refine building_type from Google's authoritative place_types.
        google_result = enrichment["google"]
        if isinstance(google_result, dict) and "apartment_complex" in (google_result.get("place_types") or []):
            building_type = "Apartment Complex"
            if ipins_ok:
                ipins_result["building_type"] = "Apartment Complex"

    for api in _ALL_APIS - enabled:
        enrichment[api] = {"_disabled": True}

    return {
        "lead_info": {
            "name": lead.name,
            "email": lead.email,
            "company": lead.company,
            "address": lead.property_address,
            "city": lead.city,
            "state": lead.state
        },
        "enrichment": _nullify({
            "geocoords":  geocoords,
            "census":     enrichment.get("census", {}),
            "fred":       enrichment.get("fred", {}),
            "wikipedia":  enrichment.get("wikipedia", ""),
            "news":       enrichment.get("news", {}),
            "walkscore":    enrichment.get("walkscore", {}),
            "intellipins":  enrichment.get("intellipins", {}),
            "google":       enrichment.get("google", {}),
            "osm":        enrichment.get("osm", {}),
            "open_meteo": enrichment.get("open_meteo", {}),
            "crime":      enrichment.get("crime", {}),
        })
    }
