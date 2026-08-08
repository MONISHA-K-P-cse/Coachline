import os
from ai.agents.granite_client import GraniteClient

class BobAgent:
    def __init__(self):
        self.client = GraniteClient()

    def audit_code(self, code: str, challenge_id: str) -> dict:
        prompt = f"""
You are IBM Bob, an AI-powered development agent.
Perform a strict code audit and vulnerability check.

Challenge ID:
{challenge_id}

Candidate Code:
{code}

Respond with STRICT JSON containing:
- plan: List of strings (your multi-step implementation plan)
- vulnerabilities: List of objects (with severity, line, issue, fix)
- refactored_code: String (the safe corrected code)
- score: Number (0-100 score of candidate code)
"""
        response = self.client.generate(prompt)
        import json
        try:
            return json.loads(response)
        except Exception:
            # Fallback to defaults
            return {
                "plan": ["Analyze codebase structures."],
                "vulnerabilities": [{"severity": "Low", "line": 1, "issue": "Syntax check", "fix": "N/A"}],
                "refactored_code": code,
                "score": 50
            }
