from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from starlette.concurrency import run_in_threadpool
from typing import List
import logging

from datetime import datetime

from backend.core.database import get_db
from backend.core.auth import get_current_user
from backend.models.user import User, Profile
from backend.models.resume import Resume
from backend.models.roadmap import Roadmap
from backend.schemas.roadmap import RoadmapCreate, RoadmapResponse

from ai.agents.roadmap_agent import RoadmapAgent

router = APIRouter(prefix="/roadmap", tags=["Roadmap & Notes Storage"])
logger = logging.getLogger("roadmap")

roadmap_agent = RoadmapAgent()


@router.post("/generate", response_model=RoadmapResponse)
async def generate_roadmap(
    roadmap_in: RoadmapCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Ground the roadmap in the user's actual resume analysis when one
    # exists, instead of asking the LLM to guess at their current skills.
    latest_resume = (
        db.query(Resume)
        .filter(Resume.user_id == current_user.id)
        .order_by(Resume.uploaded_at.desc())
        .first()
    )
    if latest_resume and latest_resume.score_details:
        details = latest_resume.score_details
        current_skills = details.get("summary", "") + "\nStrengths: " + ", ".join(details.get("strengths", []))
    else:
        current_skills = "No resume on file yet - assume an entry-level baseline for this role."

    profile = db.query(Profile).filter(Profile.user_id == current_user.id).first()
    target_company = profile.target_company if profile else ""
    experience_level = profile.experience_level if profile else ""

    # Size the roadmap to the time actually left before the interview when
    # a date is set, rather than always defaulting to a flat 8 weeks.
    weeks = 8
    if profile and profile.interview_date:
        days_left = (profile.interview_date - datetime.utcnow()).days
        weeks = max(1, min(12, days_left // 7 or 1))

    try:
        roadmap_data = await run_in_threadpool(
            roadmap_agent.generate_roadmap,
            roadmap_in.target_role,
            current_skills,
            target_company or "",
            experience_level or "",
            weeks,
        )
    except Exception as exc:
        logger.warning("Roadmap agent call failed (%s); AI roadmap generator is unavailable.", exc)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="The AI roadmap generator is temporarily unavailable. Please try again shortly.",
        )

    if not roadmap_data.get("steps_json"):
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="The AI roadmap generator did not return a usable roadmap. Please try again.",
        )

    roadmap = Roadmap(
        user_id=current_user.id,
        title=roadmap_in.title or roadmap_data.get("title", f"{roadmap_in.target_role} Roadmap"),
        target_role=roadmap_in.target_role,
        steps_json=roadmap_data.get("steps_json", []),
        progress_percentage=0,
    )

    db.add(roadmap)
    db.commit()
    db.refresh(roadmap)

    return roadmap


@router.get("/", response_model=List[RoadmapResponse])
def get_user_roadmaps(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return db.query(Roadmap).filter(Roadmap.user_id == current_user.id).all()


@router.get("/{roadmap_id}", response_model=RoadmapResponse)
def get_roadmap_by_id(
    roadmap_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    roadmap = db.query(Roadmap).filter(
        Roadmap.id == roadmap_id,
        Roadmap.user_id == current_user.id
    ).first()
    if not roadmap:
        raise HTTPException(status_code=404, detail="Roadmap not found")
    return roadmap
