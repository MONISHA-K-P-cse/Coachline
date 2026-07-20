from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
import httpx
import json
import os

from core.database import get_db
from core.auth import get_current_user
from core.config import settings
from models.user import User
from models.jd import JobDescription
from schemas.jd import JobDescriptionCreate, JobDescriptionResponse

router = APIRouter(prefix="/job-description", tags=["JD & Skill Gap Analysis"])

MOCK_JD_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "mocks", "jd_agent.json")

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
    analysis_data = None
    try:
        async with httpx.AsyncClient(timeout=settings.AGENT_TIMEOUT_SECONDS) as client:
            resp = await client.post(
                f"{settings.P3_AGENT_BASE_URL}/agent/jd/analyze",
                json={
                    "target_role": jd_in.target_role,
                    "company_name": jd_in.company_name,
                    "jd_text": jd_in.jd_text,
                    "user_id": current_user.id
                }
            )
            if resp.status_code == 200:
                analysis_data = resp.json()
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
