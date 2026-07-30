from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from starlette.concurrency import run_in_threadpool
import json
import os

from backend.core.database import get_db
from backend.core.auth import get_current_user
from backend.core.config import settings
from backend.models.user import User
from backend.models.jd import JobDescription
from backend.schemas.jd import JobDescriptionCreate, JobDescriptionResponse

from ai.agents.jd_agent import JobDescriptionAgent

router = APIRouter(prefix="/job-description", tags=["JD & Skill Gap Analysis"])
jd_agent = JobDescriptionAgent()

MOCK_JD_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "mocks", "jd_agent.json")

def load_mock_jd_analysis() -> dict:
    if os.path.exists(MOCK_JD_PATH):
        with open(MOCK_JD_PATH, "r") as f:
            return json.load(f)
    return {
        "skill_gaps": [
            {"category": "Missing Skills", "missing_skills": ["Redis Caching", "Kafka"], "priority": "High"}
        ]
    }

@router.post("/upload", response_model=JobDescriptionResponse)
async def upload_job_description(
    jd_in: JobDescriptionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        analysis_data = await run_in_threadpool(
            jd_agent.analyze_jd,
            jd_in.target_role,
            jd_in.company_name or "",
            jd_in.jd_text
        )
    except Exception:
        analysis_data = load_mock_jd_analysis()

    if not analysis_data:
        analysis_data = load_mock_jd_analysis()

    jd_entry = JobDescription(
        user_id=current_user.id,
        target_role=jd_in.target_role,
        company_name=jd_in.company_name,
        jd_text=jd_in.jd_text,
        skill_gaps=analysis_data.get("skill_gaps", []),
    )

    db.add(jd_entry)
    db.commit()
    db.refresh(jd_entry)

    return jd_entry
