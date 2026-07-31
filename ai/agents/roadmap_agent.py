import logging

from ai.agents.granite_client import GraniteClient
from ai.agents.llm_json import extract_json
from ai.rag.retriever import retrieve

logger = logging.getLogger("roadmap_agent")


class RoadmapAgent:
    def __init__(self):
        self.client = GraniteClient()

    def generate_roadmap(
        self,
        target_role: str,
        current_skills: str,
        target_company: str = "",
        experience_level: str = "",
        weeks: int = 8,
    ):
        context = "\n\n".join(retrieve(target_role, k=3))

        profile_lines = [f"Target Role:\n{target_role}"]
        if target_company:
            profile_lines.append(f"Target Company:\n{target_company}")
        if experience_level:
            profile_lines.append(f"Candidate Experience Level:\n{experience_level}")
        profile_block = "\n\n".join(profile_lines)

        prompt = f"""
You are an expert software mentor.

{profile_block}

Current Skills:
{current_skills}

Reference Material (may not be directly relevant to the Target Role - only
use it if it actually applies; otherwise rely on your own knowledge of the
Target Role):
{context}

Create an {weeks}-week learning roadmap tailored to the candidate's stated
experience level and, if given, the hiring focus of the target company:
- Every week's topic MUST be genuinely specific to the Target Role above -
  do not default to generic backend/web/OS/DBMS fundamentals unless the
  Target Role is actually that kind of role.
- An Entry/Junior candidate should spend more weeks on fundamentals before
  advanced topics.
- A Senior/Staff candidate should skip basics entirely and spend most weeks
  on advanced system design, scale, and leadership/architecture topics.
- If a target company is given, weight topics toward what that company is
  known to emphasize in interviews (e.g. a company known for heavy system
  design interviews should get more system design weeks).

Respond with STRICT JSON ONLY. No prose, no markdown code fences, no
commentary before or after the JSON object.

The JSON object MUST match exactly this schema:
{{
  "steps": [
    {{"title": <string>, "description": <string, 1-3 sentences>, "estimated_hours": <integer>}},
    ...
  ]
}}

Produce exactly {weeks} entries in "steps", one per week, in week order.
"""

        raw = self.client.generate(prompt)
        return self._convert_to_schema(raw, target_role, weeks)

    def _convert_to_schema(self, raw: str, target_role: str, weeks: int):
        try:
            data = extract_json(raw)
            raw_steps = data["steps"]
            if not raw_steps:
                raise ValueError("LLM returned zero roadmap steps")
            steps = [
                {
                    "step_number": i + 1,
                    "title": str(s["title"]).strip(),
                    "description": str(s["description"]).strip(),
                    "estimated_hours": int(s.get("estimated_hours", 20)),
                    "status": "pending",
                }
                for i, s in enumerate(raw_steps)
            ]
        except (ValueError, KeyError, TypeError) as exc:
            logger.warning(
                "Roadmap agent JSON parse/validation failed for role '%s' (%s); using fallback single step",
                target_role,
                exc,
            )
            steps = [
                {
                    "step_number": 1,
                    "title": f"{target_role} Roadmap Generation Failed",
                    "description": "The AI roadmap generator could not produce a structured roadmap. Please retry.",
                    "estimated_hours": 0,
                    "status": "pending",
                }
            ]

        return {
            "title": f"{target_role} Roadmap",
            "target_role": target_role,
            "steps_json": steps,
            "progress_percentage": 0,
        }