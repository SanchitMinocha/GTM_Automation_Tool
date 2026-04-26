# EliseAI GTM Automation Tool — User Guide

> **Audience:** SDRs and SDR managers who run this tool daily.
> **Assumption:** You have never used Python or the command line before. We'll cover everything.

---

## 1. What You Need Before Starting

You'll need API keys for a handful of services. Most of them are free. The only one that costs money per use is the LLM provider (Anthropic or Groq) — and Groq has a generous free tier if you want to start without a credit card.

| Service | What it does | Where to get a key | Free tier |
|---------|-------------|-------------------|-----------|
| **Anthropic** *(or Groq — pick one)* | Writes the outreach email and pain points | [console.anthropic.com](https://console.anthropic.com) → API Keys | Pay-per-use; ~$0.01–0.05 per lead |
| **Groq** *(free alternative to Anthropic)* | Same steps, using open-source models | [console.groq.com](https://console.groq.com) → API Keys | Generous free tier; no credit card required |
| **WalkScore** | Walk/transit/bike scores | [walkscore.com/professional/api.php](https://www.walkscore.com/professional/api.php) | 5,000 requests/day free |
| **Intellipins** | Property data and building type | [intellipins.com](https://intellipins.com) → Developer | Contact for pricing |
| **Google Places** | Property ratings and reviews | [console.cloud.google.com](https://console.cloud.google.com) → APIs & Services → Places API | $200 free credit/month |
| **NewsAPI** | Company news | [newsapi.org/register](https://newsapi.org/register) | 100 requests/day free |
| **FRED (St. Louis Fed)** | Vacancy rates | [fred.stlouisfed.org/docs/api/api_key.html](https://fred.stlouisfed.org/docs/api/api_key.html) | Free |
| **FBI API** | Crime data | [api.data.gov/signup/](https://api.data.gov/signup/) | Free |
| **Census Bureau** | Population and income | [api.census.gov/data/key_signup.html](https://api.census.gov/data/key_signup.html) | Free (optional but recommended) |

---

## 2. Setup — Step by Step

### Step 1: Check if Python is installed

Open Terminal (Mac) or Command Prompt (Windows) and type:

```
python3 --version
```

If you see something like `Python 3.11.4`, you're good. If you get an error, download Python from **python.org/downloads** and install it. On Windows, make sure to check "Add Python to PATH" during installation.

### Step 2: Download the project

If you received a ZIP file, unzip it and place the folder somewhere easy to find, like your Desktop. You should have a folder called `GTM_Automation_Tool`.

### Step 3: Open Terminal and navigate to the project

**Mac:**
1. Open Terminal (search "Terminal" in Spotlight)
2. Type: `cd ~/Desktop/GTM_Automation_Tool`
3. Press Enter

**Windows:**
1. Open Command Prompt (search "cmd" in Start)
2. Type: `cd C:\Users\YourName\Desktop\GTM_Automation_Tool`
3. Press Enter

### Step 4: Create a virtual environment

This keeps the tool's dependencies separate from anything else on your machine.

```
python3 -m venv venv
```

Then activate it:

**Mac/Linux:**
```
source venv/bin/activate
```

**Windows:**
```
venv\Scripts\activate
```

You should see `(venv)` appear at the start of your command line. That means it worked.

### Step 5: Install dependencies

```
pip install -r requirements.txt
```

This downloads everything the tool needs. It takes 1–3 minutes the first time.

### Step 6: Add your API keys

In the project folder, find the file called `.env.example` and rename it to `.env`. Open it in any text editor (Notepad, TextEdit, VS Code). You'll see lines like:

```
ANTHROPIC_API_KEY=your_anthropic_key_here
WALKSCORE_API_KEY=your_walkscore_key_here
...
```

Replace each placeholder with your actual API key. Save the file. Never share it — it contains credentials.

**LLM provider — you only need one of Anthropic or Groq:**

- **Anthropic** (default, best email quality): Set `ANTHROPIC_API_KEY`. Costs ~$0.01–0.05/lead.
- **Groq** (free tier, open-source models): Set `GROQ_API_KEY` and pass `"llm_provider": "groq"` in the pipeline request. Uses llama-3.3-70b for email and llama-3.1-8b for pain points.
- **Local LLM via Ollama** (advanced, no cloud cost): Install [Ollama](https://ollama.com), pull a model (`ollama pull llama3`), and point the provider to `http://localhost:11434/v1`. It uses the same OpenAI-compatible API as Groq.

### Step 7: Start the backend server

With your virtual environment active, run:

```
uvicorn backend.main:app --reload
```

You should see:

```
INFO:     Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)
INFO:     Started reloader process...
```

Leave this terminal window open. The backend is now running.

### Step 8: Open the frontend

Open a file browser, navigate to `GTM_Automation_Tool/frontend/`, and double-click `index.html`. It opens in your browser and you're ready to go.

---

## 3. Running the Tool

### To process a single lead:

1. Fill in the form on the left:
   - **Contact Name** — the person you're reaching out to
   - **Email** — their work email
   - **Company** — the property management company name
   - **Property Address** — the specific property address (e.g., `838 NE 66th St`) — not the HQ
   - **City** — the city where the property is located
   - **State** — two-letter state code (e.g., `WA`, `CA`, `NY`)

2. Click **"Run Full Pipeline"** for scores, pain points, and a draft email. Or click **"Enrich Lead Data"** if you only want the raw market data without scoring or an email.

3. Wait 20–60 seconds. The tool is making ~10 API calls in parallel.

4. Results appear on the right: score dashboard, pain points, draft email, and all raw enrichment data below.

---

## 4. How to Enter the Lead Information

| Field | Format | Example | What happens if wrong |
|-------|--------|---------|----------------------|
| Contact Name | Full name | `Jordan Lee` | Nothing breaks; used in email greeting only |
| Email | Standard email | `jlee@greystar.com` | Used for records only |
| Company | Public company name | `Greystar` or `Greystar Real Estate Partners` | Affects news search and Wikipedia — be as specific as you know |
| Property Address | Street number + name only | `1600 Vine St` | Don't include city/state here. Don't include Suite/Unit numbers — they can break geocoding |
| City | City name | `Los Angeles` | Must be a real US city. Enter parent city for suburbs (e.g., "Hollywood" → "Los Angeles") |
| State | 2-letter abbreviation, uppercase | `CA` | Invalid state = Census and FRED calls fail |

**Tip:** If the property is a large apartment complex, use the main gate address, not a unit address. For companies managing multiple properties, enter the address most relevant to your pitch.

---

## 5. Reading the Output

### Score Dashboard

Five cards, each with a color-coded grade:

| Color | Grade | Score | What it means |
|-------|-------|-------|---------------|
| Green | A | 75–100 | Strong ICP match — prioritize immediately |
| Yellow | B | 60–74 | Good fit — high-priority sequence |
| Orange | C | 45–59 | Qualified — standard sequence |
| Red | D | 30–44 | Weak fit — low touch or hold |
| Gray | F | 0–29 | Not ICP — skip |

The five scores:

- **Lead Score** — the overall 0–100 number. This is the one to use for prioritization. A and B go to outreach today; C goes into a slower sequence; D and F are deprioritized.
- **Demand** — how active is the rental market at this location? High demand means the property manager is flooded with inquiries.
- **Friction** — how hard is this property to operate? High friction (bad weather, high crime) means more maintenance calls, more tenant communication, more automation value. High friction = better lead for us.
- **Scale** — how big is the property? Large apartment complex scores high. Single-family rental scores low.
- **Opportunity** — is there a specific reason to reach out now? Driven by news signals, Google rating, and vacancy urgency.

Each card also shows the individual signals driving it — so if a score looks wrong, you can see exactly which data point is pulling it up or down.

### Pain Points

Below the scores, you'll see a list of specific operational problems the tool identified for this property. Each has a severity (HIGH or MEDIUM) and a data-backed description.

These are your talking points. Use them in the email or call — they're grounded in real data, not generic assumptions.

**Example:**
> **[HIGH] Tight Market — Speed Wins Leases**
> A 3.4% vacancy rate with 54% renters means fierce competition for units. The first team to respond wins the lease. EliseAI's instant AI engagement converts leads before competitors do.

### The Outreach Email

Below the pain points, you'll find a draft email with subject line and body. Before you send it:

1. Read the whole thing end-to-end.
2. Check that any numbers (rating, vacancy rate, Walk Score) match what you see in the score dashboard.
3. Add any personal context you have (previous conversations, mutual connections).
4. The email is signed from Alex Chen, AE, EliseAI — update this to your actual name.

Click into the text, select all, copy, and paste into Gmail, Outreach, Apollo, or wherever you send.

---

## 6. When Data Is Missing

Not every API returns data for every city or property. That's normal — the tool handles it gracefully.

| What you see | Why | What to do |
|-------------|-----|------------|
| Crime data missing | Small towns often lack FBI agency data | Ignore — friction score runs on weather only |
| Walk Score missing | Geocoding failed (address not found) | Try a slightly different address format and re-run |
| Google rating not shown | Property isn't registered on Google Maps | Skip — opportunity score uses other signals |
| Vacancy rate is state-level | FRED only publishes state data | Treat as a market proxy, not a property-specific number |
| "No relevant news found" | Company is private or very small | Common — use market and property signals as your pitch angle |
| Score shows "available_weight: 0.45" | Only 45% of signals were retrievable | Still valid — the score is built on what it actually knows |

---

## 7. Running Multiple Leads

### Option A: One at a time (recommended)

Export your lead list from Salesforce or HubSpot as a CSV. Run leads one at a time through the UI. All processed leads are saved automatically to `data/leads/` and appear in the history panel.

### Option B: Direct API calls (for technical users)

You can call the backend directly with `curl` or any HTTP client:

```bash
curl -X POST http://localhost:8000/pipeline \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Jordan Lee",
    "email": "jlee@example.com",
    "company": "Greystar",
    "property_address": "1600 Vine St",
    "city": "Los Angeles",
    "state": "CA"
  }'
```

To run this on a schedule, a developer can set up a cron job or GitHub Action that reads from a CSV and posts each row. For batches larger than 50 leads, add a 2-second delay between requests to stay within rate limits.

### Option C: Google Sheets button (planned)

A future version will include a Google Apps Script that adds a "Run Pipeline" button directly to a Google Sheet. No terminal needed — paste leads in, click the button, get scored results in new columns. See Doc 4 for the rollout plan.

---

## 8. Troubleshooting

**The tool is loading forever / nothing comes back.**

Check the terminal window where you ran `uvicorn`. If you see error messages, the backend crashed. Common causes:
- Missing API key: look for `Key required` in the terminal output
- Network timeout: one API took too long. Usually resolves on retry.
- Python package missing: run `pip install -r requirements.txt` again.

---

**"Connection refused" error in the browser.**

The backend isn't running. Navigate to the project folder in your terminal, activate the virtual environment, and run `uvicorn backend.main:app --reload` again.

---

**The score seems too low for a lead I know is good.**

Check the `available_weight` on each sub-score. If it's below 0.5, fewer than half the signals were available — the score is working with limited data. Most common causes:
- Geocoding failed → all location-based scores (Walk, climate, crime) are missing
- Small city with no FBI data → friction runs on weather only

Try re-entering the address with the full street name spelled out.

---

**The outreach email mentions wrong numbers.**

The AI uses data from the enrichment run. If the enrichment returned unexpected data (e.g., a Walk Score from a slightly wrong address), the email may reference it. Check the raw enrichment data at the bottom of the results panel. If something looks off, re-run with a corrected address.

---

**"Walk Score unavailable" even with a correct address.**

WalkScore needs a valid lat/lon, which comes from geocoding. If geocoding failed, WalkScore can't run. Try these address variations:
- `838 NE 66th St` → `838 Northeast 66th Street`
- Remove apartment or suite numbers
- Use the main building address, not a specific unit

---

**Error about the Anthropic API.**

Check that `ANTHROPIC_API_KEY` in your `.env` file is correct with no extra spaces, then restart the server. If it says "insufficient quota," your Anthropic account may need a credit card on file.

---

**Can I run this without an Anthropic API key?**

Yes, partially. Enrichment and scoring still run. Pain point and email generation are skipped (they return empty). You'll still get the Lead Score and all enrichment data — just no draft email. Alternatively, set up a free Groq key and use `"llm_provider": "groq"` to get the full output at no cost.

---

**Where are my results saved?**

All processed leads are saved in `GTM_Automation_Tool/data/leads/` as JSON files. The summary index is at `data/index.json`. The History panel in the UI shows all saved leads.

---

**How do I clear old leads?**

Delete the `.json` files from `data/leads/` and replace the contents of `data/index.json` with `[]`. This doesn't affect any API keys or settings.
