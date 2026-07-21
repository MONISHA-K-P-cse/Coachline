import json

from granite_client import GraniteClient


class ResumeAgent:
    def __init__(self):
        self.client = GraniteClient()

    def analyze_resume(self, resume_text: str):
        prompt = f"""
You are an expert ATS Resume Reviewer.

Analyze the following resume and return ONLY valid JSON.

The JSON must exactly match this format:

{{
    "score": 0,
    "ats_score": 0,
    "keyword_count": 0,
    "summary": "",
    "resume_feedback": "",
    "strengths": [],
    "improvements": [],
    "fallback_used": false
}}

Scoring Guidelines:
- Score should be between 0 and 100.
- ATS score should be between 0 and 100.
- Count important technical keywords.
- Write a short professional summary.
- Give detailed resume feedback.
- List 3-5 strengths.
- List 3-5 improvements.
- Set fallback_used to false.

Resume:
{resume_text}
"""

        response = self.client.generate(prompt)

        return json.loads(response)  