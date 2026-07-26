from backend.api.auth import router as auth_router
from backend.api.resume import router as resume_router
from backend.api.jd import router as jd_router
from backend.api.roadmap import router as roadmap_router
from backend.api.notes import router as notes_router
from backend.api.interview import router as interview_router
from backend.api.dashboard import router as dashboard_router
from backend.api.mentor import router as mentor_router

__all__ = [
    "auth_router",
    "resume_router",
    "jd_router",
    "roadmap_router",
    "notes_router",
    "interview_router",
    "dashboard_router",
    "mentor_router",
]
