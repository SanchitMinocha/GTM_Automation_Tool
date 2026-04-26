# Rollout Plan

---

## How I'd Actually Test and Roll This Out

The honest answer is I'd want to be pretty careful here. An SDR sending a bad cold email because the tool hallucinated a rating or cited the wrong vacancy rate is worse than no tool at all. So the rollout is really about earning trust at each step before expanding.

---

## Step 1: Internal Testing (Week 1)

Before anyone touches this in a real sales workflow, I'd spend a few days running it against leads where we already know the outcome. Take 10–15 closed-won deals and 10–15 deals that went nowhere, run them through the pipeline, and see if the scores track with reality. I'm not looking for a perfect model — I'm looking for obvious failures. Does a converted enterprise deal score as an F? Does a solo SFR in a rural town score higher than a 400-unit apartment complex in Seattle?

I'd also manually check the outreach email on a few leads to make sure the numbers it cites match what's actually in the score dashboard. That's the most important thing to validate — factual accuracy trumps everything else.

If anything looks badly wrong, I'd fix the scoring weights or LLM prompts before moving on. If the results roughly make sense, that's enough signal to run a pilot.

---

## Step 2: Pilot with One SDR Pod (Weeks 2–3)

I'd pick 2–3 SDRs from one pod — ideally including at least one skeptic, not just the enthusiastic early adopters. Give them the tool, the user guide, and 30 minutes of training. Ask them to use it on every new outbound lead for two weeks, but keep using their own judgment on whether to actually send the email.

What I'd want to learn from the pilot:
- Where do they trust the score and where don't they? The places they override it are the most useful data.
- Does the email actually feel usable, or does it need heavy rewriting every time?
- Any addresses where the geocoding fails or the data comes back obviously wrong?

I'd stay close — check in weekly, ask them to flag anything weird in Slack. The goal isn't to prove the tool works; it's to find what breaks in practice before it breaks for everyone.

---

## Step 3: Full Rollout (Weeks 4–5)

If the pilot goes reasonably well — no major accuracy issues, SDRs finding it saves meaningful time — I'd roll it out to the full team. One training session (30 min), walkthrough of the user guide, and a shared Slack channel for questions and bug reports.

At this point I'd also set up a simple tracking sheet: which leads were run through the tool, what grade they got, did they get a response. After 6–8 weeks you start to see whether Grade A leads actually convert better than Grade C, which is the signal that tells you whether the scoring is actually adding value or just creating a false sense of prioritization.

---

## Who I'd Involve

**SDR Manager** — their buy-in is the most important thing. If the manager doesn't believe in the scores, the team won't use them. I'd loop them in from day one of the pilot, not just present them with results afterward.

**2–3 Pilot SDRs** — I'd ask them to help me understand the workflow, not just QA the outputs. SDRs know things about prospecting in their specific market that no scoring model captures.

**RevOps** — they need to own the API keys, monitor costs, and figure out how scored leads eventually flow into Salesforce or whatever CRM is in use. I'd bring them in early so the CRM integration isn't an afterthought.

**Engineering (just me for now)** — fix what breaks, iterate on the scoring weights based on pilot feedback, and eventually build the CRM push if the pilot validates the tool is worth it.

---

## What Success Looks Like

Short term (after pilot): SDRs self-report saving at least 15 minutes per lead, and the emails are going out same-day rather than sitting in a draft folder.

Medium term (8 weeks): Grade A/B leads are booking meetings at a noticeably higher rate than Grade C/D leads. If they're not, the scoring weights need recalibration.

Longer term: this becomes the default step before any outbound email goes out — not because it's required, but because SDRs find it genuinely useful.
