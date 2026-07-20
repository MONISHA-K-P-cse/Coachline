from api.auth import router as auth_router
from api.resume import router as resume_router
from api.jd import router as jd_router
from api.roadmap import router as roadmap_router
from api.notes import router as notes_router
from api.interview import router as interview_router
from api.dashboard import router as dashboard_router
from api.mentor import router as mentor_router

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
