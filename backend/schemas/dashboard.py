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
    days_until_interview: Optional[int] = None
    panic_mode: bool = False
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

class ActivityHeatmapEntry(BaseModel):
    date: str  # YYYY-MM-DD
    interviews: int
    notes: int
    resumes: int
    total: int

class ActivityHeatmapResponse(BaseModel):
    days: List[ActivityHeatmapEntry]

class TopicMasteryEntry(BaseModel):
    topic: str
    mastery_score: float
    needs_regeneration: bool
    updated_at: datetime

    class Config:
        from_attributes = True
