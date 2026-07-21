from agents.granite_client import GraniteClient
from rag.retriever import retrieve


class InterviewAgent:
    def __init__(self):
        self.client = GraniteClient()

    def generate_question(
        self,
        role: str,
        previous_score: float = 0,
    ):
        context = "\n\n".join(
            retrieve(role, k=3)
        )

        difficulty = "Beginner"

        if previous_score >= 80:
            difficulty = "Hard"
        elif previous_score >= 60:
            difficulty = "Medium"

        prompt = f"""
You are an expert technical interviewer.

Role:
{role}

Difficulty:
{difficulty}

Reference Material:
{context}

Generate ONE interview question.

Then provide:

Expected Answer:
Hints:

Do NOT use JSON.
"""

        response = self.client.generate(prompt)

        return {
            "role": role,
            "difficulty": difficulty,
            "question": response,
            "previous_score": previous_score,
        }