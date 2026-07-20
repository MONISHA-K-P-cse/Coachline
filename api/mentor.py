from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
import httpx

from core.database import get_db
from core.auth import get_current_user
from core.config import settings
from models.user import User
from models.mentor import CareerMentorMessage
from schemas.mentor import MentorMessageCreate, MentorMessageResponse

router = APIRouter(prefix="/mentor", tags=["Career Mentor Chat"])

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

    # Call P3 Career Mentor Agent (IBM Granite + Vector DB RAG)
    mentor_reply_text = None
    try:
        async with httpx.AsyncClient(timeout=settings.AGENT_TIMEOUT_SECONDS) as client:
            resp = await client.post(
                f"{settings.P3_AGENT_BASE_URL}/agent/mentor/chat",
                json={
                    "message": msg_in.message,
                    "user_id": current_user.id
                }
            )
            if resp.status_code == 200:
                mentor_reply_text = resp.json().get("reply")
    except Exception:
        pass

    if not mentor_reply_text:
        mentor_reply_text = (
            f"As your Career Mentor, I recommend focusing on mastering core system architecture "
            f"and database indexing for your targeted backend role. Feel free to ask me about mock interview preparation!"
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
