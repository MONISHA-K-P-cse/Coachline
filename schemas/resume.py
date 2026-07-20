from pydantic import BaseModel
from typing import Optional, Dict, Any, List
from datetime import datetime

class ResumeResponse(BaseModel):
    id: int
    filename: str
    score: int
    ats_score: int
    resume_feedback: Optional[str] = None
    parsed_text_preview: Optional[str] = None
    score_details: Optional[Dict[str, Any]] = None
    uploaded_at: datetime

    class Config:
        from_attributes = True

class ResumeScore(BaseModel):
    score: int
    ats_score: int
    summary: str
    resume_feedback: str
    strengths: List[str]
    improvements: List[str]
    fallback_used: bool = False
