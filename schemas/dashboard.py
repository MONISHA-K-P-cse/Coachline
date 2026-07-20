from pydantic import BaseModel
from typing import Optional, List, Dict, Any

class DashboardSummaryResponse(BaseModel):
    user_id: int
    full_name: Optional[str] = None
    target_role: Optional[str] = None
    latest_resume_score: int
    roadmap_progress_percentage: int
    total_notes_count: int
    bookmarked_notes_count: int
    total_interviews_conducted: int
    average_interview_score: float
    weak_topics: List[str] = []
