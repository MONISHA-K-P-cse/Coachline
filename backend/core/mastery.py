import json
import logging

from sqlalchemy.orm import Session

from backend.models.mastery import TopicMastery
from backend.models.roadmap import Note
from backend.models.user import Profile

logger = logging.getLogger("mastery")

def update_topic_mastery(db: Session, user_id: int, topic: str, score_delta: float) -> TopicMastery:
    """
    Updates or creates a TopicMastery record for a user.
    If evaluation flags a weak topic (low score), flags needs_regeneration = True
    and automatically triggers note regeneration.
    """
    mastery = db.query(TopicMastery).filter(
        TopicMastery.user_id == user_id,
        TopicMastery.topic == topic
    ).first()

    if not mastery:
        mastery = TopicMastery(
            user_id=user_id,
            topic=topic,
            mastery_score=max(0.0, min(100.0, 70.0 + score_delta))
        )
        db.add(mastery)
    else:
        mastery.mastery_score = max(0.0, min(100.0, mastery.mastery_score + score_delta))

    if mastery.mastery_score < 70.0:
        mastery.needs_regeneration = True
        enqueue_note_regeneration(db, user_id, topic)

    db.commit()
    db.refresh(mastery)
    return mastery


def enqueue_note_regeneration(db: Session, user_id: int, topic: str) -> Note:
    """
    Agentic feedback loop: automatically (re)generates a targeted study note
    for a weak topic by calling the Notes Agent with that topic and the
    user's own learning_style, so the output is a real personalized agent
    generation rather than a static template.
    """
    # Imported lazily so importing core.mastery (and anything that imports
    # it, like main.py) doesn't require the RAG stack (chromadb) at
    # process start - only when a note regeneration actually fires.
    from ai.agents.notes_agent import NotesAgent, DEFAULT_LEARNING_STYLE

    logger.info(
        "Feedback loop triggered: generating targeted revision note for user %s on topic '%s'",
        user_id,
        topic,
    )

    profile = db.query(Profile).filter(Profile.user_id == user_id).first()
    learning_style = (profile.learning_style if profile and profile.learning_style else DEFAULT_LEARNING_STYLE)

    generated = NotesAgent().generate_notes(topic, learning_style=learning_style)
    auto_content = json.dumps(generated["blocks"])

    existing_note = db.query(Note).filter(
        Note.user_id == user_id,
        Note.topic == topic
    ).first()

    if existing_note:
        existing_note.content = auto_content
        existing_note.note_type = generated.get("note_type", existing_note.note_type)
        note = existing_note
    else:
        note = Note(
            user_id=user_id,
            topic=topic,
            title=f"Refresher: {topic}",
            content=auto_content,
            note_type=generated.get("note_type", "detailed_note"),
            is_bookmarked=True,
        )
        db.add(note)

    return note
