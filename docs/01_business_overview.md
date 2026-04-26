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

8. **Writes the email** — generates a cold outreach email grounded in the actual data points above. Not "I noticed your company" — more like "Your 2.8-star Google rating in a 97 Walk Score neighborhood suggests your residents expect fast responses you can't currently deliver."

The SDR reviews the output, tweaks the email if needed, and sends. Total active time: under 5 minutes per lead.

---

## The Scoring Logic — How It Works and Why

The lead score is built from four independent sub-scores that each answer a different question. Here's what each one measures and why I weighted it the way I did.

---

### Demand Score — 20% of Lead Score
*"How overwhelmed is this property manager likely to be with inbound rental activity?"*

A tight rental market with a lot of renters and high walkability means constant inquiry volume. The property manager is fighting fires all day — which is exactly when automation is most valuable.

| Signal | Weight | What "maxed out" looks like | Why I chose this |
|--------|--------|----------------------------|-----------------|
| Renter % of households | 25% | 70% renters | Cities above 70% renter share are effectively full rental markets — think Manhattan or San Francisco |
| Vacancy rate (inverted) | 20% | ~0% vacancy | Low vacancy = properties filling up fast = high inquiry volume |
| Walk Score | 15% | Score of 100 | Walkable neighborhoods attract renters who comparison-shop aggressively. Slow response = lost lease |
| Transit Score | 10% | Score of 100 | Transit access expands the renter pool to people without cars, increasing lead volume per unit |
| Median household income | 10% | $150k/year | Higher-income renters have higher service expectations and are quicker to complain or churn |
| Nearby amenities (1km radius) | 12% | 100 amenities | Transit stops + parks + retail density is a density proxy — more density = more renters in the area |
| Population | 8% | 500k | Base-rate adjustment: large cities have deeper renter pools |

---

### Friction Score — 35% of Lead Score
*"How hard is it to operate this property, and does that difficulty make EliseAI more valuable?"*

This is the highest-weighted sub-score because friction is EliseAI's primary wedge. More friction means more maintenance calls, more tenant communication, more scheduling, more everything — all the stuff that AI handles well.

**Important:** a high Friction score is a good thing for us. A 100/100 friction score means the property is maximally stressful to run and maximally in need of automation.

| Signal | Weight | What "maxed out" looks like | Why I chose this |
|--------|--------|----------------------------|-----------------|
| Crime score (1–15 scale) | 25% | Score of 15 (very high crime) | High crime → more security incidents → more tenant communication → more demand for fast response |
| Annual precipitation days | 25% | 200 rain days/year | Wet climates (Seattle, Portland, Boston) mean more water intrusion issues, HVAC problems, and maintenance requests |
| Annual snowfall | 20% | 200 cm/year | Snow markets (Chicago, Minneapolis) drive maintenance spikes and push tenants toward digital scheduling |
| Temperature range (hottest – coldest day) | 20% | 80°C swing | Extreme seasonal variation stresses building systems — more maintenance, more tenant complaints |
| Elevation | 10% | 2,000m | High-elevation properties face harsher winters and higher HVAC/insulation demands |

---

### Scale Score — 15% of Lead Score
*"How big is the operational footprint? More units = more automation leverage."*

A 400-unit apartment complex in Seattle and a single-family rental in rural Montana are not the same opportunity. This score captures that difference.

| Signal | Weight | What "maxed out" looks like | Why I chose this |
|--------|--------|----------------------------|-----------------|
| Building type | 30% | Apartment Complex | EliseAI's primary ICP. SFR scores about half this because automation leverage per unit is much lower |
| Building footprint | 25% | 100,000 sq ft | Larger physical footprint correlates with more units and more tenant activity |
| Lot area | 20% | ~200,000 sq ft parcel | Larger parcel typically means a larger property complex |
| Floors | 15% | 30 floors | Vertical complexity adds elevator, HVAC, and per-floor maintenance communication |
| Unit count | 10% | 500 units | Rarely available in the data — treated as a bonus signal when it is |

**Building type scores used in calculation:**

| Building Type | Score |
|---------------|-------|
| Apartment Complex | 1.00 |
| Hotel | 0.80 |
| Commercial / Industrial | 0.75 |
| Office Building | 0.70 |
| Single Family Housing | 0.45 |
| Unknown | 0.20 |

---

### Opportunity Score — 30% of Lead Score
*"Is there a specific trigger or opening that makes this company likely to act now?"*

This score is about timing and buying signal — it tells you whether to reach out today or wait.

| Signal | Weight | What moves it | Why I chose this |
|--------|--------|--------------|-----------------|
| News sentiment | 30% | Growth → 0.85, Cost pressure → 0.75, Trouble → 0.65, No news → 0.30 | A company expanding its portfolio needs automation immediately. A company under cost pressure is actively looking for efficiency gains |
| Low Google rating | 20% | 1 star → 0.90, 5 stars → 0.20 | A low rating with lots of reviews is evidence of existing operational pain EliseAI directly solves |
| Renter market share | 15% | 65% renters = max | High renter % means the addressable leasing automation market is large |
| Vacancy urgency | 15% | 10%+ vacancy = 0.90, 0% = 0.30 | High vacancy means the property is struggling to fill units — they're in pain and looking for solutions |
| Walkability | 10% | Walk Score 100 = max | Premium walkable markets attract renters with high expectations — faster response is a competitive edge |
| Wikipedia presence | 10% | Page found = 0.80 | A company with a Wikipedia page is an established named account with verifiable public information |

---

### The Final Number

```
Lead Score = (Demand × 0.20) + (Friction × 0.35) + (Scale × 0.15) + (Opportunity × 0.30)
```

| Grade | Score | What to do |
|-------|-------|------------|
| A | 75–100 | Strong ICP match. Route to AE immediately. |
| B | 60–74 | Good fit. High-priority outreach. |
| C | 45–59 | Qualified but not urgent. Standard sequence. |
| D | 30–44 | Weak fit. Low-touch or hold. |
| F | 0–29 | Not ICP. Skip. |

**One thing worth noting about missing data:** if fewer than 30% of a sub-score's signals were available, that sub-score is excluded from the composite entirely rather than dragging the lead's score down. The final score is always a weighted average of what's actually known. Every score record includes an `available_weight` field showing coverage — so you can tell at a glance if a score was built on solid data or just a handful of signals.

---

## What Good and Bad Leads Look Like in Practice

### Grade A — Large apartment complex, Denver, CO

The company recently announced acquiring two new communities. Google rating 2.9/5 (340 reviews). Walk Score 82.

- **Demand: 71/100** — strong renter market (58% renter share), low vacancy (4.1%), high walkability
- **Friction: 78/100** — heavy snowfall (~180cm/yr), above-average crime, wide temp swing
- **Scale: 85/100** — Apartment Complex, 92,000 sq ft footprint, 8 floors
- **Opportunity: 88/100** — growth signal (acquisition), poor Google rating, tight market urgency

**Lead Score: 80/100 — Grade A**

This one is right. The company is growing and needs to scale workflows fast, already showing service failures in their reviews, operates in a harsh climate with high maintenance communication load, and manages a large multifamily asset. Every EliseAI product line has a use case here.

**Email hook:** *"Your acquisition of [property] in Denver adds roughly X units to coordinate — and your 2.9-star Google rating suggests the teams there are already stretched. Here's how operators like yours use EliseAI to scale leasing and maintenance without headcount."*

---

### Grade B — San Min, Real Property Associates, Seattle, WA

Property at 838 NE 66th St. No recent news. Walk Score 97, Transit 65.

- **Demand: ~68/100** — 54.8% renter share, $105k median income, Walker's Paradise
- **Friction: ~52/100** — Seattle rain (~150 precip days), moderate crime
- **Scale: ~45/100** — parcel is 83,000 sq ft but limited building type data available
- **Opportunity: ~55/100** — no news signal, no Google rating retrieved, moderate walkability

**Lead Score: 66/100 — Grade B**

The absence of news here isn't disqualifying. It just means the pitch leads with market conditions rather than a news trigger. Seattle is a strong rental market and the property is sizeable. The score is honest about what it doesn't know.

**Email hook:** *"Your Walk Score 97 property is in one of Seattle's highest-demand corridors — renters there expect instant responses, and the ones you lose go to the next building on the block."*

---

### Grade F — Regional property manager, rural Montana

Single-family rental portfolio, town population 8,000, renter share 28%, vacancy 11%, Walk Score 22, no news, Google rating 4.4/5 (12 reviews).

- **Demand: 18/100** — low population, very low renter share, poor walkability
- **Friction: 35/100** — some snowfall and temp range, but limited crime data
- **Scale: 22/100** — SFR building type, small footprint
- **Opportunity: 29/100** — high vacancy but no news, excellent reviews (no pain signal), no Wikipedia presence

**Lead Score: 28/100 — Grade F**

This one is also right. The renter market is thin, the property type isn't EliseAI's ICP, and the high rating suggests this manager is handling service well without automation. The high vacancy is the only hook, but without scale or market depth behind it, there's no real opportunity here.

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
