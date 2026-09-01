# ⚡ Company Intelligence Agent

> **LH2 AI Labs · Founder's Office — Automation Intern Task**
>
> An end-to-end autonomous pipeline: companies go in, structured judgment comes out, and it keeps itself running.

![Python](https://img.shields.io/badge/Python-3.11-blue?logo=python)
![FastAPI](https://img.shields.io/badge/FastAPI-0.104-green?logo=fastapi)
![Docker](https://img.shields.io/badge/Docker-Containerized-blue?logo=docker)
![License](https://img.shields.io/badge/License-MIT-yellow)

---

## What It Does

This is a fully automated **company intelligence pipeline** that:

1. **Sources** company names from a Google Sheet (auto-detects new rows)
2. **Enriches** each company with 3 independent signals:
   - 🌐 **Wikipedia API** — company description, industry, and overview (HTTP)
   - 🐙 **GitHub Search API** — open-source presence, top repos, tech stack (HTTP)
   - 🔍 **DuckDuckGo via Selenium** — real browser automation scraping search results
3. **Persists** all data in a SQLite database (not memory, not sheets)
4. **Judges** via Groq LLM (Llama 3 70B) — produces structured verdicts with fit assessment, confidence score, evidence-based reasoning, and follow-up questions
5. **Syncs back** verdicts to the Google Sheet with proper Service Account authentication
6. **Runs itself** on a configurable schedule (APScheduler) + on-demand via API
7. **Ships** as a Docker container, deployed to Render.com with a live URL
8. **Wired to GitHub** with CI (lint + test on every push) and a separate workflow to trigger the pipeline automatically

---

## Why These Choices

| Decision | Rationale |
|---|---|
| **FastAPI** over Flask | Async support, auto-generated OpenAPI docs, modern Python |
| **SQLite** over Postgres | Zero-cost, zero-config, file-based — perfect for this scale |
| **Groq** over OpenAI | Generous free tier (30 RPM), blazing fast Llama 3 inference |
| **Selenium** for browser signal | Task explicitly requires "real browser automation, not plain HTTP" |
| **DuckDuckGo** over Google | More bot-friendly, avoids CAPTCHAs, reliable for scraping |
| **APScheduler** | In-process scheduler, no external Redis/Celery needed |
| **Render.com** | Free tier with Docker support, auto-deploy from GitHub |

---

## Architecture

```
Google Sheet ──▶ FastAPI Pipeline ──▶ SQLite DB ──▶ LLM Judge ──▶ Sheet
                      │
               ┌──────┼──────┐
               ▼      ▼      ▼
          Wikipedia  GitHub  Selenium
           (HTTP)   (HTTP)  (Browser)
```

**API Endpoints:**
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/` | Dashboard UI |
| POST | `/api/run` | Trigger pipeline on demand |
| GET | `/api/status` | Pipeline status + schedule info |
| GET | `/api/companies` | All companies with verdicts |
| GET | `/api/companies/{name}` | Single company details + signals |
| GET | `/health` | Health check |
| GET | `/docs` | Swagger UI (auto-generated) |

---

## Setup Guide

### Prerequisites
- Python 3.11+
- A Google account
- A Groq account (free)

### Step 1: Google Cloud Service Account

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project (or use an existing one)
3. Navigate to **APIs & Services → Library**
4. Enable **Google Sheets API** and **Google Drive API**
5. Go to **APIs & Services → Credentials**
6. Click **Create Credentials → Service Account**
7. Give it a name (e.g., `company-intel-agent`), click **Done**
8. Click on the service account → **Keys** tab → **Add Key → Create new key → JSON**
9. Download the JSON key file
10. Copy the entire JSON content — you'll paste it as an env var

### Step 2: Create & Share Google Sheet

1. Create a new Google Sheet in your Google Drive
2. Copy the Sheet ID from the URL: `https://docs.google.com/spreadsheets/d/{SHEET_ID}/edit`
3. Share the sheet with the service account email (found in the JSON key file as `client_email`). Give it **Editor** access.

### Step 3: Get Groq API Key

1. Go to [console.groq.com](https://console.groq.com)
2. Sign up (free)
3. Navigate to **API Keys** and create a new key

### Step 4: Configure Environment

```bash
# Copy the example env file
cp .env.example .env

# Edit .env with your values:
# - Paste the entire JSON key as GOOGLE_CREDENTIALS_JSON (on one line)
# - Set GOOGLE_SHEET_ID
# - Set GROQ_API_KEY
```

### Step 5: Install & Run

```bash
# Install dependencies
pip install -r requirements.txt

# Populate the Google Sheet with companies
python setup_sheet.py

# Start the app
python -m app.main
```

The dashboard will be available at `http://localhost:8000`

### Step 6: Run the Pipeline

- **Dashboard**: Click "Run Pipeline" button
- **API**: `curl -X POST http://localhost:8000/api/run`
- **Auto**: Pipeline runs automatically every 30 minutes

---

## Deployment (Render.com)

1. Push code to GitHub
2. Go to [render.com](https://render.com) → **New → Web Service**
3. Connect your GitHub repo
4. Settings:
   - **Runtime**: Docker
   - **Branch**: main
   - **Instance Type**: Free
5. Add environment variables:
   - `GOOGLE_CREDENTIALS_JSON`
   - `GOOGLE_SHEET_ID`
   - `GROQ_API_KEY`
   - `DEPLOYED_URL` (your Render URL, e.g., `https://your-app.onrender.com`)
6. Deploy!

---

## GitHub Actions

### CI Workflow (`.github/workflows/ci.yml`)
- Triggers on **every push** to any branch
- Runs: `ruff` linting + `pytest` unit tests

### Pipeline Trigger (`.github/workflows/trigger_pipeline.yml`)
- **Scheduled**: Runs every 6 hours via cron
- **Manual**: Trigger from GitHub Actions UI → "Run workflow"
- Calls the deployed app's `/api/run` endpoint — no human clicking needed
- Requires `DEPLOYED_URL` secret in GitHub repo settings

---

## Project Structure

```
├── app/
│   ├── main.py              # FastAPI app, routes, scheduler
│   ├── config.py             # Environment configuration
│   ├── database.py           # SQLite schema + CRUD
│   ├── sheets.py             # Google Sheets read/write
│   ├── pipeline.py           # Pipeline orchestrator
│   ├── judge.py              # Groq LLM verdict engine
│   └── enrichment/
│       ├── wikipedia.py      # Wikipedia API (HTTP)
│       ├── github_search.py  # GitHub Search API (HTTP)
│       └── browser.py        # Selenium browser automation
├── templates/
│   └── index.html            # Dashboard UI
├── static/
│   └── style.css             # Premium dark-mode styles
├── tests/
│   └── test_pipeline.py      # Unit tests
├── setup_sheet.py             # One-time sheet population script
├── Dockerfile                 # Container definition
├── docker-compose.yml         # Local Docker setup
├── .github/workflows/
│   ├── ci.yml                # CI on every push
│   └── trigger_pipeline.yml  # Scheduled pipeline trigger
├── requirements.txt
├── .env.example
└── README.md
```

---

## Free Tier Verification

| Service | Free Tier | Our Usage |
|---------|-----------|-----------|
| Google Sheets API | 500 req/100sec | ~20 req/run |
| Wikipedia API | Unlimited | ~12 req/run |
| GitHub Search API | 10 req/min (unauth) | ~12 req/run |
| Groq (Llama 3 70B) | 30 RPM, 14.4K/day | ~12 req/run |
| Render.com | 750 hrs/month | 1 instance |
| GitHub Actions | 2000 min/month | ~5 min/run |
| SQLite | Free (built-in) | ∞ |
| Selenium/Chromium | Free (open source) | ∞ |

**Total cost: $0.00** ✅

---

## License

MIT — Built for LH2 AI Labs Founder's Office Automation Intern application.
