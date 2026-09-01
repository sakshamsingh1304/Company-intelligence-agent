"""
Pipeline orchestrator — the single end-to-end flow.
Source → Enrich → Persist → Judge → Sync back (Task §1–§5).
"""
import logging
from datetime import datetime, timezone

from app import database as db
from app import sheets
from app.enrichment import wikipedia, github_search, browser
from app.judge import judge

logger = logging.getLogger(__name__)

# ── Pipeline state (in-memory, transient) ──────────────────────
pipeline_state = {
    "is_running": False,
    "last_run_at": None,
    "last_run_status": None,
    "last_run_details": None,
}


def run_pipeline() -> dict:
    """
    Execute the full company intelligence pipeline:
      1. Source   — read new companies from Google Sheet
      2. Enrich   — pull signals (Wikipedia + GitHub + browser)
      3. Persist  — store in SQLite
      4. Judge    — LLM verdict via Groq
      5. Sync     — write verdict back to Sheet

    Returns a summary dict of the run.
    """
    if pipeline_state["is_running"]:
        return {"status": "already_running", "message": "Pipeline is already in progress"}

    pipeline_state["is_running"] = True
    pipeline_state["last_run_at"] = datetime.now(timezone.utc).isoformat()

    results = {
        "started_at": pipeline_state["last_run_at"],
        "companies_processed": 0,
        "companies_skipped": 0,
        "errors": [],
    }

    try:
        # ── Step 1: Source — fetch companies from Sheet ────────
        logger.info("Pipeline Step 1: Sourcing companies from Google Sheet")
        try:
            sheet_companies = sheets.fetch_companies()
        except Exception as e:
            logger.error(f"Failed to fetch from Sheet: {e}")
            results["errors"].append(f"Sheet fetch failed: {str(e)}")
            results["status"] = "error"
            return results

        if not sheet_companies:
            logger.info("No companies found in Sheet")
            results["status"] = "no_data"
            return results

        # ── Step 2–5: Process each company ─────────────────────
        for company in sheet_companies:
            name = company["name"]
            sheet_row = company["sheet_row"]

            # Skip already-completed companies
            if company.get("status") == "completed":
                results["companies_skipped"] += 1
                continue

            try:
                logger.info(f"Processing: {name}")

                # Upsert into database
                company_id = db.upsert_company(name, sheet_row)
                db.update_company_status(company_id, "enriching")
                sheets.sync_status(sheet_row, "enriching")

                # ── Step 2: Enrich ─────────────────────────────
                logger.info(f"  Enriching: {name}")
                signals = []

                # Signal 1: Wikipedia (HTTP)
                try:
                    wiki_data = wikipedia.enrich(name)
                    db.save_enrichment(company_id, "wikipedia", wiki_data)
                    signals.append(wiki_data)
                    logger.info(f"    Wikipedia: {'found' if wiki_data.get('found') else 'not found'}")
                except Exception as e:
                    logger.error(f"    Wikipedia failed: {e}")
                    results["errors"].append(f"Wikipedia({name}): {str(e)}")

                # Signal 2: GitHub (HTTP)
                try:
                    github_data = github_search.enrich(name)
                    db.save_enrichment(company_id, "github", github_data)
                    signals.append(github_data)
                    logger.info(f"    GitHub: {github_data.get('total_repos_found', 0)} repos")
                except Exception as e:
                    logger.error(f"    GitHub failed: {e}")
                    results["errors"].append(f"GitHub({name}): {str(e)}")

                # Signal 3: Browser automation (Selenium)
                try:
                    browser_data = browser.enrich(name)
                    db.save_enrichment(company_id, "browser", browser_data)
                    signals.append(browser_data)
                    logger.info(f"    Browser: {browser_data.get('results_count', 0)} results")
                except Exception as e:
                    logger.error(f"    Browser failed: {e}")
                    results["errors"].append(f"Browser({name}): {str(e)}")

                db.update_company_status(company_id, "enriched")

                # ── Step 3: Persist (already done above via db.save_enrichment)

                # ── Step 4: Judge ──────────────────────────────
                if signals:
                    logger.info(f"  Judging: {name}")
                    verdict = judge(name, signals)

                    db.save_verdict(
                        company_id=company_id,
                        fit=verdict["fit"],
                        confidence=verdict["confidence"],
                        reasoning=verdict["reasoning"],
                        follow_up_question=verdict["follow_up_question"],
                    )

                    # ── Step 5: Sync back to Sheet ─────────────
                    logger.info(f"  Syncing verdict back to Sheet: {name}")
                    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
                    sheets.sync_verdict(
                        sheet_row=sheet_row,
                        status="completed",
                        fit=verdict["fit"],
                        confidence=verdict["confidence"],
                        reasoning=verdict["reasoning"],
                        follow_up_question=verdict["follow_up_question"],
                        updated_at=now,
                    )

                    db.update_company_status(company_id, "completed")
                    results["companies_processed"] += 1
                    logger.info(f"  ✓ Done: {name} → {verdict['fit']}")
                else:
                    db.update_company_status(company_id, "error")
                    sheets.sync_status(sheet_row, "error - no signals")
                    results["errors"].append(f"No signals collected for {name}")

            except Exception as e:
                logger.error(f"Failed to process {name}: {e}")
                results["errors"].append(f"{name}: {str(e)}")
                try:
                    db.update_company_status(company_id, "error")
                    sheets.sync_status(sheet_row, "error")
                except Exception:
                    pass

        results["status"] = "completed"
        results["finished_at"] = datetime.now(timezone.utc).isoformat()

    except Exception as e:
        logger.error(f"Pipeline failed: {e}")
        results["status"] = "error"
        results["errors"].append(str(e))

    finally:
        pipeline_state["is_running"] = False
        pipeline_state["last_run_status"] = results.get("status", "unknown")
        pipeline_state["last_run_details"] = results

    logger.info(f"Pipeline finished: {results['companies_processed']} processed, "
                f"{len(results['errors'])} errors")
    return results
