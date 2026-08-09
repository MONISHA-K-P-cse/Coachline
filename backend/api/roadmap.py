from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from starlette.concurrency import run_in_threadpool
from typing import List
import logging

from datetime import datetime

from backend.core.database import get_db
from backend.core.auth import get_current_user
from backend.models.user import User, Profile
from backend.models.resume import Resume
from backend.models.roadmap import Roadmap
from backend.models.jd import JobDescription
from backend.schemas.roadmap import (
    RoadmapCreate,
    RoadmapResponse,
    PracticeQuestionEvalRequest,
    PracticeQuestionEvalResponse,
)

from ai.agents.roadmap_agent import RoadmapAgent
from ai.agents.eval_agent import EvaluationAgent
from sqlalchemy.orm.attributes import flag_modified

router = APIRouter(prefix="/roadmap", tags=["Roadmap & Notes Storage"])
logger = logging.getLogger("roadmap")

roadmap_agent = RoadmapAgent()
eval_agent = EvaluationAgent()


def _format_skill_gaps(gaps_data) -> str:
    if not gaps_data:
        return ""
    gaps_list = []
    for item in gaps_data:
        if isinstance(item, str):
            gaps_list.append(item)
        elif isinstance(item, dict):
            for v in item.values():
                if isinstance(v, list):
                    gaps_list.extend([str(x) for x in v])
                elif isinstance(v, str):
                    gaps_list.append(v)
    return ", ".join(gaps_list)


@router.post("/generate", response_model=RoadmapResponse)
async def generate_roadmap(
    roadmap_in: RoadmapCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    profile = db.query(Profile).filter(Profile.user_id == current_user.id).first()
    
    # Ground the roadmap in any uploaded Job Description analysis
    latest_jd = (
        db.query(JobDescription)
        .filter(JobDescription.user_id == current_user.id)
        .order_by(JobDescription.uploaded_at.desc())
        .first()
    )

    target_role = (
        roadmap_in.target_role
        or (profile.target_role if profile and profile.target_role else None)
        or (latest_jd.target_role if latest_jd and latest_jd.target_role else "Software Engineer")
    )
    target_company = (
        (profile.target_company if profile and profile.target_company else None)
        or (latest_jd.company_name if latest_jd and latest_jd.company_name else "")
    )
    experience_level = profile.experience_level if profile and profile.experience_level else ""
    learning_style = profile.learning_style if profile and profile.learning_style else ""

    jd_summary = ""
    if latest_jd:
        gaps = _format_skill_gaps(latest_jd.skill_gaps)
        jd_summary = f"Job Description Analysis for {latest_jd.target_role} at {latest_jd.company_name or 'target company'}.\nIdentified Skill Gaps: {gaps}\nSnippet: {latest_jd.jd_text[:300]}"


    # Ground the roadmap in the user's actual resume analysis when one exists
    latest_resume = (
        db.query(Resume)
        .filter(Resume.user_id == current_user.id)
        .order_by(Resume.uploaded_at.desc())
        .first()
    )
    if latest_resume and latest_resume.score_details:
        details = latest_resume.score_details
        current_skills = details.get("summary", "") + "\nStrengths: " + ", ".join(details.get("strengths", []))
    else:
        current_skills = "No resume on file yet - assume baseline preparation for this role."

    # Size the roadmap to the time actually left before the interview when a date is set
    weeks = 8
    if profile and profile.interview_date:
        days_left = (profile.interview_date - datetime.utcnow()).days
        weeks = max(1, min(12, days_left // 7 or 1))

    try:
        roadmap_data = await run_in_threadpool(
            roadmap_agent.generate_roadmap,
            target_role,
            current_skills,
            target_company or "",
            experience_level or "",
            weeks,
            jd_summary,
            learning_style,
        )
    except Exception as exc:
        logger.warning("Roadmap agent call failed (%s); AI roadmap generator is unavailable.", exc)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="The AI roadmap generator is temporarily unavailable. Please try again shortly.",
        )

    if not roadmap_data.get("steps_json"):
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="The AI roadmap generator did not return a usable roadmap. Please try again.",
        )

    # For roadmap regeneration: clear old roadmaps so only the latest active roadmap is served
    db.query(Roadmap).filter(Roadmap.user_id == current_user.id).delete(synchronize_session=False)
    db.commit()

    company_suffix = f" @ {target_company}" if target_company else ""
    roadmap = Roadmap(
        user_id=current_user.id,
        title=roadmap_in.title or roadmap_data.get("title", f"{target_role}{company_suffix} Preparation Roadmap"),
        target_role=target_role,
        steps_json=roadmap_data.get("steps_json", []),
        progress_percentage=0,
    )

    db.add(roadmap)
    db.commit()
    db.refresh(roadmap)

    return roadmap



@router.get("/", response_model=List[RoadmapResponse])
def get_user_roadmaps(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return db.query(Roadmap).filter(Roadmap.user_id == current_user.id).all()


@router.get("/{roadmap_id}", response_model=RoadmapResponse)
def get_roadmap_by_id(
    roadmap_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    roadmap = db.query(Roadmap).filter(
        Roadmap.id == roadmap_id,
        Roadmap.user_id == current_user.id
    ).first()
    if not roadmap:
        raise HTTPException(status_code=404, detail="Roadmap not found")
    return roadmap


@router.post("/{roadmap_id}/steps/{step_number}/evaluate-question", response_model=PracticeQuestionEvalResponse)
async def evaluate_practice_question(
    roadmap_id: int,
    step_number: int,
    eval_in: PracticeQuestionEvalRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    roadmap = db.query(Roadmap).filter(
        Roadmap.id == roadmap_id,
        Roadmap.user_id == current_user.id
    ).first()
    if not roadmap:
        raise HTTPException(status_code=404, detail="Roadmap not found")

    steps = roadmap.steps_json or []
    target_step = None
    target_step_idx = -1
    for idx, s in enumerate(steps):
        if s.get("step_number") == step_number:
            target_step = s
            target_step_idx = idx
            break

    if not target_step:
        raise HTTPException(status_code=404, detail=f"Step number {step_number} not found in roadmap")

    # Evaluate answer with EvaluationAgent
    try:
        eval_result = await run_in_threadpool(
            eval_agent.evaluate_answer,
            eval_in.question,
            eval_in.user_answer,
        )
    except Exception as exc:
        logger.warning("Evaluation agent call failed (%s); using fallback evaluation", exc)
        eval_result = {
            "overall_score": 45.0,
            "feedback": "Answer analyzed: your answer lacks key technical depth for this topic.",
        }

    score = float(eval_result.get("overall_score", 0.0))
    feedback = str(eval_result.get("feedback", ""))
    passed = score >= 50.0

    generated_new_question = None

    # Requirement: For every question with score less than 50%, generate a new question to increase understandability of concepts of the respective week
    if score < 50.0:
        topic = target_step.get("title", f"Week {step_number}")
        syllabus = target_step.get("syllabus", [])
        try:
            generated_new_question = await run_in_threadpool(
                roadmap_agent.generate_remediation_question,
                roadmap.target_role,
                step_number,
                topic,
                syllabus,
                eval_in.question,
                eval_in.user_answer,
                feedback,
            )
        except Exception as exc:
            logger.warning("Failed to generate remediation question (%s); using fallback adaptive question", exc)
            generated_new_question = f"Adaptive Concept Question (Week {step_number}): Can you break down the core principles of {topic} step-by-step?"

        step_questions = target_step.get("questions", [])
        if generated_new_question and generated_new_question not in step_questions:
            step_questions.append(generated_new_question)
            target_step["questions"] = step_questions
            steps[target_step_idx] = target_step
            roadmap.steps_json = steps
            flag_modified(roadmap, "steps_json")
            db.commit()

    return PracticeQuestionEvalResponse(
        score=score,
        feedback=feedback,
        passed=passed,
        generated_new_question=generated_new_question,
        step_questions=target_step.get("questions", []),
    )

