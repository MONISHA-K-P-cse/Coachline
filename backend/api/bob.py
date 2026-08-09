from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from typing import List, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import flag_modified

from backend.core.database import get_db
from backend.models.user import User
from backend.models.bob import BobChallengeResult
from backend.models.mastery import TopicMastery
from backend.models.roadmap import Roadmap
from backend.api.auth import get_current_user
from ai.agents.bob_agent import BobAgent

router = APIRouter(prefix="/bob", tags=["IBM Bob Developer Agent"])
bob_agent = BobAgent()

class CodeAuditRequest(BaseModel):
    code: str
    challenge_id: str
    language: str = "python"

class VulnerabilityItem(BaseModel):
    severity: str
    line: int
    issue: str
    fix: str

class CodeAuditResponse(BaseModel):
    plan: List[str]
    vulnerabilities: List[VulnerabilityItem]
    refactored_code: str
    score: int

class ChallengeRecommendation(BaseModel):
    challenge_id: str
    topic: str
    reason: str

@router.get("/recommendation", response_model=ChallengeRecommendation)
async def get_challenge_recommendation(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Find weakest topic from mastery
    weakest_mastery = db.query(TopicMastery).filter(
        TopicMastery.user_id == current_user.id
    ).order_by(TopicMastery.mastery_score.asc()).first()
    
    weak_topic = None
    if weakest_mastery and weakest_mastery.mastery_score < 70:
        weak_topic = weakest_mastery.topic
        
    # If no weak mastery, retrieve from last interview session
    if not weak_topic and current_user.interviews:
        latest_interview = current_user.interviews[-1]
        metadata = latest_interview.metadata_json or {}
        weak_list = metadata.get("weak_topics", [])
        if weak_list:
            weak_topic = weak_list[0]

    # Map weak topic to Bob's security challenge
    challenge_id = "sql_injection"
    topic_name = "DBMS"
    reason = "Based on your target role, Bob recommends starting with the SQL Injection challenge."

    if weak_topic:
        wt_lower = weak_topic.lower()
        if any(k in wt_lower for k in ["api security", "cors", "network", "headers", "cn"]):
            challenge_id = "cors_security"
            topic_name = "API Security"
            reason = f"Your CoachLine evaluation flags weakness in {weak_topic}. Bob recommends patching this CORS misconfiguration."
        elif any(k in wt_lower for k in ["dbms", "database", "sql", "query"]):
            challenge_id = "sql_injection"
            topic_name = "DBMS"
            reason = f"Your CoachLine evaluation flags weakness in {weak_topic}. Bob recommends optimizing secure SQL data retrievals."
        elif any(k in wt_lower for k in ["concurrency", "lock", "race", "threads", "thread"]):
            challenge_id = "concurrency_race"
            topic_name = "Concurrency / OS"
            reason = f"Your CoachLine evaluation flags weakness in {weak_topic}. Bob recommends fixing this multithreaded race condition."
        elif any(k in wt_lower for k in ["xss", "script", "html", "frontend"]):
            challenge_id = "xss_scripting"
            topic_name = "API Security"
            reason = f"Your CoachLine evaluation flags weakness in {weak_topic}. Bob recommends fixing this inline script XSS injection."
        elif any(k in wt_lower for k in ["path", "file", "directory", "os"]):
            challenge_id = "path_traversal"
            topic_name = "OS"
            reason = f"Your CoachLine evaluation flags weakness in {weak_topic}. Bob recommends shielding local directories from path traversal."

    return {
        "challenge_id": challenge_id,
        "topic": topic_name,
        "reason": reason
    }

@router.post("/audit", response_model=CodeAuditResponse)
async def run_code_audit(
    request: CodeAuditRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        result = bob_agent.audit_code(request.code, request.challenge_id)
        score = result.get("score", 50)
        
        # Save Bob Challenge Result
        bob_res = BobChallengeResult(
            user_id=current_user.id,
            challenge_id=request.challenge_id,
            score=score,
            submitted_code=request.code,
            vulnerabilities_json=result.get("vulnerabilities", [])
        )
        db.add(bob_res)
        
        # Determine topic name based on challenge_id
        topic_name = "API Security"
        if request.challenge_id == "sql_injection":
            topic_name = "DBMS"
        elif request.challenge_id == "concurrency_race":
            topic_name = "OS"
        elif request.challenge_id == "path_traversal":
            topic_name = "OS"

        # Update topic mastery score
        mastery = db.query(TopicMastery).filter(
            TopicMastery.user_id == current_user.id,
            TopicMastery.topic == topic_name
        ).first()
        if not mastery:
            mastery = TopicMastery(
                user_id=current_user.id,
                topic=topic_name,
                mastery_score=float(score)
            )
            db.add(mastery)
        else:
            mastery.mastery_score = float(score)

        # Update user's learning roadmap to inject practice step if score < 85
        if score < 85:
            roadmap = db.query(Roadmap).filter(Roadmap.user_id == current_user.id).first()
            if roadmap:
                steps_data = roadmap.steps_json or {}
                if "steps" in steps_data:
                    step_title = f"Remedial Practice: {topic_name}"
                    # Check if exists
                    exists = any(s.get("title") == step_title for s in steps_data["steps"])
                    if not exists:
                        new_step_num = len(steps_data["steps"]) + 1
                        new_step = {
                            "step_number": new_step_num,
                            "title": step_title,
                            "description": f"Targeted hands-on exercises to reinforce {topic_name} concepts, prompted by your IBM Bob score of {score}/100.",
                            "estimated_hours": 5,
                            "status": "pending"
                        }
                        steps_data["steps"].append(new_step)
                        roadmap.steps_json = steps_data
                        flag_modified(roadmap, "steps_json")

        db.commit()
        return result
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"IBM Bob Code Audit failed: {str(e)}"
        )
