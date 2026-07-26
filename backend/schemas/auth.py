from pydantic import BaseModel, EmailStr
from typing import Optional, Literal
from datetime import datetime

LearningStyle = Literal["visual", "reading_writing", "kinesthetic"]

class UserCreate(BaseModel):
    email: EmailStr
    password: str
    full_name: Optional[str] = None
    target_role: Optional[str] = None
    target_company: Optional[str] = None
    experience_level: Optional[str] = None
    interview_date: Optional[datetime] = None
    learning_style: Optional[LearningStyle] = None

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"

class ProfileResponse(BaseModel):
    target_role: Optional[str] = None
    target_company: Optional[str] = None
    experience_level: Optional[str] = None
    interview_date: Optional[datetime] = None
    bio: Optional[str] = None
    learning_style: Optional[str] = None

    class Config:
        from_attributes = True

class ProfileUpdate(BaseModel):
    target_role: Optional[str] = None
    target_company: Optional[str] = None
    experience_level: Optional[str] = None
    interview_date: Optional[datetime] = None
    bio: Optional[str] = None
    learning_style: Optional[LearningStyle] = None

class UserResponse(BaseModel):
    id: int
    email: EmailStr
    full_name: Optional[str] = None
    created_at: datetime
    profile: Optional[ProfileResponse] = None

    class Config:
        from_attributes = True
