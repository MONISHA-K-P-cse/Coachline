import logging
from ai.agents.granite_client import GraniteClient
from ai.agents.llm_json import extract_json

logger = logging.getLogger("jd_agent")

class JobDescriptionAgent:
    def __init__(self, client=None):
        self.client = client or GraniteClient()

    def analyze_jd(self, target_role: str, company_name: str, jd_text: str) -> dict:
        prompt = self._build_prompt(target_role, company_name, jd_text)
        raw = self.client.generate(prompt)

        try:
            data = extract_json(raw)
            # Basic validation
            if "skill_gaps" not in data:
                raise ValueError("Missing 'skill_gaps' in JD agent JSON response")
            return {
                "skill_gaps": data["skill_gaps"],
                "matched_skills": data.get("matched_skills", [])
            }
        except Exception as exc:
            logger.warning("JD agent JSON parse/validation failed: %s. Using default fallback gaps.", exc)
            return {
                "skill_gaps": [
                    {
                        "category": "Must-Have Technical Skills",
                        "missing_skills": ["System Design", "Distributed Systems", "Cloud Deployment"],
                        "priority": "High"
                    }
                ],
                "matched_skills": []
            }

    @staticmethod
    def _build_prompt(target_role: str, company_name: str, jd_text: str) -> str:
        return f"""You are an expert Job Description (JD) Analyzer.

Analyze the job description text below for the role of '{target_role}' at '{company_name}'. Identify key skill gaps that a typical candidate might lack based on standard industry expectations for this role, and identify skills they might already have if they meet the basic qualifications.

Respond with STRICT JSON ONLY. No prose, no markdown code fences, no commentary before or after the JSON object.

The JSON object MUST match exactly this schema:
{{
  "skill_gaps": [
    {{
      "category": "<string, category of skills>",
      "missing_skills": ["<string, specific skill>", ...],
      "priority": "<string: High, Medium, or Low>"
    }},
    ...
  ],
  "matched_skills": ["<string>", ...]
}}

Job Description:
{jd_text}
"""
