from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from typing import List, Dict, Any
from sqlalchemy.orm import Session

from backend.core.database import get_db
from backend.models.user import User
from backend.api.auth import get_current_user
from ai.agents.bob_agent import BobAgent

router = APIRouter(prefix="/bob", tags=["IBM Bob Developer Agent"])
bob_agent = BobAgent()

class CodeAuditRequest(BaseModel):
    code: str
    challenge_id: str
    language: str = "python"

class VulnerabilityItem(BaseModel):
    severity: str
    line: int
    issue: str
    fix: str

class CodeAuditResponse(BaseModel):
    plan: List[str]
    vulnerabilities: List[VulnerabilityItem]
    refactored_code: str
    score: int

@router.post("/audit", response_model=CodeAuditResponse)
async def run_code_audit(
    request: CodeAuditRequest,
    current_user: User = Depends(get_current_user),
):
    try:
        result = bob_agent.audit_code(request.code, request.challenge_id)
        return result
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"IBM Bob Code Audit failed: {str(e)}"
        )
