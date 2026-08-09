from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, JSON
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
