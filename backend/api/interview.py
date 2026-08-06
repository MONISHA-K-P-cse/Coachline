from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, HTTPException
from sqlalchemy.orm import Session
from starlette.concurrency import run_in_threadpool
from typing import List
import json
import logging
from datetime import datetime

from backend.core.database import SessionLocal, get_db
from backend.core.auth import get_current_user
from backend.core.mastery import update_topic_mastery
from backend.models.interview import InterviewSession, QuestionAnswer
from backend.models.resume import Resume
from backend.models.user import User, Profile
from backend.schemas.interview import (
    InterviewSessionResponse,
    ReplayDiffResponse,
    ReplayDiffAttempt,
)

from ai.agents.eval_agent import EvaluationAgent
from ai.agents.interview_agent import InterviewAgent

router = APIRouter(prefix="/interview", tags=["Interview Session Infra"])
logger = logging.getLogger("interview")

# A strong answer (>= this overall score, 0-100 scale) triggers a devil's
# advocate follow-up instead of moving straight to a fresh topic.
DEVILS_ADVOCATE_SCORE_THRESHOLD = 80.0

eval_agent = EvaluationAgent()
interview_agent = InterviewAgent()


def _candidate_background(db: Session, user_id: int) -> str:
    """Brief resume-derived context used to seed real question generation,
    so the opening question can reference the candidate's actual skills
    instead of being generic."""
    resume = (
        db.query(Resume)
        .filter(Resume.user_id == user_id)
        .order_by(Resume.uploaded_at.desc())
        .first()
    )
    if not resume or not resume.score_details:
        return ""
    details = resume.score_details
    parts = []
    if details.get("summary"):
        parts.append(details["summary"])
    if details.get("strengths"):
        parts.append("Strengths: " + ", ".join(details["strengths"]))
    return "\n".join(parts)


def _placeholder_eval() -> dict:
    """Last-resort static result used only if the real EvaluationAgent call
    itself raises (e.g. Ollama isn't running) - not the primary path."""
    return {
        "technical_score": 50.0,
        "communication_score": 50.0,
        "behavioral_score": 50.0,
        "confidence_score": 50.0,
        "star_score": 50.0,
        "overall_score": 50.0,
        "feedback": "The AI interviewer is temporarily unavailable, so this turn could not be scored. This is a placeholder, not a real evaluation.",
        "weak_topics": [],
        "fallback_used": True,
    }


@router.websocket("/ws/{user_id}")
async def interview_websocket(websocket: WebSocket, user_id: int):
    await websocket.accept()
    db: Session = SessionLocal()
    session = None
    turn_number = 1
    experience_level = ""
    candidate_background = ""

    try:
        while True:
            raw_data = await websocket.receive_text()
            data = json.loads(raw_data)
            event = data.get("event")

            if event == "start":
                role = data.get("role", "Backend Engineer")
                week = data.get("week", 1)
                topic = data.get("topic", "")
                profile = db.query(Profile).filter(Profile.user_id == user_id).first()
                experience_level = profile.experience_level if profile and profile.experience_level else ""
                candidate_background = _candidate_background(db, user_id)

                session = InterviewSession(
                    user_id=user_id,
                    role=role,
                    status="active",
                    started_at=datetime.utcnow()
                )
                db.add(session)
                db.commit()
                db.refresh(session)

                # Real agent call for the opening question too - role,
                # experience level, and (if available) the candidate's own
                # resume background all shape it, instead of a fixed
                # "REST APIs and database design" template with only the
                # role name spliced in.
                try:
                    opening = await run_in_threadpool(
                        interview_agent.generate_question,
                        role, 0, experience_level, candidate_background, True, week, topic
                    )
                    initial_q = opening["question"]
                except Exception as exc:
                    logger.warning("Interview agent opening question failed (%s); using placeholder question.", exc)
                    initial_q = f"Welcome to your {role} mock interview! To begin, please introduce yourself and your relevant experience for this role."

                qa = QuestionAnswer(
                    session_id=session.id,
                    turn_number=turn_number,
                    question=initial_q
                )
                db.add(qa)
                db.commit()

                await websocket.send_json({
                    "event": "question",
                    "session_id": session.id,
                    "turn_number": turn_number,
                    "question": initial_q,
                    "mode": "standard",
                })

            elif event == "answer":
                if not session:
                    await websocket.send_json({"event": "error", "message": "No active interview session found."})
                    continue

                user_answer = data.get("user_answer", "")

                current_qa = db.query(QuestionAnswer).filter(
                    QuestionAnswer.session_id == session.id,
                    QuestionAnswer.turn_number == turn_number
                ).first()

                if current_qa:
                    current_qa.user_answer = user_answer

                question_text = current_qa.question if current_qa else ""

                # Combined call: scores the answer AND produces the next
                # question in a single Granite round-trip, instead of two
                # sequential calls (eval, then next-question). Halves the
                # "evaluating..." wait on CPU-only inference. Falls back to
                # the previous two-call path if the combined output can't be
                # parsed, so a single bad generation can't cost reliability.
                try:
                    eval_result, next_q = await run_in_threadpool(
                        interview_agent.evaluate_and_generate_next,
                        session.role, question_text, user_answer, experience_level, candidate_background,
                    )
                except Exception as exc:
                    logger.warning(
                        "Combined eval+next-question call failed (%s); falling back to two separate calls.", exc
                    )
                    try:
                        eval_result = await run_in_threadpool(
                            eval_agent.evaluate_answer, question_text, user_answer
                        )
                    except Exception as exc2:
                        logger.warning("Eval agent call failed (%s); using placeholder score.", exc2)
                        eval_result = _placeholder_eval()

                    fallback_score = eval_result["overall_score"]
                    try:
                        if fallback_score >= DEVILS_ADVOCATE_SCORE_THRESHOLD:
                            next_q = await run_in_threadpool(
                                interview_agent.generate_devils_advocate_question,
                                session.role, question_text, user_answer,
                            )
                        else:
                            next_q = await run_in_threadpool(
                                interview_agent.generate_question,
                                session.role, fallback_score, experience_level, candidate_background, False,
                            )
                    except Exception as exc2:
                        logger.warning("Interview agent question generation failed (%s); using placeholder question.", exc2)
                        next_q = {
                            "question": f"Let's continue - tell me more about your hands-on experience relevant to the {session.role} role.",
                            "difficulty": "Medium",
                            "mode": "standard",
                        }

                score = eval_result["overall_score"]
                tech_score = eval_result["technical_score"]
                comm_score = eval_result["communication_score"]
                behav_score = eval_result["behavioral_score"]
                conf_score = eval_result["confidence_score"]
                star_score = eval_result["star_score"]
                feedback = eval_result["feedback"]
                weak_topics = eval_result["weak_topics"]

                if current_qa:
                    current_qa.score = score
                    current_qa.technical_score = tech_score
                    current_qa.communication_score = comm_score
                    current_qa.behavioral_score = behav_score
                    current_qa.confidence_score = conf_score
                    current_qa.star_score = star_score
                    current_qa.feedback = feedback
                    current_qa.weak_topics = weak_topics
                    db.commit()

                turn_number += 1
                next_question = next_q["question"]

                next_qa = QuestionAnswer(
                    session_id=session.id,
                    turn_number=turn_number,
                    question=next_question
                )
                db.add(next_qa)
                db.commit()

                await websocket.send_json({
                    "event": "eval_and_next",
                    "previous_score": score,
                    "scores_breakdown": {
                        "technical": tech_score,
                        "communication": comm_score,
                        "behavioral": behav_score,
                        "confidence": conf_score,
                        "star_method": star_score
                    },
                    "feedback": feedback,
                    "weak_topics": weak_topics,
                    "fallback_used": eval_result.get("fallback_used", False),
                    "turn_number": turn_number,
                    "next_question": next_question,
                    "difficulty": next_q.get("difficulty"),
                    "mode": next_q.get("mode", "standard"),
                })

                # Feedback-loop note regeneration runs *after* the candidate
                # already has their score and next question, not before -
                # eval_agent can flag several weak topics from a single
                # answer, and update_topic_mastery calls NotesAgent (a full
                # ~150-250s Granite generation) for each one it flags. Doing
                # that sequentially before responding turned one slow answer
                # into a multi-topic pileup that could keep the candidate
                # waiting 15+ minutes for a response that should take one or
                # two model calls. Score is 0-100 (real EvaluationAgent
                # scale); 70 is the same "neutral baseline" core.mastery
                # already uses when creating a fresh TopicMastery row.
                for topic in weak_topics:
                    score_delta = score - 70.0
                    try:
                        await run_in_threadpool(
                            update_topic_mastery, db, user_id=user_id, topic=topic, score_delta=score_delta
                        )
                    except Exception as exc:
                        logger.warning(
                            "update_topic_mastery failed for topic '%s' (%s); continuing without it.",
                            topic, exc,
                        )

            elif event == "end":
                if session:
                    session.status = "completed"
                    session.ended_at = datetime.utcnow()

                    qas = db.query(QuestionAnswer).filter(QuestionAnswer.session_id == session.id).all()
                    scored = [q for q in qas if q.score and q.score > 0]

                    def _avg(attr: str) -> float:
                        if not scored:
                            return 0.0
                        return round(sum(getattr(q, attr) for q in scored) / len(scored), 1)

                    session.average_score = _avg("score")
                    session.technical_score = _avg("technical_score")
                    session.communication_score = _avg("communication_score")
                    session.behavioral_score = _avg("behavioral_score")
                    session.confidence_score = _avg("confidence_score")
                    session.star_score = _avg("star_score")

                    db.commit()
                    await websocket.send_json({
                        "event": "ended",
                        "session_id": session.id,
                        "average_score": session.average_score,
                        "scores_breakdown": {
                            "technical": session.technical_score,
                            "communication": session.communication_score,
                            "behavioral": session.behavioral_score,
                            "confidence": session.confidence_score,
                            "star_method": session.star_score
                        }
                    })
                break

    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected for user {user_id}")
    finally:
        db.close()


@router.get("/sessions", response_model=List[InterviewSessionResponse])
def list_interview_sessions(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return (
        db.query(InterviewSession)
        .filter(InterviewSession.user_id == current_user.id)
        .order_by(InterviewSession.started_at.desc())
        .all()
    )


@router.get("/sessions/{session_id}", response_model=InterviewSessionResponse)
def get_interview_session(
    session_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    session = db.query(InterviewSession).filter(
        InterviewSession.id == session_id,
        InterviewSession.user_id == current_user.id,
    ).first()
    if not session:
        raise HTTPException(status_code=404, detail="Interview session not found")
    return session


@router.get("/replay-diff/{topic}", response_model=ReplayDiffResponse)
def get_replay_diff(
    topic: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Compares the candidate's earliest vs most recent answer flagged with
    `topic` in QuestionAnswer.weak_topics, so the frontend can show concrete
    improvement (or lack thereof) on a specific weak area over time.
    """
    qas = (
        db.query(QuestionAnswer)
        .join(InterviewSession, QuestionAnswer.session_id == InterviewSession.id)
        .filter(InterviewSession.user_id == current_user.id)
        .filter(QuestionAnswer.user_answer.isnot(None))
        .order_by(QuestionAnswer.created_at.asc())
        .all()
    )

    matches = [qa for qa in qas if qa.weak_topics and topic in qa.weak_topics]

    if not matches:
        raise HTTPException(
            status_code=404,
            detail=f"No answered interview turns found flagging '{topic}' as a weak topic.",
        )

    def _to_attempt(qa: QuestionAnswer) -> ReplayDiffAttempt:
        return ReplayDiffAttempt(
            session_id=qa.session_id,
            turn_number=qa.turn_number,
            question=qa.question,
            user_answer=qa.user_answer,
            score=qa.score,
            feedback=qa.feedback,
            created_at=qa.created_at,
        )

    earliest = matches[0]
    latest = matches[-1]

    return ReplayDiffResponse(
        topic=topic,
        attempt_count=len(matches),
        earliest=_to_attempt(earliest),
        latest=_to_attempt(latest),
        score_delta=round(latest.score - earliest.score, 1) if len(matches) > 1 else None,
    )
