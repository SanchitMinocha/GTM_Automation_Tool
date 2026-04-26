# EliseAI GTM Automation Tool — Business Overview

> **Audience:** CEO, Sales Leadership, Revenue stakeholders
> **Purpose:** Understand the problem this tool solves, how it thinks, and why you can trust its outputs.

---

## 1. The Problem: What SDRs Do Today (and How Long It Takes)

A typical SDR prospecting a property management company does this manually:

| Step | Activity | Time per lead |
|------|----------|---------------|
| Research the company | Google, LinkedIn, news searches | 10–15 min |
| Qualify the market | Is this a real rental market? Is there demand? | 5–10 min |
| Assess the property | Apartment complex or single-family home? How large? | 5–10 min |
| Write the email | Generic template, lightly personalized | 5–10 min |
| **Total** | | **25–45 min per lead** |

At 20 leads per day, that's 8–15 hours — most of which is low-value lookup work, not selling.

The deeper problem: because it's expensive, SDRs cherry-pick leads by instinct rather than data. A mid-size apartment complex in a tight rental market in Boston gets the same treatment (or less) as a single-family home in a low-vacancy suburb. The signal is there; no one has time to read it.

---

## 2. What This Tool Does (Plain English)

The GTM Automation Tool takes a prospect's name, company, and property address and, in roughly 30–60 seconds, does the following:

1. **Looks up the property** — confirms coordinates, building type (apartment complex vs. office vs. SFR), physical footprint, and lot size using property data APIs.

2. **Reads the local market** — pulls Census data (population, renter share, median income), FRED vacancy rates, and WalkScore to understand the rental demand environment the property sits in.

3. **Checks the weather and crime** — not because we care about the weather, but because harsh climates and high crime directly increase the operational burden on property managers (more maintenance calls, more tenant communication, more resident turnover), which is exactly where EliseAI creates value.

4. **Scans recent news** — finds company announcements (expansions, cost cuts, lawsuits) that signal whether the timing is right and what angle to lead with.

5. **Checks Google reviews** — a 2.8-star property with 80 reviews is practically screaming that residents are unhappy with communication. That's an EliseAI problem.

6. **Scores the lead** — generates four scores (Demand, Friction, Scale, Opportunity) and rolls them into a single 0–100 Lead Score with a grade (A through F).

7. **Names the pain** — identifies which specific operational problems this property likely has, ordered by severity.

8. **Writes the email** — generates a cold outreach email grounded in the actual data points above. Not "I noticed your company" — more like "Your 2.8-star Google rating in a 97 Walk Score neighborhood suggests your residents expect fast responses you can't currently deliver."

The SDR reviews the output, tweaks the email if needed, and sends. Total active time: under 5 minutes per lead.

---

## 3. The Scoring Logic — Assumptions Explained

The lead score is built from four sub-scores. Each is independently meaningful. Here is exactly how each works and why I made the choices I did.

---

### 3a. Demand Score (20% of Lead Score)
*"How overwhelmed is the property manager likely to be with inbound rental activity?"*

| Signal | Weight | Normalization | Assumption |
|--------|--------|---------------|------------|
| Renter percentage | 25% | 70% = max score | A city where 70%+ of households rent is the upper bound of rental intensity. Below 20% renter share, EliseAI has limited addressable market. |
| Vacancy rate (inverted) | 20% | 0% vacancy = max score | A tight market (low vacancy) means properties are getting flooded with inquiries. More inquiries = more automation value. The FRED series reports state-level vacancy, which is a proxy. |
| Walk Score | 15% | 100 = max score | Walkable neighborhoods attract renters who comparison-shop intensively. Slow response in a walkable urban market costs leases. |
| Transit Score | 10% | 100 = max score | High transit access expands the renter pool to non-car-owners, increasing lead volume per unit. |
| Median household income | 10% | $150k = max score | Higher-income renters have higher service expectations and are more likely to leave reviews, escalate issues, or churn on communication failures. |
| Nearby amenities (1km radius) | 12% | 100 amenities = max score | Transit stops + parks + retail density within 1km is a density proxy. High-density neighborhoods generate more renter leads per property. |
| Population | 8% | 500k = max score | Large cities have deeper renter pools. This is a base-rate adjustment, not a differentiator on its own. |

---

### 3b. Friction Score (35% of Lead Score)
*"How hard is it to operate this property, and does that difficulty drive EliseAI's value?"*

This is the highest-weighted sub-score because operational friction is EliseAI's primary wedge. High friction = high maintenance load = high communication volume = high automation value.

| Signal | Weight | Normalization | Assumption |
|--------|--------|---------------|------------|
| Crime score (1–15) | 25% | 15 = max friction | Higher crime → more security incidents → more tenant communication → more maintenance coordination. Scored on a 1–15 composite scale (violent + property crime vs. national averages). |
| Annual precipitation days | 25% | 200 days = max friction | Wet climates (Seattle, Portland, Boston) increase HVAC issues, water intrusion, and in-person tour friction. 200 rain days is approximately tropical — US max is ~180. |
| Annual snowfall | 20% | 200cm = max friction | Heavy snow markets (Chicago, Minneapolis, Denver) drive HVAC/plumbing maintenance spikes and make in-person tours harder, pushing value to virtual tours and AI scheduling. |
| Temperature range (hottest–coldest day) | 20% | 80°C swing = max friction | Extreme seasonal swings stress building systems. A 45°C swing (e.g., Chicago) = more maintenance, more tenant complaints in summer and winter. |
| Elevation | 10% | 2,000m = max friction | High-elevation properties face harsher winters and higher HVAC/insulation demands. |

> **Note:** Friction does not mean a bad lead. A high-friction market means more operational stress, which means EliseAI is more valuable there, not less. A 100/100 friction score is ideal.

---

### 3c. Scale Score (15% of Lead Score)
*"How big is the operational footprint? More units = more automation leverage."*

| Signal | Weight | Normalization | Assumption |
|--------|--------|---------------|------------|
| Building type | 30% | Apartment Complex = 1.0 | Apartment complexes are EliseAI's primary ICP. Hotels score 0.80 (similar communication patterns). SFR scores 0.45 — still usable but much lower automation leverage per unit. |
| Building footprint (sq ft) | 25% | 100,000 sq ft = max | A larger physical footprint correlates with more units and more tenant activity. Sourced from OSM polygon geometry. |
| Lot area | 20% | ~2.15M sq ft = max | Larger parcel = larger property complex. Sourced from Intellipins parcel data. |
| Floors | 15% | 30 floors = max | Vertical complexity increases elevator, HVAC, and per-floor maintenance communication. |
| Unit count (explicit) | 10% | 500 units = max | When OSM has explicit unit tags, this directly caps the communication volume estimate. Rarely available — treated as a bonus signal. |

---

### 3d. Opportunity Score (30% of Lead Score)
*"Is there a specific trigger or opening that makes this company likely to buy now?"*

| Signal | Weight | Scoring | Assumption |
|--------|--------|---------|------------|
| News sentiment | 30% | Growth = 0.85, Cost pressure = 0.75, Trouble = 0.65, Mixed = 0.55, Neutral = 0.40, No news = 0.30 | A company expanding its portfolio needs automation immediately to avoid scaling headcount. A company under cost pressure is actively seeking efficiency. |
| Low Google rating | 20% | 1/5 = 0.90, 5/5 = 0.20 | A low rating with substantial reviews is evidence of existing operational pain that EliseAI directly addresses (response time, maintenance communication). |
| Renter market share | 15% | 65% renter = max | High renter % means the addressable market for EliseAI's leasing automation is large. Overlaps with Demand but weighted differently here as a market-fit signal. |
| Vacancy urgency | 15% | 0% vacancy = 0.30, 10%+ = 0.90 | Paradoxically, high vacancy = higher opportunity. A property struggling to fill units is in pain. Low vacancy = already winning, less urgency. |
| Walkability | 10% | 100 = max | Premium walkable markets attract quality renters with high expectations — faster response time is a competitive differentiator. |
| Wikipedia presence | 10% | Present = 0.80 | A company with a Wikipedia page is established, named-account material, and has verifiable public information. |

---

### 3e. Final Lead Score Composite

```
Lead Score = (Demand × 0.20) + (Friction × 0.35) + (Scale × 0.15) + (Opportunity × 0.30)
```

**Grade thresholds:**

| Grade | Score | Interpretation |
|-------|-------|----------------|
| A | 75–100 | Strong ICP match. Route to AE immediately. |
| B | 60–74 | Good fit. High-priority outreach sequence. |
| C | 45–59 | Qualified but not urgent. Standard sequence. |
| D | 30–44 | Weak fit. Low-touch or hold. |
| F | 0–29 | Not ICP. Do not contact. |

**Missing data handling:** If fewer than 30% of a sub-score's signals are available, that sub-score is excluded from the composite rather than penalizing the lead for missing data. The final score is always a weighted average of what's actually known. Every score record includes an `available_weight` field showing data coverage.

---

## 4. What Good and Bad Leads Look Like

### Lead Profile A — Grade A (Strong ICP)
**Scenario:** Large apartment complex, Denver, CO. Company recently announced acquisition of two new communities. Google rating 2.9/5 (340 reviews). Walk Score 82.

**What the scores see:**
- Demand: 71/100 — strong renter market (58% renter share), low vacancy (4.1%), high walkability
- Friction: 78/100 — heavy snowfall (~180cm/yr), above-average crime, wide temp swing (–25°C to 40°C)
- Scale: 85/100 — classified Apartment Complex, 92,000 sq ft footprint, 8 floors
- Opportunity: 88/100 — growth news signal (acquisition), poor Google rating (high pain), tight market urgency

**Lead Score: 80/100 — Grade A**

**Why this is right:** This company is growing (need to scale workflows fast), already showing service failures (2.9-star reviews), operates in a harsh climate (high maintenance communication load), and manages a large multifamily asset. Every EliseAI product line has a use case here.

**Email hook:** "Your acquisition of [property] in Denver adds roughly X units to coordinate — and your current 2.9-star Google rating suggests the teams there are already stretched. Here's how operators like yours use EliseAI to scale leasing and maintenance without headcount."

---

### Lead Profile B — Grade B (Solid Fit)
**Scenario (real data):** San Min, Real Property Associates, Seattle, WA. Property at 838 NE 66th St. No recent news. Walk Score 97, Transit 65.

**What the scores see:**
- Demand: ~68/100 — 54.8% renter share, $105k median income, Walker's Paradise (97), moderate transit
- Friction: ~52/100 — Seattle rain (~150 precip days), moderate crime, modest snowfall
- Scale: ~45/100 — parcel is 83,000 sq ft but limited building type data
- Opportunity: ~55/100 — no news signal, no Google rating retrieved, moderate walkability

**Lead Score: 66/100 — Grade B**

**Why this is right:** Seattle is a strong rental market and the property is sizeable. The absence of news isn't disqualifying — it just means the pitch leads with market conditions ("Your Walk Score 97 property is in one of Seattle's highest-demand corridors…") rather than a news trigger. The score is honest about data gaps.

---

### Lead Profile C — Grade D/F (Weak ICP)
**Scenario (hypothetical):** Regional property manager, rural Montana. Single-family rental portfolio, town population 8,000, renter share 28%, vacancy 11%, Walk Score 22, no news, Google rating 4.4/5 (12 reviews).

**What the scores see:**
- Demand: 18/100 — low population, very low renter share, poor walkability
- Friction: 35/100 — some snowfall and temp range, but limited crime data
- Scale: 22/100 — SFR building type (0.45 weight), small footprint
- Opportunity: 29/100 — high vacancy (struggling) but no news, excellent reviews (no pain signal), no Wikipedia presence

**Lead Score: 28/100 — Grade F**

**Why this is right:** The tool correctly identifies this as a low-value target. The renter market is thin, the property type isn't EliseAI's ICP, and the high rating suggests the manager is handling service well without automation. SDR time is better spent elsewhere. The 11% vacancy is the only hook — but without scale or market depth, it's not enough.

---

## 5. Limitations — What the Tool Cannot Do

**Be honest about this. Sales leadership needs to know where not to trust the output.**

| Limitation | Why It Exists | What to Do |
|------------|---------------|------------|
| **State-level vacancy only** | FRED doesn't publish city-level vacancy consistently. The FRED series (e.g., `WARVAC`) is state-wide, not city-specific. | Treat vacancy as a market signal, not a property-specific measurement. |
| **No direct unit count for most properties** | OSM building tags rarely include `building:units`. Most scale scores use footprint as a proxy. | When a lead is borderline, verify unit count manually before calling. |
| **News is company-level, not property-level** | NewsAPI searches by company name. A large REIT with 500 properties may have national news that doesn't apply to the local property. | Scan the news snippets in the output before using them in the email. |
| **Google Places may match the wrong listing** | The tool searches by property address first, then company name. For large companies (Greystar, AvalonBay), the address search may match a corporate office, not the property. | Check `matched_via` in the output. If it says `company`, verify the rating is for a property, not an office. |
| **Crime data only available for city-level agencies** | FBI CDE data is by police agency. Small towns or counties without their own PD may return no data. Approximately 15% of US cities have no ORI match. | When crime is missing, the friction score runs on weather only — still valid. |
| **No portfolio-level scoring** | Each lead is scored as a single address. A company managing 200 properties is scored on whatever address the SDR entered. | For enterprise accounts, enter the HQ address or most prominent property and use the company-level signals (news, Wikipedia, Google) as the primary inputs. |
| **LLM-generated email is a draft** | The outreach email is generated by Claude Sonnet. It uses real data, but tone, accuracy of claims, and CTA should be reviewed before sending. | Always read the email before sending. The pain point evidence is real; the language is a starting point. |
| **Historical enrichment, not real-time** | Census data is 2021 ACS. Climate data is 2024 archive. Crime data is latest available year (typically 1–2 years behind). | Use for directional market assessment. For deals where freshness matters, supplement with current Zillow or CoStar data. |

---

## 6. Future Iterations — What We'd Build With More Time

| Priority | Feature | Value |
|----------|---------|-------|
| **High** | **Portfolio-level scoring** — upload a CSV of 50 properties for one company and score the entire footprint, not just one address | Enables enterprise account prioritization |
| **High** | **CRM integration (Salesforce / HubSpot)** — auto-push scored leads with all enrichment fields; auto-update score when data refreshes | Eliminates the CSV handoff; keeps data current |
| **High** | **City-level vacancy via Zillow or CoStar** | Replaces state-level FRED proxy with actual local market data |
| **Medium** | **Explicit unit count lookup** via CoStar or county assessor APIs | Makes scale score significantly more precise |
| **Medium** | **Sequence integration** — auto-add Grade A/B leads to Outreach.io or Apollo sequence with the generated email pre-loaded | Reduces SDR active time from 5 min to <1 min per lead |
| **Medium** | **Score refresh on trigger** — re-score a lead automatically when a news event fires (via NewsAPI webhook) or the Google rating changes significantly | Keeps the lead list fresh without re-running manually |
| **Low** | **Competitive signal detection** — flag when a company is already using Yardi, RealPage, or Entrata (indicating a displacement sale, not a greenfield) | Adjusts the email angle from "here's a new tool" to "here's why to switch" |
| **Low** | **Multi-language support** — for Spanish-language markets in Miami, LA, Houston | Expands serviceable markets |
