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
from backend.models.user import User
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

    try:
        while True:
            raw_data = await websocket.receive_text()
            data = json.loads(raw_data)
            event = data.get("event")

            if event == "start":
                role = data.get("role", "Backend Engineer")
                session = InterviewSession(
                    user_id=user_id,
                    role=role,
                    status="active",
                    started_at=datetime.utcnow()
                )
                db.add(session)
                db.commit()
                db.refresh(session)

                initial_q = f"Welcome to your {role} mock interview! To begin, please introduce yourself and your experience with REST APIs and database design."
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

                # Real Evaluation Agent call (Granite LLM). EvaluationAgent
                # already has its own internal fallback (fallback_used=True,
                # score=50) if the model output can't be parsed as structured
                # JSON - this try/except only covers the LLM call itself
                # failing to run at all.
                try:
                    eval_result = await run_in_threadpool(
                        eval_agent.evaluate_answer, question_text, user_answer
                    )
                except Exception as exc:
                    logger.warning("Eval agent call failed (%s); using placeholder score.", exc)
                    eval_result = _placeholder_eval()

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

                # Trigger Feedback-Loop for weak topics. score is 0-100 (real
                # EvaluationAgent scale); 70 is the same "neutral baseline"
                # core.mastery already uses when creating a fresh
                # TopicMastery row, so a score above/below 70 nudges mastery
                # up/down accordingly.
                #
                # update_topic_mastery can synchronously call NotesAgent (a
                # blocking Granite call) when it flags a topic weak - run it
                # in a thread so a slow model call doesn't freeze the event
                # loop for every other connection on the server.
                for topic in weak_topics:
                    score_delta = score - 70.0
                    await run_in_threadpool(
                        update_topic_mastery, db, user_id=user_id, topic=topic, score_delta=score_delta
                    )

                turn_number += 1

                devils_advocate = score >= DEVILS_ADVOCATE_SCORE_THRESHOLD
                try:
                    if devils_advocate:
                        next_q = await run_in_threadpool(
                            interview_agent.generate_devils_advocate_question,
                            session.role, question_text, user_answer,
                        )
                    else:
                        next_q = await run_in_threadpool(
                            interview_agent.generate_question, session.role, score,
                        )
                except Exception as exc:
                    logger.warning("Interview agent question generation failed (%s); using placeholder question.", exc)
                    next_q = {
                        "question": f"Let's continue - tell me more about your hands-on experience relevant to the {session.role} role.",
                        "difficulty": "Medium",
                        "mode": "standard",
                    }

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
