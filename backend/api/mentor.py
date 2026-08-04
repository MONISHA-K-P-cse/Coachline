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
