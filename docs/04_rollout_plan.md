# EliseAI GTM Automation Tool — Rollout & Project Plan

> **Audience:** Revenue leadership, RevOps, SDR managers.
> **Purpose:** Define how we test, validate, and scale this tool — and what success looks like at each stage.

---

## 1. MVP Testing Plan

**Goal:** Confirm the tool produces accurate, trustworthy outputs before any SDR uses it in a real outreach sequence.

**Who:** The builder (eng/RevOps) + 1 SDR manager as QA reviewer.

**What:**

| Test | Pass Criteria |
|------|--------------|
| Run 10 leads with known outcomes (closed/lost deals) | Grade A/B leads should map to deals that closed or progressed; Grade D/F should map to deals that stalled or were unqualified |
| Verify enrichment accuracy for 10 addresses | Spot-check Census population, Walk Score, and vacancy rate against publicly verifiable sources (City-Data.com, WalkScore.com directly) |
| Verify building type classification for 10 addresses | Check that apartment complexes are classified as "Apartment Complex" and not SFR — the single most important classification for ICP fit |
| Check outreach emails for factual accuracy | Every number in the email body (Walk Score, vacancy rate, Google rating) should match the score dashboard. Zero hallucinations. |
| Test geocoding on edge case addresses | Include 3 addresses that are unusual (rural, industrial park, campus) — verify graceful failure, not crash |
| Test missing-key behavior | Remove one API key; verify the pipeline still runs and the score is labeled with `available_weight` reflecting the gap |

**Duration:** 1–2 days.

**Exit criteria:** 0 crashes on valid input, <5% factual inaccuracies in email body, building type correct on ≥80% of apartment complexes.

---

## 2. Pilot Rollout

**Goal:** Put the tool into the hands of one SDR pod and measure whether it actually changes behavior and outcomes.

**Who:** 2–3 SDRs from the most active pod. One SDR manager as the feedback owner.

**Duration:** 2 weeks.

**Structure:**

| Week | Activity |
|------|----------|
| Week 1 | SDRs run every new outbound lead through the tool. They use the draft email as a starting point but are not required to send it verbatim. Slack channel for real-time bug reports. |
| Week 2 | SDRs rate each lead score after their call/reply (was the grade accurate?). Manager reviews 20 outreach emails — flagging any that had wrong data. |

**Feedback loop:** Weekly 30-minute sync between SDR manager and builder. SDRs log anomalies in a shared spreadsheet (lead, expected grade, actual grade, issue).

**Success metrics for pilot:**

| Metric | Target |
|--------|--------|
| Time saved per lead (self-reported) | ≥15 min average vs. manual process |
| SDR satisfaction (survey, 1–5) | ≥4.0 |
| Score accuracy (SDR-rated "was the grade right?") | ≥75% correct |
| Email factual accuracy (manager spot-check) | ≥95% — zero wrong numbers |
| Pipeline crashes / errors | <3 during pilot period |

**Exit criteria:** All targets met, or issues are understood and have a known fix.

---

## 3. Full Rollout Timeline

| Week | Milestone |
|------|-----------|
| **Week 1** | MVP test complete. Builder + manager QA sign-off. |
| **Week 2** | Pilot begins. 2–3 SDRs onboarded with the User Guide. Slack channel open. |
| **Week 3** | Mid-pilot check-in. Bug fixes applied. If major issues: extend pilot 1 week. |
| **Week 4** | Pilot complete. Metrics reviewed. Go/no-go decision for full rollout. |
| **Week 5** | Full SDR team onboarded (training session + User Guide). All leads run through tool before outreach. |
| **Week 6** | First batch of A/B-scored leads enter a dedicated high-priority sequence. Track reply and meeting rates vs. historical baseline. |
| **Week 8** | First look at conversion data: are Grade A leads converting at a higher rate than Grade C/D? |
| **Week 12** | Retrospective. Score weights adjusted if accuracy data suggests a signal is over/underweighted. |
| **Week 16** | CRM integration scoping begins (Salesforce / HubSpot push). Google Sheets button built for SDRs who prefer not to use the UI. |

---

## 4. Stakeholder Map

| Role | Owner | Responsibility |
|------|-------|----------------|
| **Champion / Decision Maker** | VP Sales or CRO | Approves rollout; sets success targets; allocates SDR time for pilot |
| **RevOps Owner** | RevOps lead | Manages API keys, cost tracking, CRM integration scoping |
| **SDR Manager** | Pod manager for pilot | Selects pilot SDRs; runs feedback syncs; rates score accuracy |
| **Pilot SDRs** | 2–3 selected SDRs | Run the tool daily; report bugs and anomalies; rate email quality |
| **Technical Owner** | Builder (engineering) | Bug fixes, API monitoring, new feature development post-rollout |
| **Security/Compliance** | IT or legal (if applicable) | Review API key storage, data retention policy for lead records |

---

## 5. Success Metrics

### Leading indicators (measurable immediately)

| Metric | Measurement | Target |
|--------|-------------|--------|
| Time saved per lead | SDR self-reported (survey or time tracking) | ≥15 min per lead |
| Leads processed per SDR per day | Divide leads entered / SDR count | 2× baseline (tool removes lookup work) |
| Score accuracy (SDR-rated) | Post-call survey: "Was this grade correct?" | ≥75% match |
| Email open rate — tool-generated vs. manual | Track in email sequencing tool (Outreach, Apollo) | ≥5pp lift |

### Lagging indicators (visible at 8–12 weeks)

| Metric | Measurement | Target |
|--------|-------------|--------|
| Reply rate by grade | % replies for A/B leads vs. C/D leads | A/B ≥2× C/D reply rate |
| Meeting conversion by grade | % meetings booked for A/B vs. C/D | A/B ≥2× C/D meeting rate |
| Closed-won rate by grade | Deals closed from A/B-sourced leads vs. C/D | ≥20pp lift for A/B |
| Time from lead to first outreach | Days between SDR receiving lead and first email sent | Reduce from ~3 days to same day |

### Calibration metric

| Metric | Measurement |
|--------|-------------|
| Score weight accuracy | At 12 weeks: do Grade A leads actually convert at higher rates? If Grade C leads convert as well as Grade A, the scoring weights need recalibration. |

---

## 6. Cost Analysis

### Per-lead API cost (approximate)

| API | Cost per lead | Notes |
|-----|--------------|-------|
| Anthropic (Haiku — pain points) | ~$0.002 | ~500 input + 200 output tokens at Haiku pricing |
| Anthropic (Sonnet — email) | ~$0.01–0.02 | ~800 input + 250 output tokens at Sonnet pricing |
| Google Places | ~$0.034 | Text Search ($0.017) + Place Details ($0.017) |
| WalkScore | ~$0 | Free tier covers 5,000/day |
| NewsAPI | ~$0 | Free tier covers 100/day; developer plan at $449/mo covers 1,000/day |
| Intellipins | TBD | Priced commercially; contact for per-lookup rate |
| All others (Census, FRED, OSM, Open-Meteo, FBI, Wikipedia) | $0 | Free / public |

**Estimated total per lead (excluding Intellipins): ~$0.05–0.06**

### Cost at scale

| Volume | Monthly cost (est., excluding Intellipins) |
|--------|-------------------------------------------|
| 50 leads/day (1,000/mo) | ~$50–60/mo |
| 200 leads/day (4,000/mo) | ~$200–250/mo |
| 500 leads/day (10,000/mo) | ~$500–600/mo + NewsAPI developer plan ($449/mo) |

**NewsAPI becomes the binding constraint at volume.** At 500 leads/day, you need the developer plan ($449/mo). Above 1,000/day, contact NewsAPI for an enterprise plan.

**Google Places billing note:** Google provides $200/month free credit. At $0.034/lead, that covers ~5,900 leads/month for free. Above that, billing begins.

**Anthropic billing note:** Claude Sonnet pricing changes with model versions. At current pricing (Sonnet 4.6), the email generation step costs roughly $0.01–0.02 per lead. Budget $25–50/month at 50 leads/day.

### ROI framing

At 50 leads/day and 15 minutes saved per lead:
- **Time saved:** 50 × 15 min = 12.5 hours/day = ~260 hours/month
- **SDR fully-loaded cost:** ~$50/hour (blended)
- **Value of time saved:** ~$13,000/month
- **Tool cost:** ~$60–500/month depending on Intellipins pricing
- **ROI:** >20:1 on time alone, before any improvement in conversion rate

At 200 leads/day, the math improves further. The tool's cost scales with usage; SDR time cost scales linearly too, but the efficiency gain compounds as more leads get scored and deprioritized before human time is spent on them.

---

## 7. Risk Register

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| SDR adoption resistance ("I don't trust the score") | Medium | High | Walk SDRs through 3 example leads in the pilot kickoff. Show them the data behind the grade, not just the grade. |
| API cost overrun (Google Places) | Low | Medium | Set billing alerts in Google Cloud console. The $200 free credit covers ~6,000 leads/month. |
| Intellipins rate limiting at batch scale | Medium | Medium | Add 1-second inter-lead delay in batch mode. Already handled gracefully in the code — falls back to Nominatim. |
| Score accuracy complaints from SDRs | Medium | High | Set expectations: score is a prioritization tool, not a guarantee. Track accuracy data in the pilot to build trust. |
| LLM email hallucinations | Low | High | Mandatory human review before sending. This is already in the User Guide. |
| Data freshness issues (Census 2021, crime 1-2yr lag) | Medium | Low | Documented in the Business Overview limitations. Use for directional signals, not precise claims. |
