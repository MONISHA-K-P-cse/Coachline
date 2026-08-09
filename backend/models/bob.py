from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, JSON, Boolean
from sqlalchemy.orm import relationship
from datetime import datetime
from backend.core.database import Base

class BobChallengeResult(Base):
    __tablename__ = "bob_challenge_results"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    challenge_id = Column(String, nullable=False)
    score = Column(Integer, default=0)
    submitted_code = Column(Text, nullable=True)
    vulnerabilities_json = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="bob_results")

class BobCoachSession(Base):
    __tablename__ = "bob_coach_sessions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    target_role = Column(String, nullable=False)
    topic = Column(String, nullable=False)
    difficulty = Column(String, nullable=False, default="medium")
    conversation_json = Column(JSON, nullable=False, default=list)
    evaluation_json = Column(JSON, nullable=True)
    overall_score = Column(Integer, nullable=True)
    completed = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="bob_coach_sessions")
