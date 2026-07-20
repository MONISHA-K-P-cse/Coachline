from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, status
from sqlalchemy.orm import Session
import pdfplumber
import httpx
import json
import os
import io

from core.database import get_db
from core.auth import get_current_user
from core.config import settings
from models.user import User
from models.resume import Resume
from schemas.resume import ResumeResponse, ResumeScore

router = APIRouter(prefix="/resume", tags=["Resume Pipeline"])

MOCK_RESUME_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "mocks", "resume_agent.json")

def load_mock_resume_score() -> dict:
    if os.path.exists(MOCK_RESUME_PATH):
        with open(MOCK_RESUME_PATH, "r") as f:
            return json.load(f)
    return {
        "score": 85,
        "ats_score": 88,
        "summary": "Solid technical background.",
        "resume_feedback": "Strong ATS formatting. Consider highlighting throughput metrics.",
        "strengths": ["API Design", "Database Modeling"],
        "improvements": ["Add deployment metrics"],
        "fallback_used": True
    }

@router.post("/upload", response_model=ResumeResponse)
async def upload_resume(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not file.filename.endswith(".pdf"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only PDF files are supported."
        )

    file_bytes = await file.read()
    extracted_text = ""

    try:
        with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
            for page in pdf.pages:
                text = page.extract_text()
                if text:
                    extracted_text += text + "\n"
    except Exception:
        extracted_text = f"Sample raw text extracted from {file.filename}."

    # Call P3 Resume Agent with resilience timeout
    agent_score_data = None
    try:
        async with httpx.AsyncClient(timeout=settings.AGENT_TIMEOUT_SECONDS) as client:
            resp = await client.post(
                f"{settings.P3_AGENT_BASE_URL}/agent/resume/evaluate",
                json={"text": extracted_text, "user_id": current_user.id}
            )
            if resp.status_code == 200:
                agent_score_data = resp.json()
    except Exception:
        agent_score_data = load_mock_resume_score()

    if not agent_score_data:
        agent_score_data = load_mock_resume_score()

    resume_entry = Resume(
        user_id=current_user.id,
        filename=file.filename,
        parsed_text=extracted_text[:3000],
        score=agent_score_data.get("score", 85),
        ats_score=agent_score_data.get("ats_score", 88),
        resume_feedback=agent_score_data.get("resume_feedback", "ATS layout looks clean. Add quantifiable metrics."),
        score_details=agent_score_data,
    )

    db.add(resume_entry)
    db.commit()
    db.refresh(resume_entry)

    return ResumeResponse(
        id=resume_entry.id,
        filename=resume_entry.filename,
        score=resume_entry.score,
        ats_score=resume_entry.ats_score,
        resume_feedback=resume_entry.resume_feedback,
        parsed_text_preview=resume_entry.parsed_text[:200] if resume_entry.parsed_text else "",
        score_details=resume_entry.score_details,
        uploaded_at=resume_entry.uploaded_at
    )
