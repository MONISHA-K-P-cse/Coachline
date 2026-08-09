from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime

class InterviewSessionCreate(BaseModel):
    role: str

class ScoreBreakdown(BaseModel):
    technical_score: float
    communication_score: float
    behavioral_score: float
    confidence_score: float
    star_score: float

class EvalAgentResult(ScoreBreakdown):
    overall_score: float
    feedback: str
    weak_topics: List[str] = []
    strong_topics: List[str] = []
    remedial_explanation: Optional[str] = ""
    fallback_used: bool = False

class QuestionAnswerResponse(BaseModel):
    id: int
    turn_number: int
    question: str
    user_answer: Optional[str] = None
    score: float
    technical_score: float
    communication_score: float
    behavioral_score: float
    confidence_score: float
    star_score: float
    feedback: Optional[str] = None
    weak_topics: Optional[List[str]] = None

    class Config:
        from_attributes = True

class InterviewSessionResponse(BaseModel):
    id: int
    role: str
    status: str
    average_score: float
    technical_score: float
    communication_score: float
    behavioral_score: float
    confidence_score: float
    star_score: float
    started_at: datetime
    ended_at: Optional[datetime] = None
    qa_pairs: List[QuestionAnswerResponse] = []

    class Config:
        from_attributes = True

class WebSocketMessage(BaseModel):
    event: str
    session_id: Optional[int] = None
    role: Optional[str] = None
    user_answer: Optional[str] = None

class ReplayDiffAttempt(BaseModel):
    session_id: int
    turn_number: int
    question: str
    user_answer: Optional[str] = None
    score: float
    feedback: Optional[str] = None
    created_at: datetime

class ReplayDiffResponse(BaseModel):
    topic: str
    attempt_count: int
    earliest: ReplayDiffAttempt
    latest: ReplayDiffAttempt
    score_delta: Optional[float] = None
