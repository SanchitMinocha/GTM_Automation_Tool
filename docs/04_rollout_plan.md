# Rollout Plan

> **Audience:** Revenue Leadership, SDR Managers, RevOps

---

## Philosophy

An SDR sending a bad cold email because the tool hallucinated a rating is worse than no tool at all. The rollout is designed to earn trust at each step before expanding scope. We move from **validate** → **semi-automate** → **fully automate**, with a clear quality gate at each transition.

---

## Phase 1 — Internal Validation (Week 1)

Before any SDR touches this in a real workflow, run it against leads where we already know the outcome.

**What to run:**
- 10–15 closed-won deals
- 10–15 deals that went nowhere
- 5–10 Grade A/B candidates from the current pipeline list

**What to check:**
1. Do closed-won accounts score in the top quartile? Does closed-lost cluster below 50?
2. Does every email reference real, correct data points — not hallucinated numbers?
3. Does geocoding succeed for all test addresses? Where does it fail?
4. Run the batch processor on all 30+ leads to confirm no crashes on bad data.

**Go / no-go:** If a converted enterprise deal scores F, or if 20%+ of test emails contain incorrect facts, fix the scoring weights or LLM prompts before Week 2. If the results roughly track with reality, proceed.

---

## Phase 2 — Semi-Automated Pilot (Weeks 2–4)

### What "semi-automated" means

The tool generates the enrichment, score, pain points, and a draft email. An SDR reviews the email on-screen, tweaks it if needed, then manually clicks Send in their email client or CRM. The tool never sends anything autonomously during this phase.

### Who's involved

- **2–3 pilot SDRs** — include at least one skeptic, not just enthusiastic early adopters
- **SDR Manager** — reviews aggregate outputs weekly; their buy-in is what gets the rest of the team on board
- **RevOps** — sets up the tracking sheet and owns API key budget

### What they do each day

```
Morning (15 min):
  Run batch on today's 60 prioritized leads
  (or load pre-scored leads from overnight batch run)

Working hours (9am–3pm):
  Review queue in the tool — 10 leads/hour
  For each lead:
    ├── Read the email draft
    ├── Check: do the numbers match what's on screen?
    ├── Tweak subject line or opening if needed
    └── Copy-paste into Gmail / Outreach / Apollo → Send

End of day (5 min):
  Mark each lead: "sent as-is" | "sent with edits" | "skipped"
  Note skip reasons in shared doc
```

### What to learn from the pilot

| Question | How to measure |
|----------|---------------|
| How much do SDRs rewrite emails? | Edit distance: heavy rewrites = something in the arc or data is systematically off |
| Which leads do they skip and why? | Skip log: "wrong property type", "data looks stale", "company too small" |
| Where does geocoding fail? | Flag failed addresses; patterns often point to address format issues |
| Which story arcs do SDRs trust? | Track which arcs they send as-is vs. rewrite |

Stay close during this phase. A weekly 30-minute check-in with the pilot SDRs is worth more than any analytics dashboard — they'll tell you exactly what's broken.

---

## Phase 3 — Full Team Rollout (Weeks 5–6)

If the pilot completes with no major accuracy issues and SDRs are self-reporting meaningful time savings, roll out to the full team.

**Onboarding:**
- One 30-minute training session covering the user guide
- Shared Slack channel for questions, bugs, and weird outputs
- Simple rule: "If the email mentions a number you can't verify, fix it before sending"

**Outreach schedule (locked in from Week 5 forward):**
- Batch score new leads overnight or in a morning run
- Target the top 60 by Lead Score each day
- Send window: **9:00 AM – 3:00 PM**, 10 emails/hour, random spacing within each hour (2–8 minutes between sends)
- This pacing mirrors a human SDR's natural rhythm and avoids spam-filter triggers

---

## Phase 4 — Automated Sending (Week 7+)

Once 3–4 weeks of semi-automated data shows that:
- ≥70% of emails go out without SDR edits
- No factual error complaints from prospects
- Deliverability metrics (open rate, spam complaints) are clean

...then wire up automated sending via the CRM's API (Outreach.io, Apollo, or HubSpot sequences). The tool pushes pre-scored emails into a send queue; the scheduler fires them at the right intervals. SDRs shift to reviewing replies and booking meetings rather than managing the queue.

---

## A/B Testing Program (Starts Week 5)

The tool assigns every email a `story_arc` field. Use this to run a continuous A/B program:

### Round 1 (Weeks 5–8): Arc vs. reply rate

Group outcomes by arc and measure which hooks get responses:

| Arc | Description | Hypothesis |
|-----|-------------|-----------|
| `reputation_gap` | Low Google rating → residents expect better | Highest reply rate — concrete pain, easy to validate |
| `growth_strain` | Recent acquisition/expansion | High reply rate — timely trigger |
| `operational_friction` | Bad weather, high crime, maintenance load | Medium — resonates with operators, not decision-makers |
| `premium_expectations` | Premium market, residents expect instant responses | Medium — depends on price sensitivity |
| `lead_speed` | High vacancy urgency, tight market | Lower — feels generic without a specific trigger |

After 200 sends across arcs, compare reply rates. If `reputation_gap` outperforms `lead_speed` by 2×, increase the score threshold that triggers the reputation arc.

### Round 2 (Weeks 9–12): Subject line experiments

Split leads of the same arc into two subject line styles:
- **Data-led**: "Your 2.8-star Google rating in a Walk Score 97 building"
- **Question-led**: "Are your residents getting the response speed they expect?"

Track open rate per variant. 150 sends per variant gives statistical signal.

### Round 3 (Week 13+): Send time within window

Does 9am outperform 1pm for your specific ICP? The tracking schema captures `sent_at` — segment reply rates by hour and optimize the send window.

---

## Success Metrics

| Timeframe | What we're measuring | Target |
|-----------|---------------------|--------|
| End of pilot (Week 4) | SDRs self-report time saved per lead | ≥15 min saved vs. manual research |
| 8 weeks | Grade A/B leads book meetings at higher rate than C/D | Grade A/B reply rate ≥ 2× Grade C/D |
| 12 weeks | Emails sent without SDR edits | ≥75% go out unmodified |
| 16 weeks | Tool is the default step before any outbound email | No new outbound sent without a tool-generated score |

---

## Who Owns What

| Role | Responsibility |
|------|---------------|
| **SDR Manager** | Pilot SDR selection, weekly check-ins, go/no-go calls at each phase transition |
| **RevOps** | API keys, spend monitoring, tracking sheet setup, eventual CRM integration |
| **Engineering** | Fix geocoding failures, iterate on scoring weights and LLM prompts from pilot feedback |
| **2–3 Pilot SDRs** | Use the tool on every new outbound lead during pilot; flag anything weird |

---

## Cost at Scale

Assuming full automation on 60 sends/day, 5 days/week:

| Item | Cost | Notes |
|------|------|-------|
| Anthropic (Haiku + Sonnet) | ~$0.02–0.05/lead | Haiku for pain points (~$0.003), Sonnet for email (~$0.015) |
| **Alternative: Groq** | **$0.00** | Free tier covers both steps; quality slightly below Sonnet |
| NewsAPI developer plan | $449/mo | Only needed if running >100 leads/day on news |
| Google Places | ~$0.017/lead | 2 calls × $0.0085; $200 free credit covers ~11,700 leads |
| All other APIs | $0 | Free tiers more than sufficient at SDR-scale |
| **Total at 60 leads/day (Anthropic)** | **~$1.20–3.00/day** | ~$30–75/month |
| **Total at 60 leads/day (Groq)** | **~$0.00–1.50/day** | Google Places is the only real cost |

At any meaningful conversion rate, the pipeline cost per booked meeting is effectively zero.
