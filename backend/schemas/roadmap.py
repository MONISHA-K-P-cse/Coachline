from pydantic import BaseModel
from typing import Optional, List, Dict, Any, Literal
from datetime import datetime

class NoteBlock(BaseModel):
    type: Literal["text", "diagram", "exercise"]
    content: str

class NoteCreate(BaseModel):
    roadmap_id: Optional[int] = None
    topic: str
    title: str
    content: str
    note_type: Optional[str] = "detailed_note"  # short_note, detailed_note, cheat_sheet, flashcard, mcq
    category: Optional[str] = "System Design"
    is_bookmarked: bool = False

class NoteResponse(BaseModel):
    id: int
    roadmap_id: Optional[int] = None
    topic: str
    title: str
    content: str
    note_type: str
    category: str
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
    syllabus: List[str] = []
    questions: List[str] = []
    notes: Optional[str] = ""
    status: str = "pending"

class RoadmapResponse(BaseModel):
    id: int
    title: str
    target_role: str
    steps_json: List[Dict[str, Any]]
    progress_percentage: int
    created_at: datetime

    class Config:
        from_attributes = True

class PracticeQuestionEvalRequest(BaseModel):
    question: str
    user_answer: str

class PracticeQuestionEvalResponse(BaseModel):
    score: float
    feedback: str
    passed: bool
    generated_new_question: Optional[str] = None
    step_questions: List[str]

