# EliseAI GTM Automation Tool — Business Overview

> **Audience:** CEO, Sales Leadership, Revenue stakeholders

---

## The Problem

A typical SDR prospecting a property management company has to do a lot of legwork before they can write a single personalized email. It looks something like this:

| Step | What they're doing | Time per lead |
|------|-------------------|---------------|
| Research the company | Google, LinkedIn, news searches | 10–15 min |
| Qualify the market | Is this a real rental market? Is there demand? | 5–10 min |
| Assess the property | Apartment complex or single-family home? How large? | 5–10 min |
| Write the email | Generic template, lightly personalized | 5–10 min |
| **Total** | | **25–45 min per lead** |

At 20 leads per day, that's most of the workday gone before anyone picks up the phone. And because it's expensive, SDRs naturally cherry-pick by instinct rather than data — a mid-size apartment complex in a tight Boston rental market gets the same treatment as a single-family home in a rural suburb. The signal is there; there's just no time to read it.

---

## What the Tool Does

You give it a prospect's name, company, and property address. In 30–60 seconds, it does the following:

1. **Looks up the property** — confirms coordinates, building type (apartment complex vs. office vs. SFR), physical footprint, and lot size from property data APIs.

2. **Reads the local market** — pulls Census data (population, renter share, median income), FRED vacancy rates, and WalkScore to understand the rental demand environment.

3. **Checks the weather and crime** — not because we care about the weather, but because harsh climates and high crime directly increase the operational burden on property managers (more maintenance calls, more tenant communication, more resident turnover). That's exactly where EliseAI creates value.

4. **Scans recent news** — finds company announcements (expansions, cost cuts, lawsuits) that signal whether the timing is right and what angle to lead with.

5. **Checks Google reviews** — a 2.8-star property with 80 reviews is practically telling you that residents are unhappy with communication. That's an EliseAI problem.

6. **Scores the lead** — generates four scores (Demand, Friction, Scale, Opportunity) and rolls them into a single 0–100 Lead Score with a grade (A through F).

7. **Names the pain** — identifies which operational problems this property likely has, ordered by severity.

8. **Writes the email** — selects one of five story arcs deterministically from scores and pain points (Reputation Gap, Operational Friction, Growth Strain, Premium Expectations, Lead Speed), then generates a cold outreach email grounded in the actual data points. Not "I noticed your company" — more like "Your 2.8-star Google rating in a 97 Walk Score neighborhood suggests your residents expect fast responses you can't currently deliver."

The SDR reviews the output, tweaks the email if needed, and sends. Total active time: under 5 minutes per lead.

---

## The Scoring Logic — How It Works and Why

The lead score is built from four independent sub-scores that each answer a different question. Here's what each one measures and why I weighted it the way I did.

---

### Demand Score — 30% of Lead Score
*"How overwhelmed is this property manager likely to be with inbound rental activity?"*

A tight rental market with a lot of renters and high walkability means constant inquiry volume. The property manager is fighting fires all day — which is exactly when automation is most valuable.

| Signal | Weight | Ceiling | Engineering Note |
|--------|--------|----------------------------|-----------------|
| Renter % of households | 25% | 50% renters | **Lifted**: High renter % is the baseline for target cities; we lift the mid-range to capture market depth. |
| Vacancy rate (inverted) | 20% | 0–10% vacancy | **Lifted**: Even moderate tightness (5%) is a high-intensity signal in the real world. |
| Walk Score | 15% | **Score of 80** | **Crushed (Convex)**: Ceiling set at "Very Walkable" (80) so any property at that threshold maxes out this component. Mediocre walk scores (50) still score near 0.39; car-dependent (<25) score near 0. |
| Transit Score | 10% | **Score of 75** | **Crushed (Convex)**: Ceiling set at "Excellent Transit" (75). Low transit access is a major disqualifier. |
| Median household income | 10% | $85k/year | **Lifted**: $85k is already a premium market. |
| Nearby amenities (1km radius) | 12% | 40 amenities | **Lifted**: Density indicators are capped at realistic "busy" levels. |
| Population | 8% | 250k | **Crushed (Convex)**: Small towns are heavily penalized to protect ICP focus. Uses city-level Census population. |

---

### Friction Score — 20% of Lead Score
*"How hard is it to operate this property, and does that difficulty make EliseAI more valuable?"*

A high Friction score signals operational stress — more maintenance calls, more tenant communication, more scheduling overhead. It's a supporting signal: it tells you *why* a manager needs automation, not *whether* they do. That's why Demand and Opportunity carry more weight. Friction still matters — it sharpens the email angle and explains the pain — but it's no longer the dominant factor.

**Important:** a high Friction score is a good thing for us. A 100/100 friction score means the property is maximally stressful to run and maximally in need of automation.

| Signal | Weight | Ceiling | Logic |
|--------|--------|----------------------------|-----------------|
| Crime score (1–15) | 25% | Score of 15 | **Crushed**: Low crime areas score near zero friction. |
| Precipitation days | 25% | 120 days/year | **Crushed**: Very high precip (184+ days) maxes out. Mild weather scores near zero. |
| Annual snowfall | 20% | 80 cm/year | **Lifted**: Snowfall is an indicator signal — any meaningful snow already signals friction. Moderate NYC snowfall (38 cm) should score ~60, not near zero. |
| Temp range | 20% | 55°C swing | **Crushed**: Infrastructure stress proxy. Wide swings are aggressively rewarded. |
| Elevation | 10% | 800m | **Crushed**: Harsh winter proxy. |

---

### Scale Score — 20% of Lead Score
*"How big is the operational footprint? More units = more automation leverage."*

A 400-unit apartment complex in Seattle and a single-family rental in rural Montana are not the same opportunity. This score captures that difference.

| Signal | Weight | Ceiling | Engineering Note |
|--------|--------|----------------------------|-----------------|
| Building type | 30% | Apartment Complex | **Categorical**: Apartment Complex = 100%; SFH = 20%. |
| Building footprint | 25% | 40,000 sq ft | **Crushed**: Small buildings score near zero. |
| Lot area | 20% | 100,000 sq ft | **Lifted**: Mid-size parcels represent significant scale. |
| Floors | 15% | 15 floors | **Crushed**: 1-2 floor buildings are aggressively penalized. |
| Unit count | 10% | 250 units | **Crushed**: Direct scale proxy. |

**Building type scores used in calculation:**

| Building Type | Score |
|---------------|-------|
| Apartment Complex | 1.00 |
| Hotel | 0.80 |
| Commercial / Industrial | 0.75 |
| Office Building | 0.70 |
| Apartment / Shopping Complex | 0.65 |
| Shopping Complex / Amenity | 0.55 |
| Retail / Shopping | 0.45 |
| Single Family Housing | 0.20 |
| Unknown | 0.20 |

---

### Opportunity Score — 30% of Lead Score
*"Is there a specific trigger or opening that makes this company likely to act now?"*

This sub-score captures behavioral and reputational signals that demand doesn't — things that tell you whether a company is ready to act, not just whether the market is right. Renter %, vacancy, and walkability are intentionally excluded here (they already appear in Demand) to avoid double-counting.

| Signal | Weight | Ceiling / Trigger | Why I chose this |
|--------|--------|--------------|-----------------|
| News sentiment | 54% | Growth → 0.95 | **Decisive Floor**: Growth news is a primary trigger for Grade A prioritization. |
| Low Google rating | 31% | 1 star → 1.0 | **Lifted** (linear then `_lift`): Rating pain is an indicator signal. A 3.0-star rating should score ~55, not ~43 — moderate bad reviews already signal real pain. |
| Wikipedia presence | 15% | Page found = 0.90 | **High Floor**: Established account indicator. |

---

### The Engineering Defense: High-Dynamic-Range Scoring

In multi-layered scoring systems, "double-averaging" naturally pulls leads into a narrow 50–65 band. To solve this and ensure clear prioritization, we employ a **Three-Part Calibration Strategy**:

1.  **Ceiling Calibration**: Ceilings are set at realistic "strong" values, not theoretical maximums. Walk score ceiling is 80 (not 100) — a score of 84 is "Very Walkable" and should max out the component. Transit ceiling is 75 ("Excellent Transit"). This prevents great urban properties from being silently penalized against a ceiling no US property ever reaches.
2.  **Concave Lifting (_lift, power 0.70)**: Applied to "indicator" signals — renter share, vacancy, snowfall, low Google rating, vacancy urgency. These are signals where moderate values already represent meaningful market intent. Lifting them ensures quality mid-range signals push leads into the 65–85+ range.
3.  **Aggressive Convex Penalization (_crush, power 2.0)**: Applied to "structural" filters — Walk Score, Population, Building Footprint. These are pass/fail signals. A 50 Walk Score should score 0.25, not 0.50. This pushes weak leads below the 50 mark.
4.  **Decisive Opportunity Floors**: High floors (e.g. 0.95 for growth news) for qualitative triggers ensure a single strong sales opening can override mediocre structural data.

The result is a **High-Dynamic-Range Score** (spread of ~65 points) that makes automated prioritization meaningful.

---

### The Final Number

```
Lead Score = (Demand × 0.30) + (Friction × 0.20) + (Scale × 0.20) + (Opportunity × 0.30)
```

| Grade | Score | What to do |
|-------|-------|------------|
| A | 80–100 | Strong ICP match. Route to AE immediately. |
| B | 65–79 | Good fit. High-priority outreach. |
| C | 50–64 | Qualified but not urgent. Standard sequence. |
| D | 35–49 | Weak fit. Low-touch or hold. |
| F | 0–34 | Not ICP. Skip. |

**One thing worth noting about missing data:** sub-scores are weighted in the composite proportionally to their `available_weight`. A sub-score with sparse data contributes less to the final number rather than being dropped or dragging the score down. This also prevents a sub-score that only has weak overlap signals from claiming its full composite weight.

---

## What Good and Bad Leads Look Like in Practice

These are real pipeline runs from the test dataset — actual API responses, actual scores, actual generated emails.

---

### Grade A — 84/100 · Christopher Gonzalez · Inland American Real Estate · Chicago, IL

**Property:** 40 E Oak St, Gold Coast — 20-floor apartment complex

**What the data showed:**

| Signal | Value | What it means |
|--------|-------|---------------|
| Walk Score | **99** — Walker's Paradise | Every amenity within walking distance; inquiry volume is relentless |
| Transit Score | **92** — Rider's Paradise | Tenants move in and out constantly; turnover is high |
| Renter share | **54.4%** | Majority-renter city; the ICP market is there |
| Population | **2,742,119** | Third-largest US city; no scale concern |
| Annual snowfall | **62.7 cm** | Heavy Chicago winters; maintenance coordination load is real |
| Precipitation days | **178 days/yr** | Nearly half the year brings a weather event requiring tenant comms |
| Temperature swing | **-24°C to 35.7°C** | 60°C range; infrastructure stress year-round |
| Vacancy rate | **5.7%** | Tight market; every missed inquiry costs a lease |

**Scores:** Demand **89.4** · Friction **89.7** · Scale **100** · Opportunity **21.9** → **Lead Score: 81.1 — Grade A**

**Pain points identified:**
- [HIGH] Core ICP — Multifamily Property: Apartment complex, EliseAI's primary target
- [HIGH] High Lead Volume Overload: Walk Score 99 drives constant inquiry volume; manual handling loses leases
- [HIGH] Harsh Operating Conditions: 62.7 cm snow + 178 rain days = continuous maintenance communication burden
- [MEDIUM] High Tenant Mobility: Transit Score 92 in a 54% renter market means high turnover and a full inquiry pipeline at all times

**Generated email** *(arc: operational\_friction)*

> **Subject:** Midnight Maintenance Calls
>
> Your team deals with around 2 feet of snow and ~178 rainy days per year, which means constant maintenance issues. This creates a reactive environment where your team is always on call to fix something. Your building's temperature can drop to -12°F, putting a strain on your maintenance team.
>
> At Inland American Real Estate, a burst pipe during a cold snap can lead to a flooded lobby and numerous resident calls, taking your team away from the actual fix. EliseAI keeps residents informed automatically so your team can focus on the fix, not the calls.
>
> Worth a call?

**Why this is right:** Every EliseAI use case applies here — leasing automation (99 Walk Score drives constant inquiries), maintenance coordination (Chicago winters), and tenant communication at scale (20-floor building). Opportunity scores low (21.9) because there's no news trigger, no Wikipedia page, and a decent Google rating (4.1★) — no behavioral signal to act on right now. The Demand and Scale scores alone are enough to push it into Grade A.

---

### Grade B — 79/100 · Anna Miller · Kairoi Residential · New York, NY

**Property:** 152 E 81st St, Upper East Side

**What the data showed:**

| Signal | Value | What it means |
|--------|-------|---------------|
| Walk Score | **84** — Very Walkable | Urban core; renters have options and high expectations |
| Transit Score | **83** — Excellent Transit | High turnover; constant new-inquiry volume |
| Renter share | **66.8%** | Highest in the dataset; NYC is a renter's market |
| Population | **8,736,047** | Largest US city; market depth is unlimited |
| Google rating | **3.0★ / 120 reviews** | The pain signal — at scale, poor ratings are a documented service failure |
| Sample review | *"I called at 2am for an emergency alarm going off and the staff told me they would tell maintenance in the morning. I had to call the fire department."* | This is exactly the problem EliseAI solves |
| Precipitation days | **184 days/yr** | Constant weather-driven maintenance coordination |

**Scores:** Demand **90.6** · Friction **81.0** · Scale **65** · Opportunity **55.3** → **Lead Score: 79.7 — Grade B**

**Pain points identified:**
- [HIGH] High Lead Volume Overload: NYC density + 83 transit score = relentless inquiry volume
- [HIGH] Harsh Operating Conditions: 184 rain days/yr — highest in the dataset
- [HIGH] Resident Experience Issues: 3.0★ across 120 reviews reflects documented slow response and unresolved maintenance
- [MEDIUM] High Tenant Mobility: Transit 83 in a 67%-renter city means high churn and a full leasing pipeline

**Generated email** *(arc: reputation\_gap)*

> **Subject:** Your Google Rating
>
> Your Google rating is 3 out of 5, which signals to a prospective renter that your team may have slow maintenance response and poor communication before they ever call. This can make a big difference in whether they choose your building. You're potentially losing renters due to this perception.
>
> At Kairoi Residential, a maintenance request like the one from a resident who called at 2:00am for an emergency alarm can go unacknowledged for days, leading to a frustrated review. EliseAI provides instant ticket acknowledgment and 24/7 automated tenant updates.
>
> Worth a call?

**Why this is right:** The 3.0★ Google rating across 120 reviews is the story. The pipeline correctly identified this as a reputation gap and pulled the exact type of review (2am emergency ignored) to anchor the email. High-priority outreach.

---

### Grade C — 59/100 · Joyce Reyes · MAA · Orem, UT

**Property:** 1633 S Main St, Orem

**What the data showed:**

| Signal | Value | What it means |
|--------|-------|---------------|
| Walk Score | **45** — Car-Dependent | Structurally penalized (crushed scoring); low walkability = lower inquiry volume |
| Transit Score | **43** — Some Transit | Weak transit access; further penalizes demand |
| Renter share | **39.5%** | Below the 50% ceiling; thinner market than ICP target cities |
| Population | **96,734** | Small city; demand score crushed vs. 250k ceiling |
| Annual snowfall | **251 cm/yr** | Highest in the dataset — over 8 feet of snow |
| Precipitation days | **149 days/yr** | Heavy weather maintenance load despite small city |
| Building type | **Single Family Housing** | Type score 0.20; not EliseAI's primary ICP |
| Google rating | Not found | No Google Places listing — opportunity score runs without rating signal |

**Scores:** Demand **58.6** · Friction **73.1** · Scale **34.7** · Opportunity **0** → **Lead Score: 57.5 — Grade C**

**Pain points identified:**
- [HIGH] Harsh Weather Conditions Impact: 251 cm of snow (8+ feet) and 149 rain days creates a real maintenance coordination burden — the single strongest signal here
- [MEDIUM] Harsh Operating Conditions: Frequent precip + temp swings; meaningful but not decisive without market depth behind it
- [MEDIUM] Limited Access to Public Transport: Transit Score 43 limits tenant pool and signals a lower-demand rental environment

**Generated email** *(arc: operational\_friction)*

> **Subject:** Rainy Days and Repair Calls
>
> Your team deals with around 149 rainy days and 8 feet of snow each year, which keeps your maintenance crew on their toes. This means they're always reacting to something — a leaky roof or a frozen pipe. Your building needs constant attention, and that's just the weather.
>
> At MAA, a burst pipe during a cold snap can turn into a flooded lobby and a barrage of resident calls. EliseAI keeps residents informed automatically so the team can focus on the fix, not the calls.
>
> Worth a call?

**Why this is right:** The score is honest about the tension. The friction signal is genuinely strong (8 feet of snow is real operational pain), but the small-city population and SFH building type cap the ceiling. Opportunity scores 0 because there's no Google listing, no news hits, and no Wikipedia page — no behavioral signal available. Standard sequence — worth reaching out, but not a priority over Grade A/B leads.

---

### Grade D — 49.9/100 · Tyler Morales · Scottsdale Property Group · Scottsdale, AZ

**Property:** 6839 E Montecito Ave — Single-family house

**What the data showed:**

| Signal | Value | What it means |
|--------|-------|---------------|
| Walk Score | **69** — Somewhat Walkable | Decent, but well below the 80 "Very Walkable" ceiling |
| Transit Score | **46** — Some Transit | Weak transit; structurally penalized |
| Renter share | **33.4%** | Below 50% ceiling; owner-majority market |
| Building type | **Single Family Housing** | Type score 0.20; fundamentally wrong ICP |
| Building footprint | **3,686 sq ft** | Tiny; Scale score near zero for structural signals |
| Annual snowfall | **0.3 cm** | Scottsdale is sunny and dry; near-zero friction |
| Precipitation days | **49 days/yr** | Easy climate to operate in — the opposite of a friction trigger |
| Google rating | **4.8★ / 100 reviews** | Residents are happy. No pain signal to sell into. |

**Scores:** Demand **68.6** · Friction **39.1** · Scale **34.9** · Opportunity **0** → **Lead Score: 44.9 — Grade D**

**Pain points identified:** Only two LLM-generated pain points were identified — both marginal. The 8.4% vacancy rate generated a revenue-loss estimate, and the thin renter percentage generated a communication efficiency concern. Neither is grounded in operational pain.

**Generated email** *(arc: lead\_speed)*

> **Subject:** Units sitting empty this week
>
> Your vacancy rate is around 8%. In Scottsdale, renters make quick decisions, often shopping multiple properties at once. Prospects are 33.4% of the population, and they're moving fast.
>
> At Scottsdale Property Group, a prospect who submits at 9pm and doesn't hear back until the next morning often signs a lease somewhere else. EliseAI responds instantly, 24/7, so no lead goes cold.
>
> Worth a call?

**Why this is right — and what it tells you:** The 4.8-star Google rating is the tell. A manager with 100 happy reviews in a sunny climate with a small footprint is running their operation well without automation. Opportunity scores 0 — the 4.8★ rating produces near-zero low_rating signal, and there's no news or Wikipedia presence. There's no pain to sell into. Skip.

---

## Where Not to Trust the Output

Sales leadership needs to know where this tool's blind spots are.

| What you might see | Why it happens | What to do |
|--------------------|---------------|------------|
| **Vacancy rate is state-level** | FRED doesn't publish city-level vacancy consistently | Treat it as a market signal, not a property-specific measurement |
| **No unit count for most properties** | OSM building tags rarely include unit counts; the scale score uses footprint as a proxy | When a lead is borderline, verify unit count manually before calling |
| **News is company-level, not property-level** | NewsAPI searches by company name | For large REITs, scan the news snippets yourself before using them in the email |
| **Google Places may match the wrong listing** | The tool searches by address first, then company name; for large companies, it may match a corporate office | Check `matched_via` in the output — if it says `company`, verify the rating is for a property, not an office |
| **Crime data missing for some cities** | FBI data is by police agency; small towns without their own PD may have no data | When crime is missing, friction runs on weather only — still valid |
| **Each lead is scored on one address** | The tool is not portfolio-aware | For enterprise accounts, enter the most prominent property and lean on company-level signals |
| **The email is a draft** | Claude Sonnet or Groq llama-3.3-70b generates it from real data, but tone is a starting point | Always read the email before sending. The pain point evidence is real; the language isn't final |
| **Data is not real-time** | Census is 2021 ACS; climate is 2024 archive; crime is typically 1–2 years behind | Use for directional assessment; supplement with Zillow or CoStar for deals where freshness matters |

---

## What We'd Build Next

| Priority | Feature | Why it matters |
|----------|---------|----------------|
| **High** | **Portfolio-level scoring** — upload a CSV of 50 properties for one company | Enables enterprise account prioritization, not just single-address scoring |
| **High** | **CRM integration (Salesforce / HubSpot)** — auto-push scored leads, auto-update on refresh | Eliminates the CSV handoff and keeps data current |
| **High** | **City-level vacancy via Zillow or CoStar** | Replaces state-level FRED proxy with actual local market data |
| **Medium** | **Explicit unit count lookup** via CoStar or county assessor | Makes scale score significantly more precise |
| **Medium** | **Sequence integration** — auto-add Grade A/B leads to Outreach.io with the email pre-loaded | Reduces SDR active time from 5 min to under 1 min per lead |
| **Medium** | **Score refresh on trigger** — re-score automatically when a news event fires or Google rating changes | Keeps the lead list fresh without re-running manually |
| **Low** | **Competitive signal detection** — flag when a company is already on Yardi, RealPage, or Entrata | Adjusts the email angle from "here's a new tool" to "here's why to switch" |
| **Low** | **Multi-language support** | Expands serviceable markets in Miami, LA, and Houston |
