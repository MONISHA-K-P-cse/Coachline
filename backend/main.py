from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.concurrency import run_in_threadpool
import logging
import time

from backend.core.config import settings
from backend.core.database import engine, Base
from backend.api import (
    auth_router,
    resume_router,
    jd_router,
    roadmap_router,
    notes_router,
    interview_router,
    dashboard_router,
    mentor_router,
)
from backend.api.bob import router as bob_router

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("main")

# Auto-create tables for development
Base.metadata.create_all(bind=engine)

from sqlalchemy import text
try:
    with engine.connect() as conn:
        try:
            conn.execute(text("SELECT week FROM interview_sessions LIMIT 1"))
        except Exception:
            conn.execute(text("ALTER TABLE interview_sessions ADD COLUMN week INTEGER DEFAULT 1"))
            conn.commit()
            logger.info("Auto-migrated database: added week column to interview_sessions table.")
        try:
            conn.execute(text("SELECT topic FROM interview_sessions LIMIT 1"))
        except Exception:
            conn.execute(text("ALTER TABLE interview_sessions ADD COLUMN topic VARCHAR"))
            conn.commit()
            logger.info("Auto-migrated database: added topic column to interview_sessions table.")
        try:
            conn.execute(text("SELECT metadata_json FROM interview_sessions LIMIT 1"))
        except Exception:
            conn.execute(text("ALTER TABLE interview_sessions ADD COLUMN metadata_json JSON"))
            conn.commit()
            logger.info("Auto-migrated database: added metadata_json column to interview_sessions table.")
except Exception as e:
    logger.warning("Auto-migration check failed: %s", e)

app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    docs_url="/docs",
    redoc_url="/redoc",
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include Routers for Orchestrator Agent Pipeline
app.include_router(auth_router, prefix=settings.API_V1_STR)
app.include_router(resume_router, prefix=settings.API_V1_STR)
app.include_router(jd_router, prefix=settings.API_V1_STR)
app.include_router(roadmap_router, prefix=settings.API_V1_STR)
app.include_router(notes_router, prefix=settings.API_V1_STR)
app.include_router(interview_router, prefix=settings.API_V1_STR)
app.include_router(dashboard_router, prefix=settings.API_V1_STR)
app.include_router(mentor_router, prefix=settings.API_V1_STR)
app.include_router(bob_router, prefix=settings.API_V1_STR)


@app.on_event("startup")
async def warm_up_granite_model():
    """
    Fires one throwaway generation at boot so the Granite model is already
    loaded into memory before the first real user request - Ollama unloads
    an idle model after its keep_alive window, and loading a multi-GB model
    from disk is itself a multi-second-to-multi-minute cost that would
    otherwise land on whichever request happens to be first.
    """
    from ai.agents.granite_client import GraniteClient

    logger.info("Warming up Granite model...")
    t0 = time.time()
    try:
        await run_in_threadpool(GraniteClient().generate, "Reply with the single word: ready")
        logger.info("Granite model warm-up finished in %.1fs", time.time() - t0)
    except Exception as exc:
        logger.warning("Granite model warm-up failed after %.1fs (%s); first real request will pay the cold-start cost.", time.time() - t0, exc)


@app.get("/")
def root():
    return {
        "project": settings.PROJECT_NAME,
        "status": "online",
        "docs": "/docs",
        "api_v1": settings.API_V1_STR,
    }

@app.get("/health")
def health_check():
    return {"status": "healthy"}
