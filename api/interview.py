from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, HTTPException
from sqlalchemy.orm import Session
import json
import httpx
import os
import logging
from datetime import datetime

from core.database import SessionLocal
from core.config import settings
from core.mastery import update_topic_mastery
from models.interview import InterviewSession, QuestionAnswer

router = APIRouter(prefix="/interview", tags=["Interview Session Infra"])
logger = logging.getLogger("interview")

MOCK_EVAL_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "mocks", "eval_agent.json")

def load_mock_eval() -> dict:
    if os.path.exists(MOCK_EVAL_PATH):
        with open(MOCK_EVAL_PATH, "r") as f:
            return json.load(f)
    return {
        "question": "What is the difference between SQL and NoSQL databases?",
        "score": 8.2,
        "technical_score": 8.8,
        "communication_score": 7.9,
        "behavioral_score": 7.9,
        "confidence_score": 7.4,
        "star_score": 8.0,
        "feedback": "Clear explanation of relational vs document stores.",
        "weak_topics": ["Database Indexing"]
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
                    "question": initial_q
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

                # Call P3 Evaluation Agent with fallback
                eval_result = None
                try:
                    async with httpx.AsyncClient(timeout=settings.AGENT_TIMEOUT_SECONDS) as client:
                        resp = await client.post(
                            f"{settings.P3_AGENT_BASE_URL}/agent/interview/evaluate",
                            json={
                                "question": current_qa.question if current_qa else "",
                                "user_answer": user_answer,
                                "role": session.role
                            }
                        )
                        if resp.status_code == 200:
                            eval_result = resp.json()
                except Exception:
                    eval_result = load_mock_eval()

                if not eval_result:
                    eval_result = load_mock_eval()

                score = float(eval_result.get("score", 8.2))
                tech_score = float(eval_result.get("technical_score", 8.8))
                comm_score = float(eval_result.get("communication_score", 7.9))
                behav_score = float(eval_result.get("behavioral_score", 7.9))
                conf_score = float(eval_result.get("confidence_score", 7.4))
                star_score = float(eval_result.get("star_score", 8.0))
                feedback = eval_result.get("feedback", "Good attempt.")
                weak_topics = eval_result.get("weak_topics", [])

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

                # Trigger Feedback-Loop for weak topics
                for topic in weak_topics:
                    score_delta = score - 7.0
                    update_topic_mastery(db, user_id=user_id, topic=topic, score_delta=score_delta)

                turn_number += 1
                next_question = eval_result.get("next_question", f"Follow up question {turn_number}: How do you handle context switching and process isolation in operating systems?")

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
                    "turn_number": turn_number,
                    "next_question": next_question
                })

            elif event == "end":
                if session:
                    session.status = "completed"
                    session.ended_at = datetime.utcnow()
                    
                    qas = db.query(QuestionAnswer).filter(QuestionAnswer.session_id == session.id).all()
                    scores = [q.score for q in qas if q.score > 0]
                    session.average_score = (sum(scores) / len(scores)) * 10.0 if scores else 82.0
                    session.technical_score = 88.0
                    session.communication_score = 79.0
                    session.behavioral_score = 79.0
                    session.confidence_score = 74.0
                    session.star_score = 80.0
                    
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
