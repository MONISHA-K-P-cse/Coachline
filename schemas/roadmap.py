from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime

class NoteCreate(BaseModel):
    roadmap_id: Optional[int] = None
    topic: str
    title: str
    content: str
    is_bookmarked: bool = False

class NoteResponse(BaseModel):
    id: int
    roadmap_id: Optional[int] = None
    topic: str
    title: str
    content: str
    is_bookmarked: bool
    created_at: datetime

    class Config:
        from_attributes = True

class RoadmapCreate(BaseModel):
    target_role: str
    title: Optional[str] = None

class RoadmapStep(BaseModel):
    step_number: int
    title: str
    description: str
    estimated_hours: int
    status: str = "pending"  # pending, in_progress, completed

class RoadmapResponse(BaseModel):
    id: int
    title: str
    target_role: str
    steps_json: List[Dict[str, Any]]
    progress_percentage: int
    created_at: datetime

    class Config:
        from_attributes = True
