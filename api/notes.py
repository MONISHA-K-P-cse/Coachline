from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from core.database import get_db
from core.auth import get_current_user
from models.user import User
from models.roadmap import Note
from schemas.roadmap import NoteCreate, NoteResponse

router = APIRouter(prefix="/notes", tags=["Roadmap & Notes Storage"])

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
