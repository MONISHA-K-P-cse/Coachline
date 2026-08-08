import logging

from pydantic import ValidationError

from ai.agents.granite_client import GraniteClient
from ai.agents.llm_json import extract_json
from backend.schemas.resume import ResumeScore, RewriteSuggestion

logger = logging.getLogger("resume_agent")

FALLBACK_FEEDBACK = (
    "The AI reviewer could not produce a structured evaluation for this resume. "
    "Please retry the analysis."
)


class ResumeAgent:
    def __init__(self, client=None):
        self.client = client or GraniteClient()

    def analyze_resume(self, resume_text: str):
        prompt = self._build_prompt(resume_text)
        raw = self.client.generate(prompt)
        keyword_count = len(resume_text.split())

        try:
            data = extract_json(raw)
            rewrite_suggestions = [
                RewriteSuggestion(
                    original=str(s["original"]),
                    rewritten=str(s["rewritten"]),
                    reason=str(s["reason"]),
                )
                for s in data.get("rewrite_suggestions", [])
                if isinstance(s, dict) and "original" in s and "rewritten" in s and "reason" in s
            ]
            result = ResumeScore(
                score=int(data["score"]),
                ats_score=int(data["ats_score"]),
                keyword_count=keyword_count,
                summary=str(data["summary"]),
                resume_feedback=str(data["resume_feedback"]),
                strengths=[str(s) for s in data.get("strengths", [])],
                improvements=[str(s) for s in data.get("improvements", [])],
                rewrite_suggestions=rewrite_suggestions,
                fallback_used=False,
            )
        except (ValueError, KeyError, TypeError, ValidationError) as exc:
            logger.warning("Resume agent JSON parse/validation failed, using fallback score: %s", exc)
            result = ResumeScore(
                score=50,
                ats_score=50,
                keyword_count=keyword_count,
                summary="Unable to fully analyze this resume automatically.",
                resume_feedback=FALLBACK_FEEDBACK,
                strengths=[],
                improvements=["Retry the analysis - the AI reviewer output could not be parsed."],
                rewrite_suggestions=[],
                fallback_used=True,
            )

        return result.model_dump()

    def improve_resume(self, resume_text: str, improvements: list) -> dict:
        prompt = f"""You are an expert ATS Resume Optimizer.

Given the candidate's resume below and a list of improvements needed:
Improvements to address:
{chr(10).join(['- ' + imp for imp in improvements])}

Rewrite the resume text to address these improvements. For example, quantify results with metrics (e.g. percentages or counts), use active technical verbs, and highlight specific frameworks/clouds clearly. Crucially, you MUST maintain the exact same formatting, section headers, spacing, indentation, line breaks, and overall layout structure of the original resume. Only optimize the specific bullet points that need improvements; do not restructure or delete other parts of the document.

Then, list the key changes you made.

Respond with STRICT JSON ONLY. No prose, no markdown code fences, no commentary before or after the JSON object.

The JSON object MUST match exactly this schema:
{{
  "improved_text": "<string, the fully rewritten and improved resume text>",
  "changes_made": ["<string, description of a change made>", ...]
}}

Resume:
{resume_text}
"""
        raw = self.client.generate(prompt)
        try:
            data = extract_json(raw)
            return {
                "improved_text": str(data["improved_text"]),
                "changes_made": [str(c) for c in data.get("changes_made", [])]
            }
        except Exception as exc:
            logger.warning("Resume improvement JSON parse/validation failed: %s. Using default fallback.", exc)
            return {
                "improved_text": resume_text + "\n\n[Optimizer Note: Try to quantify your results with metrics (e.g., 'Improved load times by 40%') and explicitly specify cloud technologies used.]",
                "changes_made": [
                    "Suggested adding concrete percentage metrics for business impact",
                    "Suggested specifying exact cloud services deployed"
                ]
            }

    @staticmethod
    def _build_prompt(resume_text: str) -> str:
        return f"""You are an expert ATS Resume Reviewer.

Analyze the resume below and respond with STRICT JSON ONLY. No prose, no
markdown code fences, no commentary before or after the JSON object.

The JSON object MUST match exactly this schema:
{{
  "score": <integer 0-100, overall resume quality>,
  "ats_score": <integer 0-100, ATS keyword/formatting compatibility>,
  "summary": <string, 1-2 sentence professional summary of the candidate>,
  "resume_feedback": <string, detailed feedback paragraph>,
  "strengths": [<string>, ...],
  "improvements": [<string>, ...],
  "rewrite_suggestions": [
    {{"original": <string>, "rewritten": <string>, "reason": <string>}},
    ...
  ]
}}

Base every score strictly on the actual content of the resume below. A
resume with vague, unquantified, sparse content must score noticeably
lower than one with strong, specific, quantified achievements. Do not
default to a fixed score regardless of content.

For "rewrite_suggestions": pick 2-4 of the weakest bullets or sentences you
can actually find in the resume text below, and for each one return:
- "original": the exact original text, copied verbatim from the resume
  below (not paraphrased).
- "rewritten": a concrete, specific rewritten version of that SAME bullet
  that fixes its specific weakness - e.g. adding a real metric implied by
  context, naming a concrete technology instead of a vague term, or
  replacing a weak verb ("worked on", "helped with") with a strong action
  verb ("led", "built", "reduced"). Do not invent facts not implied by the
  original; sharpen phrasing and structure instead.
- "reason": one short sentence naming the specific gap being fixed (e.g.
  "no quantified impact", "vague technology reference", "passive/weak verb").
Do NOT produce generic advice like "add metrics" as the rewritten text -
every suggestion must reference and rewrite real text from this resume. If
the resume has fewer than 2 bullets worth improving, return fewer entries;
never fabricate a bullet that isn't in the resume below.

Resume:
{resume_text}
"""
