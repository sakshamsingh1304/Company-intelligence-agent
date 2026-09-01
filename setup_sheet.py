"""
One-time setup script to populate the Google Sheet with company names.
Run this AFTER setting up your Service Account and .env file.

Usage:
    python setup_sheet.py
"""
import json
import os
import sys

from dotenv import load_dotenv
import gspread
from google.oauth2.service_account import Credentials

load_dotenv()

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

HEADER_ROW = [
    "Company Name", "Status", "Fit", "Confidence",
    "Reasoning", "Follow-up Question", "Last Updated",
]

# ── Companies to add ───────────────────────────────────────────
COMPANIES = [
    "UpGrad",
    "Sony",
    "HCLTech",
    "Hlmando",
    "Accenture",
    "Opus",
    "Bosleo",
    "Infosys",
    "Wipro",
    "Zoho",
    "Freshworks",
    "Razorpay",
]


def main():
    creds_json = os.getenv("GOOGLE_CREDENTIALS_JSON")
    sheet_id = os.getenv("GOOGLE_SHEET_ID")

    if not creds_json:
        print("❌ GOOGLE_CREDENTIALS_JSON is not set in .env")
        sys.exit(1)
    if not sheet_id:
        print("❌ GOOGLE_SHEET_ID is not set in .env")
        sys.exit(1)

    print("🔐 Authenticating with Google...")
    creds_dict = json.loads(creds_json)
    creds = Credentials.from_service_account_info(creds_dict, scopes=SCOPES)
    gc = gspread.authorize(creds)

    print(f"📄 Opening sheet: {sheet_id}")
    spreadsheet = gc.open_by_key(sheet_id)
    ws = spreadsheet.sheet1

    # Write headers
    print("📝 Writing headers...")
    ws.update("A1:G1", [HEADER_ROW])

    # Format header row (bold)
    ws.format("A1:G1", {
        "textFormat": {"bold": True, "fontSize": 11},
        "backgroundColor": {"red": 0.15, "green": 0.15, "blue": 0.25},
        "horizontalAlignment": "CENTER",
    })

    # Write company names
    print(f"🏢 Adding {len(COMPANIES)} companies...")
    rows = [[name] for name in COMPANIES]
    ws.update(f"A2:A{len(COMPANIES) + 1}", rows)

    # Auto-resize columns
    ws.columns_auto_resize(0, 7)

    print(f"\n✅ Done! {len(COMPANIES)} companies added to the sheet.")
    print(f"🔗 Sheet URL: https://docs.google.com/spreadsheets/d/{sheet_id}")
    print("\nCompanies added:")
    for i, name in enumerate(COMPANIES, 1):
        print(f"  {i:2d}. {name}")


if __name__ == "__main__":
    main()
