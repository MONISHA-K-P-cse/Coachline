from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime

class InterviewScoreBreakdown(BaseModel):
    overall_score: float
    technical_score: float
    communication_score: float
    behavioral_score: float
    confidence_score: float
    star_score: float

class DashboardSummaryResponse(BaseModel):
    user_id: int
    full_name: Optional[str] = None
    target_role: Optional[str] = None
    target_company: Optional[str] = None
    interview_date: Optional[datetime] = None
    overall_readiness_score: int
    latest_resume_score: int
    latest_ats_score: int
    keyword_count: int
    roadmap_progress_percentage: int
    total_notes_count: int
    bookmarked_notes_count: int
    total_interviews_conducted: int
    interview_scores: InterviewScoreBreakdown
    weak_topics: List[str] = []
    recommendations: List[str] = []
