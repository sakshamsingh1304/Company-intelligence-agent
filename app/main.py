"""
FastAPI application — API routes, scheduler, and dashboard.
Serves as the entry point for the deployed service (Task §6 & §7).
"""
import logging
import threading
from contextlib import asynccontextmanager
from datetime import datetime, timezone

from fastapi import FastAPI, Request, BackgroundTasks
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from apscheduler.schedulers.background import BackgroundScheduler

from app import database as db
from app.pipeline import run_pipeline, pipeline_state
from app.config import PIPELINE_INTERVAL_MINUTES

# ── Logging ────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s │ %(name)-20s │ %(levelname)-7s │ %(message)s",
)
logger = logging.getLogger(__name__)

# ── Scheduler ──────────────────────────────────────────────────
scheduler = BackgroundScheduler()


def scheduled_pipeline():
    """Wrapper for scheduled execution."""
    logger.info("⏰ Scheduled pipeline run triggered")
    run_pipeline()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup & shutdown events."""
    # Startup
    db.init_db()
    logger.info("Database initialized")

    scheduler.add_job(
        scheduled_pipeline,
        "interval",
        minutes=PIPELINE_INTERVAL_MINUTES,
        id="pipeline_scheduled",
        replace_existing=True,
    )
    scheduler.start()
    logger.info(f"Scheduler started — pipeline runs every {PIPELINE_INTERVAL_MINUTES} min")

    yield

    # Shutdown
    scheduler.shutdown(wait=False)
    logger.info("Scheduler shut down")


# ── App ────────────────────────────────────────────────────────
app = FastAPI(
    title="Company Intelligence Agent",
    description="LH2 AI Labs — Automated company enrichment & LLM evaluation pipeline",
    version="1.0.0",
    lifespan=lifespan,
)

app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")


# ── Dashboard ──────────────────────────────────────────────────

@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    """Serve the main dashboard UI."""
    companies = db.get_all_companies()
    stats = db.get_stats()

    next_run = None
    job = scheduler.get_job("pipeline_scheduled")
    if job and job.next_run_time:
        next_run = job.next_run_time.strftime("%Y-%m-%d %H:%M UTC")

    return templates.TemplateResponse("index.html", {
        "request": request,
        "companies": companies,
        "stats": stats,
        "pipeline_state": pipeline_state,
        "next_run": next_run,
    })


# ── API Routes ─────────────────────────────────────────────────

@app.post("/api/run")
async def trigger_pipeline(background_tasks: BackgroundTasks):
    """Trigger the pipeline on demand (Task §6)."""
    if pipeline_state["is_running"]:
        return JSONResponse(
            status_code=409,
            content={"status": "already_running",
                      "message": "Pipeline is already in progress"},
        )

    background_tasks.add_task(run_pipeline)
    return {
        "status": "started",
        "message": "Pipeline triggered — running in background",
        "triggered_at": datetime.now(timezone.utc).isoformat(),
    }


@app.get("/api/status")
async def get_status():
    """Current pipeline status and last run details."""
    next_run = None
    job = scheduler.get_job("pipeline_scheduled")
    if job and job.next_run_time:
        next_run = job.next_run_time.strftime("%Y-%m-%d %H:%M UTC")

    return {
        "pipeline": pipeline_state,
        "schedule": {
            "interval_minutes": PIPELINE_INTERVAL_MINUTES,
            "next_run": next_run,
        },
        "database": db.get_stats(),
    }


@app.get("/api/companies")
async def list_companies():
    """Return all companies with verdicts from the database."""
    companies = db.get_all_companies()
    return {"count": len(companies), "companies": companies}


@app.get("/api/companies/{name}")
async def get_company(name: str):
    """Look up a single company by name."""
    company = db.get_company_by_name(name)
    if not company:
        return JSONResponse(status_code=404, content={"error": "Company not found"})

    # Also fetch enrichment signals
    enrichments = db.get_enrichments(company["id"])
    return {"company": company, "enrichment_signals": enrichments}


@app.get("/health")
async def health_check():
    """Health check endpoint for Render / uptime monitors."""
    return {"status": "healthy", "timestamp": datetime.now(timezone.utc).isoformat()}


# ── Run with Uvicorn ───────────────────────────────────────────
if __name__ == "__main__":
    import uvicorn
    from app.config import APP_HOST, APP_PORT
    uvicorn.run("app.main:app", host=APP_HOST, port=APP_PORT, reload=True)
