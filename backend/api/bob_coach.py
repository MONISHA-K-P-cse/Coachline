from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import flag_modified
from typing import List, Dict, Any

from backend.core.database import get_db
from backend.models.user import User, Profile
from backend.models.bob import BobCoachSession
from backend.models.mastery import TopicMastery
from backend.models.roadmap import Roadmap
from backend.api.auth import get_current_user
from backend.schemas.bob_coach import (
    BobCoachStartRequest,
    BobCoachStartResponse,
    BobCoachRespondRequest,
    BobCoachRespondResponse,
    BobCoachEvaluationResponse,
    BobCoachTurn
)
from ai.agents.bob_coach_agent import BobCoachAgent

router = APIRouter(prefix="/bob/coach", tags=["IBM Bob Scenario Coach"])
bob_coach_agent = BobCoachAgent()

# Limit the dialogue to 5 candidate turns (10 turns total including Bob's questions)
MAX_CANDIDATE_TURNS = 5

@router.post("/start", response_model=BobCoachStartResponse)
async def start_scenario(
    request: BobCoachStartRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    profile = current_user.profile
    target_role = request.target_role or (profile.target_role if profile else "Software Engineer")
    experience_level = profile.experience_level if profile else "Mid-Level"

    # Compile candidate context
    resume_skills = ""
    if current_user.resumes:
        latest_res = current_user.resumes[-1]
        resume_skills = latest_res.parsed_text[:500] if latest_res.parsed_text else ""

    weakness = "System Design"
    if current_user.interviews:
        meta = current_user.interviews[-1].metadata_json or {}
        weak_list = meta.get("weak_topics", [])
        if weak_list:
            weakness = weak_list[0]

    mastery_summary = ""
    if current_user.mastery_scores:
        scores = [f"{m.topic}: {int(m.mastery_score)}%" for m in current_user.mastery_scores]
        mastery_summary = ", ".join(scores)

    language = request.language or "Python"
    # Start Scenario via Granite
    result = bob_coach_agent.start_scenario(
        target_role=target_role,
        experience_level=experience_level,
        resume_skills=resume_skills,
        weakness=weakness,
        mastery_summary=mastery_summary,
        language=language
    )

    next_q = result.get("next_question", "")
    difficulty = result.get("difficulty", "medium")
    topic = result.get("topic", "System Design")
    reasoning_focus = result.get("reasoning_focus", "scalability")

    # Save Session
    session = BobCoachSession(
        user_id=current_user.id,
        target_role=target_role,
        topic=f"{topic} ({language})",
        difficulty=difficulty,
        conversation_json=[{"sender": "bob", "text": next_q}],
        completed=False
    )
    db.add(session)
    db.commit()
    db.refresh(session)

    return {
        "session_id": session.id,
        "next_question": next_q,
        "difficulty": difficulty,
        "topic": topic,
        "reasoning_focus": reasoning_focus
    }

@router.post("/respond", response_model=BobCoachRespondResponse)
async def respond_to_scenario(
    request: BobCoachRespondRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    session = db.query(BobCoachSession).filter(
        BobCoachSession.id == request.session_id,
        BobCoachSession.user_id == current_user.id
    ).first()

    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Scenario session not found."
        )

    if session.completed:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This scenario has already been evaluated."
        )

    conversation = list(session.conversation_json)
    conversation.append({"sender": "candidate", "text": request.candidate_response})

    # Count how many turns the candidate has taken
    candidate_turns_count = sum(1 for t in conversation if t["sender"] == "candidate")

    # Extract language from topic (e.g. "Algorithms (Python)" -> "Python")
    language = "Python"
    if "(" in session.topic and ")" in session.topic:
        language = session.topic.split("(")[-1].split(")")[0]

    if candidate_turns_count >= MAX_CANDIDATE_TURNS:
        # Trigger Evaluation
        session.completed = True
        session.conversation_json = conversation
        flag_modified(session, "conversation_json")
        db.commit()

        # Run AI Evaluation via Granite
        eval_res = bob_coach_agent.evaluate_scenario(conversation, session.target_role)
        session.evaluation_json = eval_res
        
        # Get overall score
        eval_scores = eval_res.get("evaluation", {})
        overall_score = eval_scores.get("overall", 70)
        session.overall_score = overall_score
        
        # 1. Update Topic Mastery based on evaluation
        # Map session topic to mastery key topic
        topic_name = "System Design"
        if "frontend" in session.target_role.lower():
            topic_name = "System Design"  # or specific UI topic
        
        topic_mastery = db.query(TopicMastery).filter(
            TopicMastery.user_id == current_user.id,
            TopicMastery.topic == topic_name
        ).first()

        if not topic_mastery:
            topic_mastery = TopicMastery(
                user_id=current_user.id,
                topic=topic_name,
                mastery_score=float(overall_score)
            )
            db.add(topic_mastery)
        else:
            topic_mastery.mastery_score = float(overall_score)
        
        # 2. Add remedial step in roadmap if score under 85%
        if overall_score < 85:
            roadmap = db.query(Roadmap).filter(
                Roadmap.user_id == current_user.id
            ).first()
            if roadmap:
                steps = list(roadmap.steps_json)
                # Check if steps already has a Bob Practice step to avoid duplicates
                already_exists = any("Bob Challenge" in s.get("title", "") for s in steps)
                if not already_exists:
                    new_step = {
                        "step_number": len(steps) + 1,
                        "title": f"Remedial Practice: {topic_name} (Bob Challenge)",
                        "description": f"Targeted hands-on system architectural practice based on Bob Scenario score of {overall_score}/100.",
                        "estimated_hours": 6,
                        "status": "pending"
                    }
                    steps.append(new_step)
                    roadmap.steps_json = steps
                    flag_modified(roadmap, "steps_json")
        
        db.commit()

        return {
            "next_question": "Scenario finished! Click to view your detailed technical evaluation.",
            "difficulty": session.difficulty,
            "topic": session.topic,
            "reasoning_focus": "evaluation",
            "completed": True
        }
    else:
        # Continue scenario conversation: Play Devil's Advocate
        result = bob_coach_agent.respond_to_candidate(
            conversation_history=conversation,
            candidate_response=request.candidate_response,
            target_role=session.target_role,
            difficulty=session.difficulty,
            language=language
        )

        next_q = result.get("next_question", "")
        difficulty = result.get("difficulty", session.difficulty)
        topic = result.get("topic", session.topic)
        reasoning_focus = result.get("reasoning_focus", "tradeoffs")

        conversation.append({"sender": "bob", "text": next_q})
        session.conversation_json = conversation
        session.difficulty = difficulty
        session.topic = topic
        flag_modified(session, "conversation_json")
        db.commit()

        return {
            "next_question": next_q,
            "difficulty": difficulty,
            "topic": topic,
            "reasoning_focus": reasoning_focus,
            "completed": False
        }

@router.get("/session/{session_id}", response_model=Dict[str, Any])
def get_session_details(
    session_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    session = db.query(BobCoachSession).filter(
        BobCoachSession.id == session_id,
        BobCoachSession.user_id == current_user.id
    ).first()

    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found."
        )

    return {
        "id": session.id,
        "target_role": session.target_role,
        "topic": session.topic,
        "difficulty": session.difficulty,
        "conversation": session.conversation_json,
        "evaluation": session.evaluation_json,
        "overall_score": session.overall_score,
        "completed": session.completed,
        "created_at": session.created_at.isoformat()
    }

@router.get("/history", response_model=List[Dict[str, Any]])
def get_coach_history(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    sessions = db.query(BobCoachSession).filter(
        BobCoachSession.user_id == current_user.id
    ).order_by(BobCoachSession.created_at.desc()).all()

    return [
        {
            "id": s.id,
            "target_role": s.target_role,
            "topic": s.topic,
            "difficulty": s.difficulty,
            "overall_score": s.overall_score,
            "completed": s.completed,
            "created_at": s.created_at.isoformat()
        }
        for s in sessions
    ]
