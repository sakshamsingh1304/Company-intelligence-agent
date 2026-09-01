"""
Centralized configuration — reads from environment variables / .env file.
"""
import os
from dotenv import load_dotenv

load_dotenv()

# ── Google Sheets ──────────────────────────────────────────────
GOOGLE_CREDENTIALS_JSON = os.getenv("GOOGLE_CREDENTIALS_JSON", "")
GOOGLE_SHEET_ID = os.getenv("GOOGLE_SHEET_ID", "")
GOOGLE_SHEET_NAME = os.getenv("GOOGLE_SHEET_NAME", "Sheet1")

# ── Google Gemini LLM ─────────────────────────────────────────
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.6-flash")

# ── Database ───────────────────────────────────────────────────
DATABASE_PATH = os.getenv("DATABASE_PATH", "data/companies.db")

# ── Scheduler ──────────────────────────────────────────────────
PIPELINE_INTERVAL_MINUTES = int(os.getenv("PIPELINE_INTERVAL_MINUTES", "30"))

# ── App ────────────────────────────────────────────────────────
APP_HOST = os.getenv("APP_HOST", "0.0.0.0")
APP_PORT = int(os.getenv("APP_PORT", "8000"))
DEPLOYED_URL = os.getenv("DEPLOYED_URL", "http://localhost:8000")
