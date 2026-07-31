from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session
from starlette.concurrency import run_in_threadpool
import pdfplumber
import docx
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


def extract_text_from_docx(file_bytes: bytes) -> str:
    doc = docx.Document(io.BytesIO(file_bytes))
    paragraphs_text = "\n".join([p.text for p in doc.paragraphs])
    
    table_texts = []
    for table in doc.tables:
        for row in table.rows:
            row_text = [cell.text.strip() for cell in row.cells if cell.text.strip()]
            if row_text:
                table_texts.append(" | ".join(row_text))
    
    if table_texts:
        paragraphs_text += "\n\n" + "\n".join(table_texts)
    return paragraphs_text


@router.post("/upload", response_model=ResumeResponse)
async def upload_resume(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    filename_lower = file.filename.lower()
    if not (filename_lower.endswith(".pdf") or filename_lower.endswith(".docx")):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only PDF and DOCX files are supported."
        )

    file_bytes = await file.read()
    extracted_text = ""

    try:
        if filename_lower.endswith(".pdf"):
            with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
                for page in pdf.pages:
                    text = page.extract_text()
                    if text:
                        extracted_text += text + "\n"
        else:
            extracted_text = extract_text_from_docx(file_bytes)
    except Exception as exc:
        logger.error("Failed to parse resume: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Could not read this file - it may be corrupted or contain no extractable text.",
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


@router.post("/{resume_id}/improve")
async def improve_resume_endpoint(
    resume_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    resume = db.query(Resume).filter(
        Resume.id == resume_id,
        Resume.user_id == current_user.id
    ).first()

    if not resume:
        raise HTTPException(status_code=404, detail="Resume not found")

    improvements = []
    if resume.score_details and "improvements" in resume.score_details:
        improvements = resume.score_details["improvements"]
    if not improvements:
        improvements = ["Add more quantifiable metrics", "Clarify cloud deployment tools"]

    try:
        opt_data = await run_in_threadpool(
            resume_agent.improve_resume,
            resume.parsed_text or "",
            improvements
        )
    except Exception as exc:
        logger.error("Failed to run resume optimizer: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="The resume optimizer is temporarily offline. Please try again later.",
        )

    return opt_data


class PDFGenerationRequest(BaseModel):
    text: str
    filename: str | None = "improved_resume.pdf"


@router.post("/generate-pdf")
async def generate_pdf_endpoint(req: PDFGenerationRequest):
    try:
        from reportlab.lib.pagesizes import letter
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.enums import TA_CENTER
    except ImportError:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="PDF generation library is not available."
        )

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=54,
        leftMargin=54,
        topMargin=54,
        bottomMargin=54
    )

    import re
    from reportlab.lib.enums import TA_CENTER

    def markdown_to_html(txt: str) -> str:
        escaped = txt.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
        escaped = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', escaped)
        escaped = re.sub(r'\*(.*?)\*', r'<i>\1</i>', escaped)
        return escaped

    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        name='TitleStyle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=18,
        leading=22,
        alignment=TA_CENTER,
        textColor='#1C1917',
        spaceAfter=12
    )

    heading_style = ParagraphStyle(
        name='HeadingStyle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=13,
        leading=16,
        textColor='#B5502E',
        spaceBefore=10,
        spaceAfter=4,
        keepWithNext=True
    )

    subheading_style = ParagraphStyle(
        name='SubHeadingStyle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=11,
        leading=14.5,
        textColor='#1C1917',
        spaceBefore=6,
        spaceAfter=2,
        keepWithNext=True
    )

    body_style = ParagraphStyle(
        name='BodyStyle',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=10,
        leading=14,
        textColor='#1C1917',
        spaceAfter=2
    )

    story = []

    lines = req.text.split('\n')
    for line in lines:
        line_clean = line.rstrip()
        if not line_clean:
            story.append(Spacer(1, 6))
            continue

        leading_spaces = len(line_clean) - len(line_clean.lstrip(' '))
        content = line_clean.lstrip(' ')

        if content.startswith('#'):
            hash_count = len(content) - len(content.lstrip('#'))
            header_text = content.lstrip('#').strip()
            formatted_text = markdown_to_html(header_text)
            
            if hash_count == 1:
                story.append(Paragraph(formatted_text, title_style))
            elif hash_count == 2:
                story.append(Paragraph(formatted_text, heading_style))
            else:
                story.append(Paragraph(formatted_text, subheading_style))
        else:
            formatted_content = markdown_to_html(content)
            formatted_text = "&nbsp;" * leading_spaces + formatted_content
            story.append(Paragraph(formatted_text, body_style))

    doc.build(story)
    buffer.seek(0)

    filename = req.filename or "improved_resume.pdf"
    if not filename.endswith(".pdf"):
        filename += ".pdf"

    return StreamingResponse(
        buffer,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )
