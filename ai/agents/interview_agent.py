import logging

from pydantic import ValidationError

from ai.agents.granite_client import GraniteClient
from ai.agents.llm_json import extract_json
from ai.rag.retriever import retrieve
from backend.schemas.interview import EvalAgentResult

logger = logging.getLogger("interview_agent")

# Same threshold interview.py uses to decide devil's-advocate mode - kept
# here too since the combined call now makes that decision internally.
DEVILS_ADVOCATE_SCORE_THRESHOLD = 80.0

# Baseline difficulty tier implied by the candidate's self-reported
# experience level, independent of how they've scored so far this session.
_LEVEL_RANK = {
    "entry": 0,
    "junior": 0,
    "intermediate": 1,
    "senior": 2,
    "staff+": 2,
}
_DIFFICULTY_NAMES = ["Beginner", "Medium", "Hard"]


def _score_rank(previous_score: float) -> int:
    if previous_score >= 80:
        return 2
    if previous_score >= 60:
        return 1
    return 0


class InterviewAgent:
    def __init__(self):
        self.client = GraniteClient()

    def generate_question(
        self,
        role: str,
        previous_score: float = 0,
        experience_level: str = "",
        candidate_background: str = "",
        is_opening_question: bool = False,
    ):
        context = "\n\n".join(
            retrieve(role, k=3)
        )

        # Blend the candidate's stated experience level with how they've
        # actually scored so far, so a self-described Senior candidate
        # starts harder than a self-described Entry-level one even before
        # either has scored anything, and both still adapt from there.
        level_rank = _LEVEL_RANK.get(experience_level.lower().strip(), 1)
        combined_rank = round((level_rank + _score_rank(previous_score)) / 2)
        difficulty = _DIFFICULTY_NAMES[combined_rank]

        opening_instructions = (
            """This is the FIRST question of the interview. Open with a brief,
warm one-sentence welcome that names the role, then ask the candidate to
introduce themselves and their relevant experience - but frame that
introduction prompt around the role and (if given) the candidate's actual
background below, not a generic unrelated topic like REST APIs or database
design unless that genuinely IS the role's subject matter."""
            if is_opening_question
            else "Generate ONE interview question that follows on from the interview so far."
        )

        prompt = f"""
You are an expert technical interviewer.

Role:
{role}
{f"Candidate Experience Level: {experience_level}" if experience_level else ""}
{f"Candidate Background (from their resume):\n{candidate_background}" if candidate_background else ""}

Difficulty:
{difficulty}

Reference Material (may be about an unrelated subject area - ONLY use it if
it genuinely matches the Role above; otherwise ignore it completely and
rely on your own knowledge of the Role instead):
{context}

Calibrate the question's depth and phrasing to the candidate's experience
level above (if given) as well as the target difficulty: a Beginner-tier
question for an entry-level candidate should ask about a single core
concept in plain terms, while a Hard-tier question for a senior candidate
should probe trade-offs, scale, or failure modes. The question's SUBJECT
MATTER must be genuinely specific to the Role above - do not default to
generic CS topics (REST APIs, databases, operating systems, memory
management, etc.) unless the role above is actually about that subject.

{opening_instructions}

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

    def evaluate_and_generate_next(
        self,
        role: str,
        question: str,
        answer: str,
        experience_level: str = "",
        candidate_background: str = "",
    ):
        """
        Scores the candidate's answer AND produces the next question in a
        SINGLE Granite call, instead of two sequential round-trips (eval,
        then next-question generation). On CPU-only inference each call can
        take 15-100s+, so halving the number of calls per turn roughly
        halves the "evaluating..." wait. Falls back to the two-call path
        (see interview.py) if this combined call's output can't be parsed.
        """
        context = "\n\n".join(retrieve(role, k=3))

        prompt = f"""
You are an expert technical interviewer conducting a live mock interview.

Role:
{role}
{f"Candidate Experience Level: {experience_level}" if experience_level else ""}
{f"Candidate Background (from their resume):\n{candidate_background}" if candidate_background else ""}

Reference Material (may be about an unrelated subject area - ONLY use it if
it genuinely matches the Role above; otherwise ignore it completely and
rely on your own knowledge of the Role instead):
{context}

The candidate was just asked:
{question}

The candidate answered:
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
  "weak_topics": [<string>, ...],
  "mode": "standard" or "devils_advocate",
  "next_question": <string, the next interview question - see rules below>
}}

Base every score strictly on the substance, correctness and depth of the
candidate answer above. A vague, incorrect or incomplete answer must score
noticeably lower than a precise, well-reasoned one. "weak_topics" MUST be
derived only from actual gaps in the candidate's answer above - never from
the Reference Material or any unrelated subject area - and should be an
empty list if there are none.

Rules for "next_question" and "mode":
- If overall_score is 80 or above, set "mode" to "devils_advocate" and make
  "next_question" push back on the candidate's OWN answer above: identify a
  specific edge case, trade-off, or weak point in what THEY actually said,
  and challenge them to defend or refine it. It must reference specifics
  from their real answer, not a generic follow-up.
- Otherwise, set "mode" to "standard" and make "next_question" a genuinely
  new question. Its SUBJECT MATTER must be specific to the Role above (do
  not default to generic CS topics like REST APIs, databases, operating
  systems, or memory management unless the role above is actually about
  that subject). Calibrate its difficulty to the candidate's experience
  level (if given) blended with the overall_score you just gave this
  answer: entry-level or a low score should get an easier, single-concept
  question; senior-level or a high score should get a harder question
  probing trade-offs, scale, or failure modes.
"""

        raw = self.client.generate(prompt)
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
        ).model_dump()

        next_question = str(data["next_question"]).strip()
        if not next_question:
            raise ValueError("Combined call returned an empty next_question")

        mode = data.get("mode") if data.get("mode") in ("standard", "devils_advocate") else (
            "devils_advocate" if result["overall_score"] >= DEVILS_ADVOCATE_SCORE_THRESHOLD else "standard"
        )

        return result, {
            "role": role,
            "difficulty": "Devil's Advocate" if mode == "devils_advocate" else None,
            "question": next_question,
            "mode": mode,
        }