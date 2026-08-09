from pydantic import BaseModel
from typing import List, Dict, Any, Optional

class BobCoachStartRequest(BaseModel):
    target_role: Optional[str] = None

class BobCoachRespondRequest(BaseModel):
    session_id: int
    candidate_response: str

class BobCoachTurn(BaseModel):
    sender: str
    text: str

class BobCoachEvaluationDetails(BaseModel):
    technical_understanding: int
    problem_solving: int
    architecture: int
    tradeoffs: int
    scalability: int
    performance: int
    cost_awareness: int
    communication: int
    decision_justification: int
    overall: int

class BobCoachStartResponse(BaseModel):
    session_id: int
    next_question: str
    difficulty: str
    topic: str
    reasoning_focus: str

class BobCoachRespondResponse(BaseModel):
    next_question: str
    difficulty: str
    topic: str
    reasoning_focus: str
    completed: bool

class BobCoachEvaluationResponse(BaseModel):
    evaluation: BobCoachEvaluationDetails
    strengths: List[str]
    weaknesses: List[str]
    key_mistakes: Optional[List[str]] = None
    better_approach: Optional[str] = None
    concepts_to_revise: List[str]
    recommendations: List[str]
