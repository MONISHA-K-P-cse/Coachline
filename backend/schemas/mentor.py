from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class MentorMessageCreate(BaseModel):
    message: str

class MentorMessageResponse(BaseModel):
    id: int
    sender: str
    message: str
    created_at: datetime

    class Config:
        from_attributes = True
