"""
Unit tests for the pipeline — database operations and config validation.
These tests don't require external APIs (Google Sheets, Groq, Selenium).
"""
import os
import json
import tempfile
import pytest

# Override DATABASE_PATH before importing app modules
os.environ["DATABASE_PATH"] = os.path.join(tempfile.gettempdir(), "test_companies.db")
os.environ["GOOGLE_CREDENTIALS_JSON"] = "{}"
os.environ["GOOGLE_SHEET_ID"] = "test_sheet_id"
os.environ["GROQ_API_KEY"] = "test_key"

from app import database as db


@pytest.fixture(autouse=True)
def setup_db():
    """Initialize a fresh test database for each test."""
    # Remove old test DB if exists
    db_path = os.environ["DATABASE_PATH"]
    if os.path.exists(db_path):
        os.remove(db_path)
    db.init_db()
    yield
    # Cleanup
    if os.path.exists(db_path):
        os.remove(db_path)


class TestDatabase:
    """Test database CRUD operations."""

    def test_init_db_creates_tables(self):
        """Tables should exist after init."""
        conn = db.get_connection()
        tables = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()
        table_names = {t["name"] for t in tables}
        conn.close()
        assert "companies" in table_names
        assert "enrichment_signals" in table_names
        assert "verdicts" in table_names

    def test_upsert_company(self):
        """Upserting a company should return its ID."""
        company_id = db.upsert_company("TestCorp", 2)
        assert company_id is not None
        assert isinstance(company_id, int)

    def test_upsert_company_duplicate(self):
        """Upserting the same company twice should return the same ID."""
        id1 = db.upsert_company("TestCorp", 2)
        id2 = db.upsert_company("TestCorp", 2)
        assert id1 == id2

    def test_get_pending_companies(self):
        """Pending companies should be returned."""
        db.upsert_company("Alpha", 2)
        db.upsert_company("Beta", 3)
        pending = db.get_pending_companies()
        assert len(pending) == 2
        names = {c["name"] for c in pending}
        assert names == {"Alpha", "Beta"}

    def test_update_company_status(self):
        """Status update should persist."""
        cid = db.upsert_company("StatusTest", 5)
        db.update_company_status(cid, "completed")
        pending = db.get_pending_companies()
        names = {c["name"] for c in pending}
        assert "StatusTest" not in names

    def test_save_and_get_enrichment(self):
        """Enrichment signals should be saved and retrievable."""
        cid = db.upsert_company("EnrichCorp", 3)
        signal = {"source": "wikipedia", "found": True, "extract": "A test company"}
        db.save_enrichment(cid, "wikipedia", signal)

        signals = db.get_enrichments(cid)
        assert len(signals) == 1
        assert signals[0]["signal_data"]["source"] == "wikipedia"
        assert signals[0]["signal_data"]["found"] is True

    def test_save_and_get_verdict(self):
        """Verdicts should be saved and retrievable."""
        cid = db.upsert_company("JudgeCorp", 4)
        db.save_verdict(cid, "strong_fit", 0.85, "Evidence-based reasoning", "What's your AI roadmap?")

        verdict = db.get_verdict(cid)
        assert verdict is not None
        assert verdict["fit"] == "strong_fit"
        assert verdict["confidence"] == 0.85
        assert "Evidence" in verdict["reasoning"]

    def test_get_all_companies_with_verdicts(self):
        """get_all_companies should join verdicts."""
        cid = db.upsert_company("FullCorp", 6)
        db.save_verdict(cid, "moderate_fit", 0.6, "Decent signals", "How do you use AI?")

        companies = db.get_all_companies()
        assert len(companies) >= 1
        corp = [c for c in companies if c["name"] == "FullCorp"][0]
        assert corp["fit"] == "moderate_fit"
        assert corp["confidence"] == 0.6

    def test_get_stats(self):
        """Stats should reflect database state."""
        db.upsert_company("A", 2)
        cid = db.upsert_company("B", 3)
        db.update_company_status(cid, "completed")

        stats = db.get_stats()
        assert stats["total"] == 2
        assert stats["processed"] == 1
        assert stats["pending"] == 1

    def test_get_company_by_name(self):
        """Should find company by exact name."""
        db.upsert_company("FindMe", 7)
        result = db.get_company_by_name("FindMe")
        assert result is not None
        assert result["name"] == "FindMe"

    def test_get_company_by_name_not_found(self):
        """Should return None for non-existent company."""
        result = db.get_company_by_name("NonExistent")
        assert result is None


class TestEnrichment:
    """Test enrichment modules (HTTP only — no Selenium in CI)."""

    def test_wikipedia_enrich_known_company(self):
        """Wikipedia should return data for a well-known company."""
        from app.enrichment import wikipedia
        result = wikipedia.enrich("Sony")
        assert result["source"] == "wikipedia"
        assert result["method"] == "http_api"
        # Sony should be found on Wikipedia
        if result["found"]:
            assert len(result.get("extract", "")) > 0

    def test_wikipedia_enrich_unknown_company(self):
        """Wikipedia should handle unknown companies gracefully."""
        from app.enrichment import wikipedia
        result = wikipedia.enrich("xyznonexistent12345corp")
        assert result["source"] == "wikipedia"
        assert result["found"] is False

    def test_github_enrich_known_company(self):
        """GitHub search should return repos for a known company."""
        from app.enrichment import github_search
        result = github_search.enrich("Google")
        assert result["source"] == "github"
        assert result["method"] == "http_api"
