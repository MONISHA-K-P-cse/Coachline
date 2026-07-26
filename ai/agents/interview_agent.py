from ai.agents.granite_client import GraniteClient
from ai.rag.retriever import retrieve


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
            "mode": "standard",
        }

    def generate_devils_advocate_question(self, role: str, question: str, answer: str):
        """
        Follow-up question that challenges a strong answer, rather than
        moving on to an unrelated topic - triggered by the caller when the
        candidate's previous answer scored highly.
        """
        context = "\n\n".join(retrieve(role, k=3))

        prompt = f"""
You are an expert technical interviewer playing devil's advocate.

Role:
{role}

The candidate was just asked:
{question}

The candidate answered:
{answer}

Reference Material:
{context}

The candidate's answer was strong. Push back on it: identify a specific
edge case, trade-off, or weak point in THEIR answer above, and challenge
them to defend or refine it. The follow-up must reference specifics from
their actual answer - do not ask an unrelated question.

Then provide:

Expected Answer:
Hints:

Do NOT use JSON.
"""

        response = self.client.generate(prompt)

        return {
            "role": role,
            "difficulty": "Devil's Advocate",
            "question": response,
            "previous_score": None,
            "mode": "devils_advocate",
        }