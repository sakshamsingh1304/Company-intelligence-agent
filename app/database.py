"""
SQLite database layer — schema init + CRUD helpers.
Results persist across restarts (satisfies Task §3: real database).
"""
import sqlite3
import json
import os
from datetime import datetime, timezone

from app.config import DATABASE_PATH


# ── Connection helpers ─────────────────────────────────────────

def _ensure_dir():
    os.makedirs(os.path.dirname(DATABASE_PATH) or ".", exist_ok=True)


def get_connection() -> sqlite3.Connection:
    """Return a connection with Row factory enabled."""
    _ensure_dir()
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_db():
    """Create tables if they don't exist."""
    conn = get_connection()
    c = conn.cursor()

    c.execute("""
        CREATE TABLE IF NOT EXISTS companies (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            name        TEXT    UNIQUE NOT NULL,
            sheet_row   INTEGER,
            status      TEXT    DEFAULT 'pending',
            created_at  TEXT    DEFAULT (datetime('now')),
            updated_at  TEXT    DEFAULT (datetime('now'))
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS enrichment_signals (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            company_id  INTEGER NOT NULL,
            source      TEXT    NOT NULL,
            signal_data TEXT    NOT NULL,
            fetched_at  TEXT    DEFAULT (datetime('now')),
            FOREIGN KEY (company_id) REFERENCES companies(id)
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS verdicts (
            id                 INTEGER PRIMARY KEY AUTOINCREMENT,
            company_id         INTEGER NOT NULL,
            fit                TEXT,
            confidence         REAL,
            reasoning          TEXT,
            follow_up_question TEXT,
            judged_at          TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (company_id) REFERENCES companies(id)
        )
    """)

    conn.commit()
    conn.close()


# ── Company CRUD ───────────────────────────────────────────────

def upsert_company(name: str, sheet_row: int) -> int:
    """Insert or ignore a company. Returns its id."""
    conn = get_connection()
    c = conn.cursor()
    c.execute(
        "INSERT OR IGNORE INTO companies (name, sheet_row) VALUES (?, ?)",
        (name, sheet_row),
    )
    conn.commit()
    # Fetch id (handles both insert & existing)
    c.execute("SELECT id FROM companies WHERE name = ?", (name,))
    row = c.fetchone()
    company_id = row["id"]
    conn.close()
    return company_id


def get_pending_companies() -> list[dict]:
    """Return companies that haven't been fully processed yet."""
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM companies WHERE status IN ('pending', 'enriched') ORDER BY id"
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_all_companies() -> list[dict]:
    """Return every company with its latest verdict (if any)."""
    conn = get_connection()
    rows = conn.execute("""
        SELECT c.*, v.fit, v.confidence, v.reasoning, v.follow_up_question, v.judged_at
        FROM companies c
        LEFT JOIN verdicts v ON v.company_id = c.id
            AND v.id = (SELECT MAX(v2.id) FROM verdicts v2 WHERE v2.company_id = c.id)
        ORDER BY c.id
    """).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_company_by_name(name: str) -> dict | None:
    """Look up a single company by exact name."""
    conn = get_connection()
    row = conn.execute(
        """
        SELECT c.*, v.fit, v.confidence, v.reasoning, v.follow_up_question, v.judged_at
        FROM companies c
        LEFT JOIN verdicts v ON v.company_id = c.id
            AND v.id = (SELECT MAX(v2.id) FROM verdicts v2 WHERE v2.company_id = c.id)
        WHERE c.name = ?
        """,
        (name,),
    ).fetchone()
    conn.close()
    return dict(row) if row else None


def update_company_status(company_id: int, status: str):
    conn = get_connection()
    conn.execute(
        "UPDATE companies SET status = ?, updated_at = datetime('now') WHERE id = ?",
        (status, company_id),
    )
    conn.commit()
    conn.close()


# ── Enrichment CRUD ────────────────────────────────────────────

def save_enrichment(company_id: int, source: str, signal_data: dict):
    """Persist one enrichment signal (JSON-serialized)."""
    conn = get_connection()
    conn.execute(
        "INSERT INTO enrichment_signals (company_id, source, signal_data) VALUES (?, ?, ?)",
        (company_id, source, json.dumps(signal_data)),
    )
    conn.commit()
    conn.close()


def get_enrichments(company_id: int) -> list[dict]:
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM enrichment_signals WHERE company_id = ? ORDER BY id",
        (company_id,),
    ).fetchall()
    conn.close()
    results = []
    for r in rows:
        d = dict(r)
        d["signal_data"] = json.loads(d["signal_data"])
        results.append(d)
    return results


# ── Verdict CRUD ───────────────────────────────────────────────

def save_verdict(company_id: int, fit: str, confidence: float,
                 reasoning: str, follow_up_question: str):
    conn = get_connection()
    conn.execute(
        """INSERT INTO verdicts (company_id, fit, confidence, reasoning, follow_up_question)
           VALUES (?, ?, ?, ?, ?)""",
        (company_id, fit, confidence, reasoning, follow_up_question),
    )
    conn.commit()
    conn.close()


def get_verdict(company_id: int) -> dict | None:
    conn = get_connection()
    row = conn.execute(
        "SELECT * FROM verdicts WHERE company_id = ? ORDER BY id DESC LIMIT 1",
        (company_id,),
    ).fetchone()
    conn.close()
    return dict(row) if row else None


# ── Stats ──────────────────────────────────────────────────────

def get_stats() -> dict:
    conn = get_connection()
    total = conn.execute("SELECT COUNT(*) as cnt FROM companies").fetchone()["cnt"]
    processed = conn.execute(
        "SELECT COUNT(*) as cnt FROM companies WHERE status = 'completed'"
    ).fetchone()["cnt"]
    pending = conn.execute(
        "SELECT COUNT(*) as cnt FROM companies WHERE status = 'pending'"
    ).fetchone()["cnt"]
    errors = conn.execute(
        "SELECT COUNT(*) as cnt FROM companies WHERE status = 'error'"
    ).fetchone()["cnt"]
    conn.close()
    return {
        "total": total,
        "processed": processed,
        "pending": pending,
        "errors": errors,
    }
