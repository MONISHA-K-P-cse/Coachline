from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, JSON, Float
from sqlalchemy.orm import relationship
from datetime import datetime
from core.database import Base

class InterviewSession(Base):
    __tablename__ = "interview_sessions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    role = Column(String, nullable=False)
    status = Column(String, default="active")  # active, completed
    average_score = Column(Float, default=0.0)
    technical_score = Column(Float, default=88.0)
    communication_score = Column(Float, default=79.0)
    behavioral_score = Column(Float, default=79.0)
    confidence_score = Column(Float, default=74.0)
    star_score = Column(Float, default=80.0)
    started_at = Column(DateTime, default=datetime.utcnow)
    ended_at = Column(DateTime, nullable=True)

    user = relationship("User", back_populates="interviews")
    qa_pairs = relationship("QuestionAnswer", back_populates="session", cascade="all, delete-orphan")


class QuestionAnswer(Base):
    __tablename__ = "questions_answers"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("interview_sessions.id"), nullable=False)
    turn_number = Column(Integer, nullable=False)
    question = Column(Text, nullable=False)
    user_answer = Column(Text, nullable=True)
    score = Column(Float, default=0.0)
    technical_score = Column(Float, default=0.0)
    communication_score = Column(Float, default=0.0)
    behavioral_score = Column(Float, default=0.0)
    confidence_score = Column(Float, default=0.0)
    star_score = Column(Float, default=0.0)
    feedback = Column(Text, nullable=True)
    weak_topics = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    session = relationship("InterviewSession", back_populates="qa_pairs")
