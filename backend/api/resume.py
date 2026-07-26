from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, status
from sqlalchemy.orm import Session
from starlette.concurrency import run_in_threadpool
import pdfplumber
import logging
import io

from backend.core.database import get_db
from backend.core.auth import get_current_user
from backend.models.user import User
from backend.models.resume import Resume
from backend.schemas.resume import ResumeResponse

from ai.agents.resume_agent import ResumeAgent

router = APIRouter(prefix="/resume", tags=["Resume Pipeline"])
logger = logging.getLogger("resume")

resume_agent = ResumeAgent()


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
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Could not read this PDF - it may be corrupted or image-only (no extractable text).",
        )

    if not extracted_text.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No text could be extracted from this PDF.",
        )

    # Real Resume Agent call (Granite LLM). ResumeAgent already has its own
    # internal fallback (fallback_used=True, score=50) if the model output
    # can't be parsed as structured JSON - this try/except only covers the
    # LLM call itself failing to run at all (e.g. Ollama not running).
    try:
        agent_score_data = await run_in_threadpool(resume_agent.analyze_resume, extracted_text)
    except Exception as exc:
        logger.warning("Resume agent call failed (%s); AI reviewer is unavailable.", exc)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="The AI resume reviewer is temporarily unavailable. Please try again shortly.",
        )

    resume_entry = Resume(
        user_id=current_user.id,
        filename=file.filename,
        parsed_text=extracted_text[:3000],
        score=agent_score_data["score"],
        ats_score=agent_score_data["ats_score"],
        keyword_count=agent_score_data["keyword_count"],
        resume_feedback=agent_score_data["resume_feedback"],
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
        keyword_count=resume_entry.keyword_count,
        resume_feedback=resume_entry.resume_feedback,
        parsed_text_preview=resume_entry.parsed_text[:200] if resume_entry.parsed_text else "",
        score_details=resume_entry.score_details,
        uploaded_at=resume_entry.uploaded_at
    )


@router.get("/", response_model=list[ResumeResponse])
def list_resumes(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    resumes = (
        db.query(Resume)
        .filter(Resume.user_id == current_user.id)
        .order_by(Resume.uploaded_at.desc())
        .all()
    )
    return [
        ResumeResponse(
            id=r.id,
            filename=r.filename,
            score=r.score,
            ats_score=r.ats_score,
            keyword_count=r.keyword_count,
            resume_feedback=r.resume_feedback,
            parsed_text_preview=r.parsed_text[:200] if r.parsed_text else "",
            score_details=r.score_details,
            uploaded_at=r.uploaded_at,
        )
        for r in resumes
    ]
