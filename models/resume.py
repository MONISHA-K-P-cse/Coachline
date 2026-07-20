from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, JSON
from sqlalchemy.orm import relationship
from datetime import datetime
from core.database import Base

class Resume(Base):
    __tablename__ = "resumes"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    filename = Column(String, nullable=False)
    parsed_text = Column(Text, nullable=True)
    score = Column(Integer, default=0)
    ats_score = Column(Integer, default=0)
    keyword_count = Column(Integer, default=44)
    resume_feedback = Column(Text, nullable=True)
    score_details = Column(JSON, nullable=True)
    uploaded_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="resumes")
