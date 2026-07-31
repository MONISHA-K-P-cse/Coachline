"""
Pytest coverage for the structured-output fixes to the agent pipeline:

  (a) resume/eval scores vary meaningfully with input content
  (b) notes differ structurally by learning style
  (c) a weak interview answer drives a real (non-static) note regeneration

Each test injects a fake GraniteClient rather than calling a live
Ollama/watsonx backend, so the suite is deterministic and runs fully
offline - the same way the real agents are unit-testable in CI without a
model server available. The fakes still exercise the real prompt-building,
JSON-parsing and Pydantic-validation code paths in each agent.
"""
import json
import re

import pytest

from ai.agents.eval_agent import EvaluationAgent
from ai.agents.notes_agent import NotesAgent
from ai.agents.resume_agent import ResumeAgent
from backend.core.mastery import update_topic_mastery
# Import the models package (not individual model modules) so every
# SQLAlchemy model is registered before mappers are configured - User has
# relationships to models (Resume, InterviewSession, ...) not otherwise
# referenced directly in this test file.
from backend.models import Base, Note, Profile, TopicMastery, User


# ---------------------------------------------------------------------------
# Fake LLM clients - content-aware so tests prove the pipeline actually
# varies output with input, not just that it can parse fixed JSON.
# ---------------------------------------------------------------------------

class ContentAwareResumeClient:
    """Scores a resume higher the more quantified/technical signal it has."""

    def generate(self, prompt: str) -> str:
        digit_count = len(re.findall(r"\d", prompt))
        strong_terms = ["led", "reduced", "scaled", "optimized", "throughput", "migrated"]
        term_hits = sum(prompt.lower().count(term) for term in strong_terms)
        score = max(10, min(97, 20 + digit_count * 4 + term_hits * 8))

        return json.dumps({
            "score": score,
            "ats_score": score,
            "summary": "Auto-generated test summary.",
            "resume_feedback": "Auto-generated test feedback.",
            "strengths": ["Relevant experience"] if score > 60 else [],
            "improvements": ["Add quantified impact"] if score <= 60 else ["Add cloud certifications"],
        })


class ContentAwareEvalClient:
    """Scores an interview answer higher the more technical depth it shows."""

    def generate(self, prompt: str) -> str:
        technical_terms = ["because", "trade-off", "complexity", "index", "cache", "handshake", "pool"]
        term_hits = sum(prompt.lower().count(term) for term in technical_terms)
        score = max(15.0, min(95.0, 25.0 + term_hits * 11.0))

        return json.dumps({
            "technical_score": score,
            "communication_score": score,
            "behavioral_score": score,
            "confidence_score": score,
            "star_score": score,
            "overall_score": score,
            "feedback": "Auto-generated test feedback.",
            "weak_topics": [] if score >= 70 else ["Connection Pooling Fundamentals"],
        })


class StyleAwareNotesClient:
    """Returns a small text-only block set for the agent's core call, and a
    style-specific supplement block (diagram/exercise) for its separate
    supplement call - mirrors the real two-call architecture, where every
    learning style gets the same core text content and only visual/
    kinesthetic styles make a second call for one extra block."""

    def generate(self, prompt: str) -> str:
        if "Produce ONE Mermaid diagram" in prompt:
            return json.dumps({
                "content": "```mermaid\ngraph TD\nA[Subproblem] --> B[Memoize] --> C[Solution]\n```",
            })
        if "Produce ONE worked example or hands-on practice problem" in prompt:
            return json.dumps({
                "content": "Practice: compute Fibonacci(10) with memoization. Solution: ...",
            })
        # Core text call (both the full and the simplified retry variant).
        return json.dumps({
            "blocks": [
                {"type": "text", "content": (
                    "I. Definition: dynamic programming solves complex problems by "
                    "breaking them into overlapping subproblems.\nII. Explanation: "
                    "results of subproblems are cached to avoid recomputation.\n"
                    "III. Key Points: memoization vs tabulation, time/space tradeoffs."
                )},
            ]
        })


class BrokenClient:
    """Simulates a model that ignores instructions and returns prose, to
    exercise the fallback path."""

    def generate(self, prompt: str) -> str:
        return "Sure! Here's my analysis in plain English with no JSON at all."


# ---------------------------------------------------------------------------
# (a) Structured, content-driven scoring
# ---------------------------------------------------------------------------

STRONG_RESUME = """
Senior Backend Engineer, 6 years experience.
Led a team of 8 engineers; reduced p99 API latency by 42% and scaled
throughput to 12,000 requests/sec. Migrated 15 microservices to Kubernetes,
optimized database indexing, and cut infra costs by 30%.
"""

WEAK_RESUME = """
Looking for a job. Know some programming. Good team player. Hardworking.
"""

STRONG_ANSWER = """
Connection pooling reuses a fixed set of established database connections
because opening a new TCP/TLS handshake per request is expensive. There's a
trade-off between pool size and memory/connection overhead; an LRU cache
for hot queries plus a B-tree index reduces lookup complexity further.
"""

WEAK_ANSWER = "It's like a thing that connects to the database. Not totally sure."


def test_resume_scores_differ_for_strong_vs_weak_resume():
    agent = ResumeAgent(client=ContentAwareResumeClient())

    strong = agent.analyze_resume(STRONG_RESUME)
    weak = agent.analyze_resume(WEAK_RESUME)

    assert strong["fallback_used"] is False
    assert weak["fallback_used"] is False
    assert strong["score"] != weak["score"]
    assert strong["score"] > weak["score"]
    assert strong["keyword_count"] != weak["keyword_count"]


def test_eval_scores_differ_for_strong_vs_weak_answer():
    agent = EvaluationAgent(client=ContentAwareEvalClient())

    strong = agent.evaluate_answer("Explain connection pooling.", STRONG_ANSWER)
    weak = agent.evaluate_answer("Explain connection pooling.", WEAK_ANSWER)

    assert strong["fallback_used"] is False
    assert weak["fallback_used"] is False
    assert strong["overall_score"] != weak["overall_score"]
    assert strong["overall_score"] > weak["overall_score"]
    assert weak["weak_topics"] != []
    assert strong["weak_topics"] == []


def test_resume_agent_falls_back_only_on_genuine_parse_failure():
    agent = ResumeAgent(client=BrokenClient())
    result = agent.analyze_resume(STRONG_RESUME)

    assert result["fallback_used"] is True
    assert result["score"] == 50


def test_eval_agent_falls_back_only_on_genuine_parse_failure():
    agent = EvaluationAgent(client=BrokenClient())
    result = agent.evaluate_answer("Explain connection pooling.", STRONG_ANSWER)

    assert result["fallback_used"] is True
    assert result["overall_score"] == 50.0


# ---------------------------------------------------------------------------
# (b) Learning-style-branched notes
# ---------------------------------------------------------------------------

def test_notes_differ_structurally_by_learning_style():
    agent = NotesAgent(client=StyleAwareNotesClient())

    visual = agent.generate_notes("Dynamic Programming", learning_style="visual")
    kinesthetic = agent.generate_notes("Dynamic Programming", learning_style="kinesthetic")
    reading = agent.generate_notes("Dynamic Programming", learning_style="reading_writing")

    visual_types = [b["type"] for b in visual["blocks"]]
    kinesthetic_types = [b["type"] for b in kinesthetic["blocks"]]
    reading_types = [b["type"] for b in reading["blocks"]]

    assert visual_types == ["text", "diagram"]
    assert kinesthetic_types == ["text", "exercise"]
    assert reading_types == ["text"]
    assert visual_types != kinesthetic_types
    assert visual_types != reading_types


def test_notes_agent_falls_back_to_single_text_block_on_parse_failure():
    agent = NotesAgent(client=BrokenClient())
    result = agent.generate_notes("Dynamic Programming", learning_style="visual")

    assert len(result["blocks"]) == 1
    assert result["blocks"][0]["type"] == "text"


class FailsOnceThenSucceedsClient:
    """Simulates a model that can't produce the fuller multi-block JSON on
    the first attempt but succeeds on the simplified single-block retry -
    exercises the retry-before-fallback path so the placeholder is only used
    as a last resort, not whenever the first attempt is imperfect."""

    def __init__(self):
        self.calls = 0

    RECOVERED_CONTENT = (
        "Recovered via simplified retry: dynamic programming solves problems "
        "by breaking them into overlapping subproblems and caching results."
    )

    def generate(self, prompt: str) -> str:
        self.calls += 1
        if self.calls == 1:
            return "not valid json at all"
        return json.dumps({"blocks": [{"type": "text", "content": self.RECOVERED_CONTENT}]})


def test_notes_agent_retries_simplified_prompt_before_falling_back():
    client = FailsOnceThenSucceedsClient()
    agent = NotesAgent(client=client)
    result = agent.generate_notes("Dynamic Programming", learning_style="reading_writing")

    assert client.calls == 2
    assert result["blocks"] == [{"type": "text", "content": client.RECOVERED_CONTENT}]


# ---------------------------------------------------------------------------
# (c) Weak answer -> real (non-static) end-to-end note regeneration
# ---------------------------------------------------------------------------

@pytest.fixture
def db_session(tmp_path):
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    engine = create_engine(f"sqlite:///{tmp_path}/mastery_test.db")
    Base.metadata.create_all(bind=engine)
    TestingSessionLocal = sessionmaker(bind=engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()


def test_weak_answer_triggers_real_note_regeneration_end_to_end(db_session, monkeypatch):
    # core.mastery imports NotesAgent lazily (inside the function body, to
    # avoid making the RAG stack a hard import-time dependency of the whole
    # backend app) so the class is patched at its home module instead.
    monkeypatch.setattr(
        "ai.agents.notes_agent.NotesAgent",
        lambda: NotesAgent(client=StyleAwareNotesClient()),
    )

    user = User(email="weak-answer@test.coachline.ai", hashed_password="x")
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)

    profile = Profile(user_id=user.id, learning_style="visual")
    db_session.add(profile)
    db_session.commit()

    topic = "Database Connection Pooling"

    # Simulates a weak interview answer: eval agent flags the topic weak,
    # api/interview.py-style code drives mastery down via a negative delta.
    update_topic_mastery(db_session, user_id=user.id, topic=topic, score_delta=-40.0)

    mastery = db_session.query(TopicMastery).filter(
        TopicMastery.user_id == user.id, TopicMastery.topic == topic
    ).first()
    assert mastery is not None
    assert mastery.needs_regeneration is True

    note = db_session.query(Note).filter(
        Note.user_id == user.id, Note.topic == topic
    ).first()
    assert note is not None

    blocks = json.loads(note.content)
    block_types = [b["type"] for b in blocks]

    # Real agent output for a "visual" learner (from the fixture profile),
    # not the old static "Targeted Revision Note" template string.
    assert "diagram" in block_types
    assert "Targeted Revision Note" not in note.content
