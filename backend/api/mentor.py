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
    target_role = profile.target_role if profile else ""

    try:
        mentor_reply_text = await run_in_threadpool(mentor_agent.chat, msg_in.message, target_role)
    except Exception as exc:
        logger.warning("Mentor agent call failed (%s); returning mock career mentor fallback.", exc)
        msg_lower = msg_in.message.strip().lower()
        if any(greet in msg_lower for greet in ["hi", "hello", "hey", "hola"]):
            mentor_reply_text = "Hello! I'm your career mentor. I'm here to help you get interview-ready! You can ask me about resume feedback, study roadmap topics, mock sessions, or general tech prep advice."
        elif any(keyword in msg_lower for keyword in ["prep", "prepare", "start", "what to", "study", "guidance", "begin"]):
            mentor_reply_text = "To prepare effectively, I recommend focusing on three core areas: 1) Data structures and algorithm basics, 2) DB transaction locks & scaling, and 3) Containerization tools (like Docker). We can review your strengths next, or start a mock session! What would you like to focus on first?"
        else:
            mentor_reply_text = "That is a very good question! Mastering that technical concept requires a solid balance of understanding core architectural properties (like ACID parameters or separation of concerns) and writing real, containerized prototype scripts. Which specific area should we drill down into next?"

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
