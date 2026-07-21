import re

from agents.granite_client import GraniteClient
from rag.retriever import retrieve


class RoadmapAgent:
    def __init__(self):
        self.client = GraniteClient()

    def generate_roadmap(
        self,
        target_role: str,
        current_skills: str,
        weeks: int = 8,
    ):
        context = "\n\n".join(retrieve(target_role, k=3))

        prompt = f"""
You are an expert software mentor.

Target Role:
{target_role}

Current Skills:
{current_skills}

Reference Material:
{context}

Create an {weeks}-week learning roadmap.

Do NOT use JSON.

Format exactly like this:

Week 1: Title
Description

Week 2: Title
Description

Continue until Week {weeks}.
"""

        response = self.client.generate(prompt)

        return self._convert_to_schema(
            response,
            target_role,
        )

    def _convert_to_schema(
        self,
        text: str,
        target_role: str,
    ):
        pattern = r"Week\s+(\d+)\s*:\s*(.+?)(?=\n)(.*?)(?=Week\s+\d+:|$)"

        matches = re.findall(
            pattern,
            text,
            flags=re.S | re.I,
        )

        steps = []

        for number, title, description in matches:
            steps.append(
                {
                    "step_number": int(number),
                    "title": title.strip(),
                    "description": " ".join(description.split()),
                    "estimated_hours": 20,
                    "status": "pending",
                }
            )

        return {
            "title": f"{target_role} Roadmap",
            "target_role": target_role,
            "steps_json": steps,
            "progress_percentage": 0,
        }