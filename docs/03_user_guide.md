# EliseAI GTM Automation Tool — User Guide

> **Audience:** SDRs and SDR managers who run this tool daily.
> **Assumption:** You have never used Python or the command line before. We'll cover everything.

---

## 1. Prerequisites — What You Need Before Starting

You need API keys for the following services. All of them are free to start.

| Service | What it does | Where to get a key | Free tier |
|---------|-------------|-------------------|-----------|
| **Anthropic** *(or Groq — see below)* | Writes the outreach email and pain points | [console.anthropic.com](https://console.anthropic.com) → API Keys | Pay-per-use; ~$0.01–0.05 per lead |
| **Groq** *(free alternative to Anthropic)* | Same LLM steps — pain points and email — using open-source models | [console.groq.com](https://console.groq.com) → API Keys | Generous free tier; no credit card required |
| **WalkScore** | Walk/transit/bike scores | [walkscore.com/professional/api.php](https://www.walkscore.com/professional/api.php) | 5,000 req/day free |
| **Intellipins** | Property data and building type | [intellipins.com](https://intellipins.com) → Developer | Contact for pricing |
| **Google Places** | Property ratings and reviews | [console.cloud.google.com](https://console.cloud.google.com) → APIs & Services → Places API | $200 free credit/month |
| **NewsAPI** | Company news | [newsapi.org/register](https://newsapi.org/register) | 100 req/day free |
| **FRED (St. Louis Fed)** | Vacancy rates | [fred.stlouisfed.org/docs/api/api_key.html](https://fred.stlouisfed.org/docs/api/api_key.html) | Free |
| **FBI API** | Crime data | [api.data.gov/signup/](https://api.data.gov/signup/) → Request Key | Free |
| **Census Bureau** | Population and income | [api.census.gov/data/key_signup.html](https://api.census.gov/data/key_signup.html) | Free (optional but recommended) |

---

## 2. Setup — Step by Step

### Step 1: Install Python

Check if Python is already installed. Open Terminal (Mac) or Command Prompt (Windows) and type:

```
python3 --version
```

If you see something like `Python 3.11.4`, you're good. If you get an error, download Python from **python.org/downloads** and install it. Accept all defaults. Make sure to check "Add Python to PATH" on Windows.

### Step 2: Download the project

If you received a ZIP file, unzip it. Place the folder somewhere easy to find, like your Desktop. You should see a folder called `GTM_Automation_Tool`.

### Step 3: Open Terminal and navigate to the project

**Mac:**
1. Open Terminal (search "Terminal" in Spotlight)
2. Type: `cd ~/Desktop/GTM_Automation_Tool`
3. Press Enter

**Windows:**
1. Open Command Prompt (search "cmd" in Start menu)
2. Type: `cd C:\Users\YourName\Desktop\GTM_Automation_Tool`
3. Press Enter

### Step 4: Create a virtual environment

This keeps the tool's dependencies separate from your other software.

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

You should see `(venv)` appear at the start of your command line. This means it worked.

### Step 5: Install dependencies

```
pip install -r requirements.txt
```

Wait for everything to finish downloading. This takes 1–3 minutes the first time.

### Step 6: Add your API keys

In the project folder, find the file called `.env` or `.env.example` (and rename `.env.example` to `.env` if it exists). Open it in any text editor (Notepad, TextEdit, VS Code). You'll see lines like:

```
ANTHROPIC_API_KEY=your_anthropic_key_here
WALKSCORE_API_KEY=your_walkscore_key_here
INTELLIPINS_KEY=your_intellipins_key_here
GOOGLE_PLACES_API_KEY=your_google_places_key_here
NEWS_API_KEY=your_newsapi_key_here
FRED_API_KEY=your_fred_key_here
FBI_API_KEY=your_fbi_key_here
CENSUS_API_KEY=your_census_key_here
```

Replace each `your_..._key_here` with your actual API key. Save the file. Never share this file or commit it to Git — it is gitignored by default.

**LLM provider — you only need one of Anthropic or Groq:**

- **Anthropic** (default): best email quality. Set `ANTHROPIC_API_KEY`. Costs ~$0.01–0.05/lead.
- **Groq** (free tier): open-source models (llama-3.3-70b for email, llama-3.1-8b for pain points). Set `GROQ_API_KEY` and pass `"llm_provider": "groq"` in the pipeline request body.
- **Local LLM via Ollama** (no cloud cost, advanced): install [Ollama](https://ollama.com), pull a model (`ollama pull llama3`), and add a third provider branch to `backend/llm.py`. Ollama exposes an OpenAI-compatible REST API at `http://localhost:11434/v1` — the code pattern is identical to the Groq integration.

### Step 7: Start the backend server

Make sure your virtual environment is active (you see `(venv)` in the terminal), then run:

```
uvicorn backend.main:app --reload
```

You should see output like:

```
INFO:     Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)
INFO:     Started reloader process...
```

Leave this terminal window open. The backend is now running.

### Step 8: Open the frontend

Open a file browser and navigate to `GTM_Automation_Tool/frontend/`. Double-click `index.html`. It should open in your web browser.

You're ready to use the tool.

---

## 3. How to Run the Tool

### To process a single lead:

1. Fill in the form on the left side of the screen:
   - **Contact Name** — the person you're reaching out to
   - **Email** — their work email
   - **Company** — the property management company name
   - **Property Address** — the specific property address (e.g., `838 NE 66th St`), not the HQ
   - **City** — the city where the property is located
   - **State** — two-letter state code (e.g., `WA`, `CA`, `NY`)

2. Click **"Run Full Pipeline"** to get scores, pain points, and a draft email.

   *Or* click **"Enrich Lead Data"** if you only want the raw market data without scoring or an email.

3. Wait 20–60 seconds. The tool is making ~10 API calls in parallel. The loading indicator will spin.

4. Results appear on the right side of the screen. The full pipeline shows:
   - Score dashboard (color-coded grades)
   - Pain points list
   - Draft outreach email
   - All raw enrichment data below

---

## 4. Input Format

| Field | Format | Example | What happens if wrong |
|-------|--------|---------|----------------------|
| Contact Name | Full name, any capitalization | `Jordan Lee` | Nothing breaks; used in email greeting only |
| Email | Standard email format | `jlee@greystar.com` | Used for records only; no validation |
| Company | The company name as it appears publicly | `Greystar` or `Greystar Real Estate Partners` | Affects news search and Wikipedia lookup — be as specific or general as you know |
| Property Address | Street number + street name only | `1600 Vine St` | **Do not include city/state here.** They have separate fields. Do not include Suite or Unit numbers — they can confuse geocoding. |
| City | City name | `Los Angeles` | Must match a real US city. Suburbs and neighborhoods may not have Census data (e.g., "Hollywood" should be entered as "Los Angeles"). |
| State | 2-letter state abbreviation | `CA` | Must be uppercase. Invalid state = Census and FRED calls return errors. |

**Tip on addresses:** If the property is a large apartment complex, use the main gate address, not a unit address. If the company runs multiple properties, enter the address of the property most relevant to your pitch.

---

## 5. Reading the Output

### Score Dashboard

The score dashboard shows five cards. Each uses a color-coded badge:

| Color | Grade | Score | Meaning |
|-------|-------|-------|---------|
| 🟢 Green | A | 75–100 | Strong ICP match — prioritize immediately |
| 🟡 Yellow | B | 60–74 | Good fit — high-priority sequence |
| 🟠 Orange | C | 45–59 | Qualified — standard sequence |
| 🔴 Red | D | 30–44 | Weak fit — low touch or hold |
| ⚫ Gray | F | 0–29 | Not ICP — do not contact |

**The five scores explained:**

- **Lead Score** — the overall number (0–100). This is the one to use for prioritization. A and B leads go to outreach today; C leads go into a slower sequence; D and F leads are deprioritized.

- **Demand** — how intense is the rental market at this location? High demand = property managers are getting flooded with inquiries.

- **Friction** — how operationally difficult is this property to run? High friction (weather, crime) = more maintenance calls, more tenant communication, more automation value.

- **Scale** — how big is the property? Large apartment complex = high score. Small SFR = low score.

- **Opportunity** — is there a specific trigger that makes this company likely to act now? Includes news sentiment, Google rating, vacancy urgency.

Each card also shows component breakdowns. For example, the Demand card might show:
- Walk Score: 97/100
- Renter %: 54.8/100
- Transit: 65/100

These tell you which signals are driving the score.

### Pain Points

Below the scores, you'll see a list of pain points — specific operational problems this property likely has. Each is labeled with a severity (HIGH, MEDIUM) and sourced either from deterministic rules (`rule`) or from the AI (`llm`).

Use these as your talking points. They're grounded in data from the APIs — the description always includes specific numbers.

**Example:**
> **[HIGH] Tight Market — Speed Wins Leases**
> A 3.4% vacancy rate with 54% renters means fierce competition for units. The first team to respond wins the lease. EliseAI's instant AI engagement converts leads before competitors do.

### The Outreach Email

Below the pain points, you'll see a draft email with:
- **Subject line** — specific to this company and location
- **Body** — references real data points from the enrichment

**Before sending:**
1. Read the subject line and body end-to-end.
2. Check that any numbers mentioned (rating, vacancy rate, Walk Score) match what you see in the score dashboard. The AI uses the data, but occasionally formats it differently.
3. Add any personal context you have about this company (if you know them from a previous conversation, mention it).
4. The email is signed from Alex Chen, AE, EliseAI — update this to your actual name.

**Copy the email:** Click into the text, select all, and copy. Paste into Gmail, Outreach, Apollo, or wherever you send.

---

## 6. Understanding Data Gaps

Sometimes a score will show as `0` or a component will be missing. This is normal — not every API returns data for every city.

**Common gaps and what they mean:**

| What you see | Why | What to do |
|-------------|-----|------------|
| Crime data missing | Small towns often don't have FBI agency data | Ignore — friction score runs on weather only |
| Walk Score missing | Geocoding failed (address not found) | Try re-running with a slightly different address format |
| Google rating not shown | Property isn't registered as a business on Google Maps | Skip — opportunity score uses other signals |
| Vacancy rate is state-level | FRED only has state data | Treat as a market proxy, not property-specific |
| "No relevant news found" | Company is private or very small | Common — use other signals as your pitch angle |
| Score shows "available_weight: 0.45" | Only 45% of signals were retrievable | Still valid; the score is honest about what it knows |

---

## 7. Setting Up Automated Runs

### Option A: Manual batch (recommended for now)

Export your lead list as a CSV from Salesforce or HubSpot. Run leads one at a time through the UI. All processed leads are saved automatically to the `data/leads/` folder and appear in the history panel.

### Option B: Cron job (for technical users)

If you want to run a batch of leads automatically every morning, you can call the API directly. Each lead needs a POST request to `http://localhost:8000/pipeline`.

**Example using curl:**
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

To run this on a schedule, a developer can set up a cron job or GitHub Action that reads from a CSV and posts each row.

### Option C: Google Sheets button (planned)

A future iteration will include a Google Apps Script that adds a "Run Pipeline" button to a Google Sheet. You paste leads into the sheet, click the button, and scored results populate in new columns. This requires no terminal use. See Doc 4 for the rollout plan.

---

## 8. FAQ and Troubleshooting

**Q: The tool is loading forever / nothing comes back.**

Check the terminal window where you ran `uvicorn`. If you see error messages, the backend crashed. Common causes:
- Missing API key: look for `Key required` in the terminal output
- Network timeout: one API took too long. Usually resolves on retry.
- Python package missing: run `pip install -r requirements.txt` again.

---

**Q: I get a "Connection refused" error in the browser.**

The backend server isn't running. Go to your Terminal, navigate to the project folder, activate the virtual environment, and run `uvicorn backend.main:app --reload` again.

---

**Q: The score seems too low for a lead I know is good.**

Check the `available_weight` on each sub-score. If it's below 0.5, fewer than half the signals were available — the score is working with limited data. The most common causes:
- Geocoding failed (address not found) → all location-based scores (Walk, climate, crime) are missing
- Small city with no FBI data → Friction score runs on weather only
- Try re-entering the address with the full street name spelled out.

---

**Q: The outreach email mentions wrong numbers.**

The AI uses data from the enrichment run. If the enrichment returned stale or unexpected data (e.g., a cached Walk Score from a different address), the email may reference it. Check the raw enrichment data at the bottom of the results panel. If something looks wrong, re-run with a corrected address.

---

**Q: "Walk Score unavailable" even though I provided a correct address.**

WalkScore requires a valid lat/lon, which comes from geocoding. If geocoding fails, WalkScore can't run. The most common geocoding failure is an address not recognized by any of the four geocoders. Try variations:
- `838 NE 66th St` → `838 Northeast 66th Street`
- Remove apartment/suite numbers
- Use the main building address, not a specific unit

---

**Q: I see an error about the Anthropic API.**

Check that `ANTHROPIC_API_KEY` in your `.env` file is correct and has no extra spaces. Then restart the server. If the error says "insufficient quota," your Anthropic account may need a credit card on file.

---

**Q: Can I run this without the Anthropic API key?**

Yes, partially. The enrichment step and scoring will work. The pain point and email generation steps will be skipped (they'll return an empty result). You won't get a draft email, but you'll still get the Lead Score and enrichment data.

---

**Q: Where are my results saved?**

All processed leads are saved in `GTM_Automation_Tool/data/leads/` as JSON files. You can open them in any text editor. The summary index is at `data/index.json`. The History panel in the UI also shows all saved leads.

---

**Q: How do I clear old leads?**

Delete the `.json` files from `data/leads/` and clear the `data/index.json` file (replace its contents with `[]`). This does not affect any API keys or settings.
