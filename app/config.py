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

# ── Groq LLM ─────────────────────────────────────────
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GROQ_MODEL = os.getenv("GROQ_MODEL", "openai/gpt-oss-120b")

# ── Database ───────────────────────────────────────────────────
DATABASE_PATH = os.getenv("DATABASE_PATH", "data/companies.db")

# ── Scheduler ──────────────────────────────────────────────────
PIPELINE_INTERVAL_MINUTES = int(os.getenv("PIPELINE_INTERVAL_MINUTES", "30"))

# ── App ────────────────────────────────────────────────────────
APP_HOST = os.getenv("APP_HOST", "0.0.0.0")
APP_PORT = int(os.getenv("APP_PORT", "8000"))
DEPLOYED_URL = os.getenv("DEPLOYED_URL", "http://localhost:8000")
