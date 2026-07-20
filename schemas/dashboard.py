from pydantic import BaseModel
from typing import Optional, List, Dict, Any

class DashboardSummaryResponse(BaseModel):
    user_id: int
    full_name: Optional[str] = None
    target_role: Optional[str] = None
    target_company: Optional[str] = None
    latest_resume_score: int
    latest_ats_score: int
    roadmap_progress_percentage: int
    total_notes_count: int
    bookmarked_notes_count: int
    total_interviews_conducted: int
    average_interview_score: float
    weak_topics: List[str] = []
    recommendations: List[str] = []
