from ai.agents.granite_client import GraniteClient
from ai.rag.retriever import retrieve


class MentorAgent:
    def __init__(self, client=None):
        self.client = client or GraniteClient()

    def chat(
        self,
        message: str,
        target_role: str = "",
        experience_level: str = "",
        resume_skills: str = "",
        weak_topics: list = None,
        strong_topics: list = None,
        roadmap_status: str = "",
        mastery_summary: str = "",
        bob_results_summary: str = ""
    ) -> str:
        context = "\n\n".join(retrieve(message, k=3))

        prompt = f"""You are CoachLine's Adaptive Engineering Coach and Career Mentor.
You are helping a candidate with the following profile:
- Target Role: {target_role or "Software Engineer"}
- Experience Level: {experience_level or "Junior"}
- Resume/Extracted Skills: {resume_skills or "N/A"}

CoachLine System Telemetry Context:
- Interview Weaknesses: {", ".join(weak_topics) if weak_topics else "None flagged yet"}
- Interview Strengths: {", ".join(strong_topics) if strong_topics else "None flagged yet"}
- Roadmap Progress: {roadmap_status or "Not started yet"}
- Mastery Competencies: {mastery_summary or "Baseline preparation"}
- IBM Bob Practice Challenges completed: {bob_results_summary or "No security audits submitted yet"}

Reference material (may or may not be relevant to this message):
{context}

Candidate message:
{message}

Provide personalized, specific, and actionable career guidance matching their exact strengths, weaknesses, and roadmap status.
Keep your response encouraging, concise (2-4 sentences max), and direct. Do NOT give generic advice.
"""
        return self.client.generate(prompt).strip()
