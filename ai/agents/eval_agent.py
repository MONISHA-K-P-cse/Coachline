import logging

from pydantic import ValidationError

from ai.agents.granite_client import GraniteClient
from ai.agents.llm_json import extract_json
from backend.schemas.interview import EvalAgentResult

logger = logging.getLogger("eval_agent")

FALLBACK_FEEDBACK = (
    "The AI interviewer could not produce a structured evaluation for this answer. "
    "Please retry the evaluation."
)


class EvaluationAgent:
    def __init__(self, client=None):
        self.client = client or GraniteClient()

    def evaluate_answer(self, question: str, answer: str):
        prompt = self._build_prompt(question, answer)
        raw = self.client.generate(prompt)

        try:
            data = extract_json(raw)
            result = EvalAgentResult(
                technical_score=float(data["technical_score"]),
                communication_score=float(data["communication_score"]),
                behavioral_score=float(data["behavioral_score"]),
                confidence_score=float(data["confidence_score"]),
                star_score=float(data["star_score"]),
                overall_score=float(data["overall_score"]),
                feedback=str(data["feedback"]),
                weak_topics=[str(t) for t in data.get("weak_topics", [])],
                fallback_used=False,
            )
        except (ValueError, KeyError, TypeError, ValidationError) as exc:
            logger.warning("Eval agent JSON parse/validation failed, using fallback score: %s", exc)
            result = EvalAgentResult(
                technical_score=50.0,
                communication_score=50.0,
                behavioral_score=50.0,
                confidence_score=50.0,
                star_score=50.0,
                overall_score=50.0,
                feedback=FALLBACK_FEEDBACK,
                weak_topics=[],
                fallback_used=True,
            )

        return result.model_dump()

    @staticmethod
    def _build_prompt(question: str, answer: str) -> str:
        return f"""You are an expert technical interviewer.

Question:
{question}

Candidate Answer:
{answer}

Respond with STRICT JSON ONLY. No prose, no markdown code fences, no
commentary before or after the JSON object.

The JSON object MUST match exactly this schema:
{{
  "technical_score": <number 0-100>,
  "communication_score": <number 0-100>,
  "behavioral_score": <number 0-100>,
  "confidence_score": <number 0-100>,
  "star_score": <number 0-100>,
  "overall_score": <number 0-100, weighted overall impression>,
  "feedback": <string, strengths and weaknesses of the answer>,
  "weak_topics": [<string>, ...]
}}

"weak_topics" should list specific sub-topics the candidate should review
based on gaps in the answer, or be an empty list if there are none.

Base every score strictly on the substance, correctness and depth of the
candidate answer above. A vague, incorrect or incomplete answer must score
noticeably lower than a precise, well-reasoned one. Do not default to a
fixed score regardless of content.
"""
