from ai.agents.granite_client import GraniteClient
from ai.rag.retriever import retrieve


class MentorAgent:
    def __init__(self, client=None):
        self.client = client or GraniteClient()

    def chat(self, message: str, target_role: str = "") -> str:
        context = "\n\n".join(retrieve(message, k=3))

        prompt = f"""You are an encouraging, knowledgeable career mentor for a
candidate preparing for a {target_role or "technical"} interview.

Reference material (may or may not be relevant to this message):
{context}

Candidate message:
{message}

Reply directly to the candidate in 2-4 sentences. Be specific and
actionable rather than generic. Do not repeat the candidate's message
back to them.
"""
        return self.client.generate(prompt).strip()
