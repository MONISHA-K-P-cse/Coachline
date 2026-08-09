from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from starlette.concurrency import run_in_threadpool
from typing import List
import logging

from backend.core.database import get_db
from backend.core.auth import get_current_user
from backend.models.user import User, Profile
from backend.models.mentor import CareerMentorMessage
from backend.schemas.mentor import MentorMessageCreate, MentorMessageResponse

from ai.agents.mentor_agent import MentorAgent

router = APIRouter(prefix="/mentor", tags=["Career Mentor Chat"])
logger = logging.getLogger("mentor")

mentor_agent = MentorAgent()


@router.post("/chat", response_model=List[MentorMessageResponse])
async def chat_with_mentor(
    msg_in: MentorMessageCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Save user message
    user_msg = CareerMentorMessage(
        user_id=current_user.id,
        sender="user",
        message=msg_in.message,
    )
    db.add(user_msg)
    db.commit()

    profile = db.query(Profile).filter(Profile.user_id == current_user.id).first()
    target_role = profile.target_role if profile else "Software Engineer"
    experience_level = profile.experience_level if profile else "Junior"

    # Extract resume parsed text skills
    resume_skills = ""
    if current_user.resumes:
        latest_res = current_user.resumes[-1]
        resume_skills = latest_res.parsed_text[:600] if latest_res.parsed_text else ""

    # Extract interview strengths & weaknesses
    weak_topics = []
    strong_topics = []
    if current_user.interviews:
        latest_int = current_user.interviews[-1]
        meta = latest_int.metadata_json or {}
        weak_topics = meta.get("weak_topics", [])
        strong_topics = meta.get("strong_topics", [])

    # Extract active roadmap steps summary
    roadmap_status = ""
    if current_user.roadmaps:
        latest_rm = current_user.roadmaps[-1]
        steps_data = latest_rm.steps_json or {}
        steps = steps_data.get("steps", [])
        completed = sum(1 for s in steps if s.get("status") == "completed")
        total = len(steps)
        roadmap_status = f"Roadmap '{latest_rm.title}': {completed}/{total} steps completed."

    # Extract mastery competencies list
    mastery_summary = ""
    if current_user.mastery_scores:
        scores = [f"{m.topic}: {int(m.mastery_score)}%" for m in current_user.mastery_scores]
        mastery_summary = ", ".join(scores)

    # Extract Bob challenge results summary
    bob_results_summary = ""
    if current_user.bob_results:
        results = [f"{r.challenge_id} (Score: {r.score}/100)" for r in current_user.bob_results]
        bob_results_summary = ", ".join(results)

    try:
        mentor_reply_text = await run_in_threadpool(
            mentor_agent.chat,
            msg_in.message,
            target_role=target_role,
            experience_level=experience_level,
            resume_skills=resume_skills,
            weak_topics=weak_topics,
            strong_topics=strong_topics,
            roadmap_status=roadmap_status,
            mastery_summary=mastery_summary,
            bob_results_summary=bob_results_summary
        )
    except Exception as exc:
        logger.warning("Mentor agent call failed (%s); AI mentor is unavailable.", exc)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="The AI career mentor is temporarily unavailable. Please try again shortly.",
        )

    mentor_msg = CareerMentorMessage(
        user_id=current_user.id,
        sender="mentor",
        message=mentor_reply_text,
    )
    db.add(mentor_msg)
    db.commit()
    db.refresh(user_msg)
    db.refresh(mentor_msg)

    return [user_msg, mentor_msg]


@router.get("/history", response_model=List[MentorMessageResponse])
def get_chat_history(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return (
        db.query(CareerMentorMessage)
        .filter(CareerMentorMessage.user_id == current_user.id)
        .order_by(CareerMentorMessage.created_at.asc())
        .all()
    )


@router.delete("/history", status_code=status.HTTP_204_NO_CONTENT)
def clear_chat_history(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    db.query(CareerMentorMessage).filter(CareerMentorMessage.user_id == current_user.id).delete()
    db.commit()
    return None


@router.post("/new-session", response_model=MentorMessageResponse, status_code=status.HTTP_201_CREATED)
def start_new_session(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    from datetime import datetime
    session_title = f"Chat - {datetime.now().strftime('%b %d, %H:%M')}"
    system_msg = CareerMentorMessage(
        user_id=current_user.id,
        sender="system",
        message=session_title,
    )
    db.add(system_msg)
    db.commit()
    db.refresh(system_msg)
    return system_msg
