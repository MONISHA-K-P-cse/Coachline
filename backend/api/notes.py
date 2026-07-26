from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from starlette.concurrency import run_in_threadpool
from typing import List
import json
import logging

from backend.core.database import get_db
from backend.core.auth import get_current_user
from backend.models.user import User, Profile
from backend.models.roadmap import Note
from backend.schemas.roadmap import NoteCreate, NoteResponse

from ai.agents.notes_agent import NotesAgent

router = APIRouter(prefix="/notes", tags=["Roadmap & Notes Storage"])
logger = logging.getLogger("notes")

notes_agent = NotesAgent()


@router.post("/generate", response_model=NoteResponse, status_code=status.HTTP_201_CREATED)
async def generate_note(
    topic: str,
    roadmap_id: int | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """AI-generates a study note for `topic`, styled to the user's own
    learning_style, using the real Notes Agent (Granite + RAG)."""
    profile = db.query(Profile).filter(Profile.user_id == current_user.id).first()
    learning_style = profile.learning_style if profile else "reading_writing"

    try:
        generated = await run_in_threadpool(notes_agent.generate_notes, topic, learning_style)
    except Exception as exc:
        logger.warning("Notes agent call failed (%s); AI note generator is unavailable.", exc)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="The AI note generator is temporarily unavailable. Please try again shortly.",
        )

    note = Note(
        user_id=current_user.id,
        roadmap_id=roadmap_id,
        topic=topic,
        title=generated["title"],
        content=json.dumps(generated["blocks"]),
        note_type=generated["note_type"],
        category="AI Generated",
        is_bookmarked=False,
    )
    db.add(note)
    db.commit()
    db.refresh(note)
    return note


@router.post("/", response_model=NoteResponse, status_code=status.HTTP_201_CREATED)
def create_note(
    note_in: NoteCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    note = Note(
        user_id=current_user.id,
        roadmap_id=note_in.roadmap_id,
        topic=note_in.topic,
        title=note_in.title,
        content=note_in.content,
        is_bookmarked=note_in.is_bookmarked,
    )
    db.add(note)
    db.commit()
    db.refresh(note)
    return note


@router.get("/", response_model=List[NoteResponse])
def list_notes(
    bookmarked_only: bool = False,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = db.query(Note).filter(Note.user_id == current_user.id)
    if bookmarked_only:
        query = query.filter(Note.is_bookmarked == True)
    return query.order_by(Note.created_at.desc()).all()


@router.patch("/{note_id}/bookmark", response_model=NoteResponse)
def toggle_bookmark(
    note_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    note = db.query(Note).filter(Note.id == note_id, Note.user_id == current_user.id).first()
    if not note:
        raise HTTPException(status_code=404, detail="Note not found")

    note.is_bookmarked = not note.is_bookmarked
    db.commit()
    db.refresh(note)
    return note


@router.delete("/{note_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_note(
    note_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    note = db.query(Note).filter(Note.id == note_id, Note.user_id == current_user.id).first()
    if not note:
        raise HTTPException(status_code=404, detail="Note not found")

    db.delete(note)
    db.commit()
    return None
