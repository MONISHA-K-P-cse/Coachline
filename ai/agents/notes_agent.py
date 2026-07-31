import logging

from pydantic import ValidationError

from ai.agents.granite_client import GraniteClient
from ai.agents.llm_json import extract_json
from ai.rag.retriever import retrieve
from backend.schemas.roadmap import NoteBlock

logger = logging.getLogger("notes_agent")

VALID_LEARNING_STYLES = {"visual", "reading_writing", "kinesthetic"}
DEFAULT_LEARNING_STYLE = "reading_writing"

# Only visual/kinesthetic learners need a second, non-text block appended -
# reading_writing notes are pure text and need only the core call below.
SUPPLEMENT_BLOCK_TYPE = {
    "visual": "diagram",
    "kinesthetic": "exercise",
}

FALLBACK_TEXT_TEMPLATE = (
    "Study notes for {topic} could not be generated automatically. "
    "Please retry the note generation."
)


class NotesAgent:
    def __init__(self, client=None):
        self.client = client or GraniteClient()

    def generate_notes(self, topic: str, learning_style: str = DEFAULT_LEARNING_STYLE, target_role: str = ""):
        style = learning_style if learning_style in VALID_LEARNING_STYLES else DEFAULT_LEARNING_STYLE
        context = "\n\n".join(retrieve(topic, k=3))

        blocks = self._generate_text_blocks(topic, context, target_role)
        if blocks is None:
            blocks = [{"type": "text", "content": FALLBACK_TEXT_TEMPLATE.format(topic=topic)}]

        supplement_type = SUPPLEMENT_BLOCK_TYPE.get(style)
        if supplement_type and blocks:
            supplement = self._generate_supplement_block(topic, context, target_role, supplement_type)
            if supplement:
                blocks.append(supplement)

        return {
            "topic": topic,
            "title": f"{topic} Notes",
            "learning_style": style,
            "blocks": blocks,
            "note_type": "detailed_note",
            "category": "AI Generated",
            "is_bookmarked": False,
        }

    def _generate_text_blocks(self, topic: str, context: str, target_role: str):
        """Core outline/definition content only - deliberately the smallest,
        simplest JSON shape we can ask for (a flat list of same-typed text
        blocks) so a small model has the best odds of returning valid,
        parseable structured output on the first try. Retries once with an
        even simpler single-block prompt before giving up; the generic
        placeholder is the last resort, not the second attempt.
        """
        raw = self.client.generate(self._build_text_prompt(topic, context, target_role, simplified=False))
        blocks = self._try_parse_blocks(raw)
        if blocks:
            return blocks

        logger.warning(
            "Notes agent text-block call failed to parse for topic '%s'; retrying with a simplified prompt",
            topic,
        )
        raw2 = self.client.generate(self._build_text_prompt(topic, context, target_role, simplified=True))
        blocks2 = self._try_parse_blocks(raw2)
        if blocks2:
            return blocks2

        logger.warning("Notes agent text-block retry also failed for topic '%s'; using fallback block", topic)
        return None

    def _generate_supplement_block(self, topic: str, context: str, target_role: str, block_type: str):
        """One additional diagram/exercise block, requested as its own tiny
        call so a parse failure here only costs the supplement, not the
        (already-succeeded) core text content."""
        raw = self.client.generate(self._build_supplement_prompt(topic, context, target_role, block_type))
        try:
            data = extract_json(raw)
            content = str(data["content"])
            block = NoteBlock(type=block_type, content=content).model_dump()
            return block
        except (ValueError, KeyError, TypeError, ValidationError) as exc:
            logger.warning(
                "Notes agent supplement call (%s) failed to parse for topic '%s' (%s); omitting supplement block",
                block_type,
                topic,
                exc,
            )
            return None

    # Below this, a "successful" parse is usually just a heading with no
    # actual body content (e.g. '# Binary Search Trees') - syntactically
    # valid JSON that is functionally as useless as a parse failure, so it
    # must trigger the same retry/fallback path rather than being accepted.
    MIN_CONTENT_CHARS = 80

    def _try_parse_blocks(self, raw: str):
        try:
            data = extract_json(raw)
            blocks = self._validate_blocks(data.get("blocks", []))
            if not blocks:
                return None
            total_len = sum(len(b["content"]) for b in blocks)
            if total_len < self.MIN_CONTENT_CHARS:
                return None
            return blocks
        except (ValueError, KeyError, TypeError, ValidationError):
            return None

    @staticmethod
    def _validate_blocks(raw_blocks):
        validated = []
        for block in raw_blocks:
            note_block = NoteBlock(type=block["type"], content=str(block["content"]))
            validated.append(note_block.model_dump())
        return validated

    @staticmethod
    def _build_text_prompt(topic: str, context: str, target_role: str, simplified: bool) -> str:
        role_instruction = (
            f"\nThe learner is preparing for a {target_role} role - choose examples and "
            f"terminology relevant to a {target_role} interview on this topic.\n"
            if target_role else ""
        )

        if simplified:
            return f"""Write study notes on "{topic}" as plain markdown text.
{role_instruction}
Respond with STRICT JSON ONLY, matching exactly this schema:
{{"blocks": [{{"type": "text", "content": <string>}}]}}

Return exactly ONE block containing a clear, well-organized markdown
explanation of {topic}: a definition, key points, and one interview tip.
No other JSON keys, no prose outside the JSON object.
"""

        return f"""You are a computer science tutor writing study notes.

Topic:
{topic}

Reference material:
{context}
{role_instruction}
Respond with STRICT JSON ONLY. No prose, no commentary before or after the
JSON object.

The JSON object MUST match exactly this schema:
{{
  "blocks": [
    {{"type": "text", "content": <string>}},
    ...
  ]
}}

Produce 2-4 "text" blocks in dense, well-organized markdown (headings,
bullet points), covering: definition, explanation, key points/examples, and
one interview tip. Every block must be type "text" - no other block types.
"""

    @staticmethod
    def _build_supplement_prompt(topic: str, context: str, target_role: str, block_type: str) -> str:
        if block_type == "diagram":
            instructions = (
                f'Produce ONE Mermaid diagram (flowchart, sequence, or graph) that '
                f'visualizes {topic} or how its steps/components relate to each other.'
            )
            content_hint = '"```mermaid\\ngraph TD\\nA-->B\\n```"'
        else:
            instructions = (
                f'Produce ONE worked example or hands-on practice problem for {topic}, '
                f'including its solution/walkthrough, so the learner can work through it step by step.'
            )
            content_hint = '"a worked example ending in its solution"'

        return f"""Topic:
{topic}

Reference material:
{context}

{instructions}

Respond with STRICT JSON ONLY, matching exactly this schema:
{{"content": <string, e.g. {content_hint}>}}

No other JSON keys, no prose outside the JSON object.
"""
