from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime

class JobDescriptionCreate(BaseModel):
    target_role: str
    company_name: Optional[str] = None
    jd_text: str

class JobDescriptionResponse(BaseModel):
    id: int
    target_role: str
    company_name: Optional[str] = None
    skill_gaps: Optional[List[Dict[str, Any]]] = None
    uploaded_at: datetime

    class Config:
        from_attributes = True
