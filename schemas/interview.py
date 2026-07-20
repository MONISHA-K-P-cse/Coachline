from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime

class InterviewSessionCreate(BaseModel):
    role: str

class QuestionAnswerResponse(BaseModel):
    id: int
    turn_number: int
    question: str
    user_answer: Optional[str] = None
    score: float
    feedback: Optional[str] = None
    weak_topics: Optional[List[str]] = None

    class Config:
        from_attributes = True

class InterviewSessionResponse(BaseModel):
    id: int
    role: str
    status: str
    average_score: float
    started_at: datetime
    ended_at: Optional[datetime] = None
    qa_pairs: List[QuestionAnswerResponse] = []

    class Config:
        from_attributes = True

class WebSocketMessage(BaseModel):
    event: str  # "start", "answer", "end"
    session_id: Optional[int] = None
    role: Optional[str] = None
    user_answer: Optional[str] = None
