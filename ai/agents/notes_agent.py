import logging

from pydantic import ValidationError

from ai.agents.granite_client import GraniteClient
from ai.agents.llm_json import extract_json
from ai.rag.retriever import retrieve
from backend.schemas.roadmap import NoteBlock

logger = logging.getLogger("notes_agent")

VALID_LEARNING_STYLES = {"visual", "reading_writing", "kinesthetic"}
DEFAULT_LEARNING_STYLE = "reading_writing"

STYLE_INSTRUCTIONS = {
    "visual": """The learner is a VISUAL learner. Lean on diagrams and visual
comparisons rather than dense prose:
- Keep any plain explanatory text blocks short.
- Include at least one "diagram" block containing a Mermaid diagram
  (flowchart, sequence, or graph) that visualizes the concept, its steps,
  or how it relates to nearby concepts.
- Include at least one "text" block containing a markdown comparison table
  contrasting the topic with a related concept or laying out trade-offs.""",
    "reading_writing": """The learner is a READING/WRITING learner. Structure the
notes as dense, well-organized outline-style prose:
- Use nested markdown bullet points and headings.
- Prefer precise written definitions and thorough written explanations.
- Every block should be of type "text" - do not use diagram or exercise
  blocks for this style.""",
    "kinesthetic": """The learner is a KINESTHETIC learner. Structure the notes
around doing rather than reading:
- Keep any plain explanatory text blocks brief.
- Interleave at least two "exercise" blocks, each a worked example or
  hands-on practice problem with its solution/walkthrough, so the learner
  can work through it step by step.""",
}

FALLBACK_TEXT_TEMPLATE = (
    "Study notes for {topic} could not be generated automatically. "
    "Please retry the note generation."
)


class NotesAgent:
    def __init__(self, client=None):
        self.client = client or GraniteClient()

    def generate_notes(self, topic: str, learning_style: str = DEFAULT_LEARNING_STYLE):
        style = learning_style if learning_style in VALID_LEARNING_STYLES else DEFAULT_LEARNING_STYLE
        context = "\n\n".join(retrieve(topic, k=3))

        prompt = self._build_prompt(topic, context, style)
        raw = self.client.generate(prompt)

        try:
            data = extract_json(raw)
            blocks = self._validate_blocks(data.get("blocks", []))
            if not blocks:
                raise ValueError("LLM returned zero blocks")
        except (ValueError, KeyError, TypeError, ValidationError) as exc:
            logger.warning(
                "Notes agent JSON parse/validation failed for topic '%s' (%s); using fallback block",
                topic,
                exc,
            )
            blocks = [{"type": "text", "content": FALLBACK_TEXT_TEMPLATE.format(topic=topic)}]

        return {
            "topic": topic,
            "title": f"{topic} Notes",
            "learning_style": style,
            "blocks": blocks,
            "note_type": "detailed_note",
            "category": "AI Generated",
            "is_bookmarked": False,
        }

    @staticmethod
    def _validate_blocks(raw_blocks):
        validated = []
        for block in raw_blocks:
            note_block = NoteBlock(type=block["type"], content=str(block["content"]))
            validated.append(note_block.model_dump())
        return validated

    @staticmethod
    def _build_prompt(topic: str, context: str, style: str) -> str:
        style_instructions = STYLE_INSTRUCTIONS[style]

        return f"""You are a computer science tutor personalizing study notes to a
learner's VARK learning style.

Topic:
{topic}

Reference material:
{context}

{style_instructions}

Respond with STRICT JSON ONLY. No prose, no commentary before or after the
JSON object (fenced code is only allowed *inside* a block's "content" string).

The JSON object MUST match exactly this schema:
{{
  "blocks": [
    {{"type": "text" | "diagram" | "exercise", "content": <string>}},
    ...
  ]
}}

Rules for "content" by block type:
- "text": a markdown-formatted definition, explanation, key points list, or
  comparison table.
- "diagram": a fenced Mermaid code block, e.g. "```mermaid\\ngraph TD\\nA-->B\\n```".
- "exercise": a worked example or practice problem, including its solution.

Produce at least 3 blocks and at most 6, covering: definition, explanation,
key points/examples, and interview tips - distributed across blocks in the
format dictated by the learning style above.
"""
