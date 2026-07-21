from agents.granite_client import GraniteClient


class EvaluationAgent:
    def __init__(self):
        self.client = GraniteClient()

    def evaluate_answer(
        self,
        question: str,
        answer: str,
    ):
        prompt = f"""
You are an expert technical interviewer.

Question:
{question}

Candidate Answer:
{answer}

Evaluate the answer.

Provide:

1. Technical Score (0-100)
2. Communication Score (0-100)
3. Behavioral Score (0-100)
4. Confidence Score (0-100)
5. STAR Score (0-100)

Then explain the strengths and weaknesses.

Do NOT use JSON.
"""

        feedback = self.client.generate(prompt)

        return {
            "technical_score": 80,
            "communication_score": 85,
            "behavioral_score": 78,
            "confidence_score": 82,
            "star_score": 75,
            "overall_score": 80,
            "feedback": feedback,
        }