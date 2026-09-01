"""
Google Sheets integration — read company list, write verdicts back.
Authenticated via Service Account (Task §1 & §5).
"""
import json
import logging

import gspread
from google.oauth2.service_account import Credentials

from app.config import GOOGLE_CREDENTIALS_JSON, GOOGLE_SHEET_ID, GOOGLE_SHEET_NAME

logger = logging.getLogger(__name__)

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

# ── Column layout ──────────────────────────────────────────────
# A: Company Name | B: Status | C: Fit | D: Confidence
# E: Reasoning | F: Follow-up Question | G: Last Updated
HEADER_ROW = [
    "Company Name", "Status", "Fit", "Confidence",
    "Reasoning", "Follow-up Question", "Last Updated",
]


def _get_client() -> gspread.Client:
    """Authenticate and return a gspread client."""
    if not GOOGLE_CREDENTIALS_JSON:
        raise RuntimeError("GOOGLE_CREDENTIALS_JSON env var is not set")
    creds_dict = json.loads(GOOGLE_CREDENTIALS_JSON)
    creds = Credentials.from_service_account_info(creds_dict, scopes=SCOPES)
    return gspread.authorize(creds)


def _get_worksheet() -> gspread.Worksheet:
    """Open the configured worksheet."""
    gc = _get_client()
    spreadsheet = gc.open_by_key(GOOGLE_SHEET_ID)
    return spreadsheet.worksheet(GOOGLE_SHEET_NAME)


def ensure_headers(ws: gspread.Worksheet):
    """Make sure row 1 has the expected headers."""
    existing = ws.row_values(1)
    if existing != HEADER_ROW:
        ws.update("A1:G1", [HEADER_ROW])
        logger.info("Sheet headers initialized")


# ── Read ───────────────────────────────────────────────────────

def fetch_companies() -> list[dict]:
    """
    Read all company rows from the Sheet.
    Returns list of {name, sheet_row, status}.
    New rows (no status) are treated as unprocessed.
    """
    ws = _get_worksheet()
    ensure_headers(ws)

    all_values = ws.get_all_values()
    companies = []

    for idx, row in enumerate(all_values[1:], start=2):  # skip header, 1-indexed
        name = row[0].strip() if len(row) > 0 else ""
        status = row[1].strip() if len(row) > 1 else ""
        if name:
            companies.append({
                "name": name,
                "sheet_row": idx,
                "status": status,
            })

    logger.info(f"Fetched {len(companies)} companies from Sheet")
    return companies


# ── Write verdict back ─────────────────────────────────────────

def sync_verdict(sheet_row: int, status: str, fit: str,
                 confidence: float, reasoning: str,
                 follow_up_question: str, updated_at: str):
    """
    Write the LLM verdict back into the Sheet for a specific row.
    Columns B–G get updated.
    """
    ws = _get_worksheet()
    ws.update(f"B{sheet_row}:G{sheet_row}", [[
        status,
        fit,
        str(round(confidence, 2)),
        reasoning[:500],  # Sheets cell limit safety
        follow_up_question,
        updated_at,
    ]])
    logger.info(f"Synced verdict for row {sheet_row}")


def sync_status(sheet_row: int, status: str):
    """Update just the status column for a row."""
    ws = _get_worksheet()
    ws.update(f"B{sheet_row}", [[status]])
