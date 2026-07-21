from agents.granite_client import GraniteClient
from rag.retriever import retrieve


class NotesAgent:
    def __init__(self):
        self.client = GraniteClient()

    def generate_notes(self, topic: str):
        context = "\n\n".join(retrieve(topic, k=3))

        prompt = f"""
You are a computer science tutor.

Topic:
{topic}

Reference material:
{context}

Write detailed study notes.

Include:
- Definition
- Explanation
- Key Points
- Examples
- Interview Tips

Do not use JSON.
"""

        notes = self.client.generate(prompt)

        return {
            "topic": topic,
            "title": f"{topic} Notes",
            "content": notes,
            "note_type": "detailed_note",
            "category": "AI Generated",
            "is_bookmarked": False,
        }