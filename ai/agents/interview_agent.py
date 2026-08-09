import logging

from pydantic import ValidationError

from ai.agents.granite_client import GraniteClient
from ai.agents.llm_json import extract_json
from ai.rag.retriever import retrieve
from backend.schemas.interview import EvalAgentResult

logger = logging.getLogger("interview_agent")

# Same threshold interview.py uses to decide devil's-advocate mode - kept
# here too since the combined call now makes that decision internally.
DEVILS_ADVOCATE_SCORE_THRESHOLD = 80.0

# Baseline difficulty tier implied by the candidate's self-reported
# experience level, independent of how they've scored so far this session.
_LEVEL_RANK = {
    "entry": 0,
    "junior": 0,
    "intermediate": 1,
    "senior": 2,
    "staff+": 2,
}
_DIFFICULTY_NAMES = ["Beginner", "Medium", "Hard"]


def _score_rank(previous_score: float) -> int:
    if previous_score >= 80:
        return 2
    if previous_score >= 60:
        return 1
    return 0


def get_syllabus_questions(role: str, week: int) -> list:
    w = max(1, min(8, week))
    role_lower = role.lower()
    
    syllabus_backend = [
        ["What is the difference between PUT and PATCH, and when would you use each?",
         "How would you design a robust API pagination strategy for a high-volume endpoint?",
         "What are idempotency keys, and how do they ensure safe request retries in payment APIs?"],
        ["Explain the difference between a clustered and non-clustered index, and how they impact write operations.",
         "How do database replica lags occur in primary-replica setups, and how do you handle read-after-write consistency?",
         "Under what conditions is database sharding preferred over vertical scaling and replication?"],
        ["What is cache stampede (thundering herd) and how do you mitigate it using mutual exclusion or background warming?",
         "Compare the Cache-Aside, Write-Through, and Write-Back caching strategies.",
         "How does Redis handle eviction when memory is full, and what is the difference between volatile-lru and allkeys-lru?"],
        ["What is the difference between a process and a thread, and how does the GIL affect concurrency in Python?",
         "How do you identify and resolve thread deadlocks in high-concurrency systems?",
         "Explain the event loop model in asynchronous frameworks compared to multi-threaded worker pools."],
        ["How does Kafka guarantee message ordering within a topic, and what happens when a consumer group rebalances?",
         "What is the difference between at-least-once, at-most-once, and exactly-once delivery guarantees?",
         "How do you handle consumer backpressure when message ingress rates exceed processing capabilities?"],
        ["What is the Saga pattern, and how does it maintain data consistency compared to two-phase commits (2PC)?",
         "How does a circuit breaker prevent cascading failures in a microservices mesh?",
         "Compare service discovery models: client-side discovery vs server-side discovery."],
        ["Why should you use multi-stage Docker builds, and how do they impact image footprint security?",
         "What is the difference between a Kubernetes Pod, ReplicaSet, and Deployment?",
         "How do Kubernetes readiness probes differ from liveness probes, and why are they critical during rollouts?"],
        ["How would you design a distributed token-bucket rate limiter that scales across multiple servers?",
         "What is the difference between active-passive and active-active failover strategies?",
         "How do you monitor key metrics like latency, throughput, error rates, and saturation (Golden Signals)?"]
    ]

    syllabus_frontend = [
        ["What is a closure in JavaScript, and how can it lead to memory leaks?",
         "How does the JavaScript event loop handle call stack, microtask queue, and macrotask queue priorities?",
         "Explain TypeScript utility types like Omit, Pick, and Exclude, and how they ensure type safety."],
        ["What is React Fiber, and how does it enable concurrent rendering and interruptible updates?",
         "How do you prevent unnecessary re-renders in deep React component trees?",
         "Compare React state hooks (useState, useReducer) with ref hooks (useRef) in terms of rendering triggers."],
        ["What are Core Web Vitals (LCP, FID, CLS, INP), and how do you optimize them?",
         "How does dynamic import() enable code splitting, and how do you implement route-level lazy loading?",
         "How do resource hints like prefetch, preload, and preconnect optimize the critical rendering path."],
        ["Compare the data flow models of Redux vs Zustand vs Recoil in state architectures.",
         "What is prop drilling, and how does React Context API solve it? What are Context's performance trade-offs?",
         "How do you synchronize local state changes with server database states (e.g. using React Query / SWR)?"],
        ["How does a Service Worker enable offline capabilities and background sync in Progressive Web Apps?",
         "Explain cross-site scripting (XSS) and cross-site request forgery (CSRF), and how modern frontends defend against them.",
         "What is Content Security Policy (CSP), and how do nonce tokens secure inline scripts?"],
        ["Compare CSS Flexbox (1D) vs CSS Grid (2D), and when is each layout model preferred?",
         "How do CSS container queries differ from traditional viewport-based media queries?",
         "What are the pros and cons of utility-first CSS frameworks like Tailwind compared to CSS Modules?"],
        ["What is the difference between unit testing, component testing, and end-to-end (E2E) testing?",
         "How do you mock API calls in component tests using tools like Mock Service Worker (MSW)?",
         "What are the key stages of a frontend deployment pipeline (linting, build verification, asset hosting)?"],
        ["Compare Server-Side Rendering (SSR), Static Site Generation (SSG), and Client-Side Rendering (CSR).",
         "How do React Server Components (RSC) differ from standard client components, and how do they reduce bundle sizes?",
         "What is progressive hydration, and how does it optimize Time to Interactive (TTI)?"]
    ]

    syllabus_ds = [
        ["How do you handle collinear features in linear regression models?",
         "Explain the difference between L1 (Lasso) and L2 (Ridge) regularization.",
         "What is the target leakage in ML pipelines, and how do you prevent it?"],
        ["Why is the ROC-AUC score preferred over classification accuracy for imbalanced datasets?",
         "How does a Random Forest model determine feature importances?",
         "What are the differences between K-Means and DBSCAN clustering algorithms?"],
        ["What is the vanishing gradient problem, and how do activation functions like ReLU mitigate it?",
         "Explain the role of Dropout layers during training vs inference.",
         "What is the difference between SGD, Adam, and RMSprop optimizers?"],
        ["Explain the self-attention mechanism in Transformer architectures.",
         "What is the difference between fine-tuning a model and utilizing RAG templates?",
         "How do temperature and top-p sampling impact text generation output randomness?"],
        ["How do you structure a high-throughput inference API for ML models using FastAPI?",
         "What is model drift, and how do you monitor performance changes in production?",
         "Under what scenarios would you choose batch prediction over real-time API inference?"],
        ["How does PySpark manage data partitioning and shuffle operations during joins?",
         "Explain the difference between ETL and ELT pipelines, and when to use Snowflake vs Redshift.",
         "How do you handle schema evolution in streaming data lakes?"],
        ["How do you determine the required sample size for an A/B test based on statistical power?",
         "What is the p-value, and what does it mean to achieve a 95% confidence interval?",
         "How do you identify and control for skew and bias in user assignment metrics?"],
        ["What are the core components of an MLOps pipeline, and how does model registry versioning work?",
         "How do you detect feature drift in a model's inputs over time?",
         "What is continuous training (CT) and when should it be automated?"]
    ]

    syllabus_default = [
        ["What is the difference between quicksort and mergesort in terms of time and space complexity?",
         "Explain how dynamic programming optimization differs from memoization techniques.",
         "What is a pointer, and how does garbage collection manage reference counts in modern runtimes?"],
        ["How do hash map collisions occur, and how do separate chaining and open addressing resolve them?",
         "What is the difference between depth-first search (DFS) and breadth-first search (BFS) on graphs?",
         "What is a binary search tree, and how do you balance a tree in-place?"],
        ["Explain the Single Responsibility Principle and the Dependency Inversion Principle.",
         "What is the Singleton pattern, and how do you implement a thread-safe singleton?",
         "Compare the Strategy design pattern with the State design pattern."],
        ["What is the difference between vertical scaling and horizontal scaling?",
         "How does a DNS query resolution loop execute from client to root server?",
         "What is the role of a reverse proxy vs a load balancer?"],
        ["What are ACID transactions, and what is the role of Write-Ahead Logging (WAL)?",
         "Explain the difference between Read Committed and Serializable transaction isolation levels.",
         "Under what scenarios is a NoSQL document database preferred over a normalized relational database?"],
        ["How does a TCP 3-way handshake establish a connection, and how does TLS handshake secure it?",
         "Explain how WebSockets enable full-duplex communication over a single TCP connection.",
         "What is HTTP/2 multiplexing, and how does it optimize page asset loading?"],
        ["Compare Git merge vs Git rebase workflows, and when to use each.",
         "How do you design a secure, automated CI/CD pipeline that enforces testing gates?",
         "What is Git cherry-pick, and under what conditions is it used?"],
        ["What is the difference between symmetric and asymmetric encryption, and how are they used in SSL/TLS?",
         "Explain the OAuth2 authorization code grant flow with PKCE.",
         "How does a token-bucket rate limiter enforce traffic bounds on APIs?"]
    ]

    if "backend" in role_lower:
        return syllabus_backend[w - 1]
    elif "frontend" in role_lower or "ui" in role_lower or "react" in role_lower:
        return syllabus_frontend[w - 1]
    elif "data scientist" in role_lower or "machine learning" in role_lower or "ds" in role_lower or "ml" in role_lower:
        return syllabus_ds[w - 1]
    else:
        return syllabus_default[w - 1]


class InterviewAgent:
    def __init__(self):
        self.client = GraniteClient()

    def generate_question(
        self,
        role: str,
        previous_score: float = 0,
        experience_level: str = "",
        candidate_background: str = "",
        is_opening_question: bool = False,
        week: int = 1,
        topic: str = "",
        syllabus: list = None,
    ):
        context = "\n\n".join(
            retrieve(role, k=3)
        )

        # Blend the candidate's stated experience level with how they've
        # actually scored so far, so a self-described Senior candidate
        # starts harder than a self-described Entry-level one even before
        # either has scored anything, and both still adapt from there.
        level_rank = _LEVEL_RANK.get(experience_level.lower().strip(), 1)
        combined_rank = round((level_rank + _score_rank(previous_score)) / 2)
        difficulty = _DIFFICULTY_NAMES[combined_rank]

        opening_instructions = (
            f"""This is the FIRST question of the interview for Week {week}: {topic or role}.
Open with a brief warm one-sentence welcome that mentions the week topic, then ask the candidate
to introduce themselves and their experience specifically related to this week's topics."""
            if is_opening_question
            else f"Generate ONE interview question that follows on from the interview so far. It MUST be about one of the Week {week} syllabus topics listed above."
        )

        bg_part = f"Candidate Background (from their resume):\n{candidate_background}" if candidate_background else ""
        exp_part = f"Candidate Experience Level: {experience_level}" if experience_level else ""
        syllabus_part = (
            f"""Week {week} Syllabus Subtopics (MANDATORY - your question MUST be specifically about one of these):
""" + "\n".join(f"  - {s}" for s in syllabus)
        ) if syllabus else f"Week {week} Topic: {topic or role}"

        prompt = f"""
You are an expert technical interviewer.

Role:
{role}
{exp_part}
{bg_part}

{syllabus_part}

Difficulty:
{difficulty}

Reference Material (only use if directly relevant to the syllabus topics above):
{context}

Calibrate the question's depth and phrasing to the candidate's experience
level above (if given) as well as the target difficulty. The question MUST
be directly about one of the syllabus subtopics listed above - do not ask
about unrelated CS topics.

{opening_instructions}

Then provide:

Expected Answer:
Hints:

Do NOT use JSON.
"""

        response = self.client.generate(prompt)

        # Override response to return only standard questions from the weekly syllabus
        q_list = get_syllabus_questions(role, week)
        if is_opening_question:
            q_text = f"Welcome to your mock interview! Let's start with the Week {week} topic: {topic or 'Technical Foundations'}. Could you introduce yourself briefly and explain how you would tackle this question: {q_list[0]}"
        else:
            q_text = q_list[0]

        return {
            "role": role,
            "difficulty": difficulty,
            "question": q_text,
            "previous_score": previous_score,
            "mode": "standard",
        }

    def generate_devils_advocate_question(self, role: str, question: str, answer: str):
        """
        Follow-up question that challenges a strong answer, rather than
        moving on to an unrelated topic - triggered by the caller when the
        candidate's previous answer scored highly.
        """
        context = "\n\n".join(retrieve(role, k=3))

        prompt = f"""
You are an expert technical interviewer playing devil's advocate.

Role:
{role}

The candidate was just asked:
{question}

The candidate answered:
{answer}

Reference Material:
{context}

The candidate's answer was strong. Push back on it: identify a specific
edge case, trade-off, or weak point in THEIR answer above, and challenge
them to defend or refine it. The follow-up must reference specifics from
their actual answer - do not ask an unrelated question.

Then provide:

Expected Answer:
Hints:

Do NOT use JSON.
"""

        response = self.client.generate(prompt)

        return {
            "role": role,
            "difficulty": "Devil's Advocate",
            "question": response,
            "previous_score": None,
            "mode": "devils_advocate",
        }

    def evaluate_and_generate_next(
        self,
        role: str,
        question: str,
        answer: str,
        experience_level: str = "",
        candidate_background: str = "",
        week: int = 1,
        topic: str = "",
        syllabus: list = None,
    ):
        """
        Scores the candidate's answer AND produces the next question in a
        SINGLE Granite call, instead of two sequential round-trips (eval,
        then next-question generation). On CPU-only inference each call can
        take 15-100s+, so halving the number of calls per turn roughly
        halves the "evaluating..." wait. Falls back to the two-call path
        (see interview.py) if this combined call's output can't be parsed.
        """
        context = "\n\n".join(retrieve(role, k=3))

        bg_part = f"Candidate Background (from their resume):\n{candidate_background}" if candidate_background else ""
        exp_part = f"Candidate Experience Level: {experience_level}" if experience_level else ""
        syllabus_part = (
            f"""Week {week} Syllabus Subtopics (the next_question MUST cover one of these):
""" + "\n".join(f"  - {s}" for s in syllabus)
        ) if syllabus else f"Week {week} Topic: {topic or role}"

        prompt = f"""You are an expert technical interviewer conducting a mock interview for the following candidate profile:

Role:
{role}
{exp_part}
{bg_part}

{syllabus_part}

Reference Material (only use if directly relevant to the syllabus topics above):
{context}

The candidate was just asked:
{question}

The candidate answered:
{answer}

Respond with STRICT JSON ONLY. No prose, no markdown code fences, no
commentary before or after the JSON object.

The JSON object MUST match exactly this schema:
{{
  "technical_score": <number 0-100>,
  "communication_score": <number 0-100>,
  "behavioral_score": <number 0-100>,
  "confidence_score": <number 0-100>,
  "star_score": <number 0-100>,
  "overall_score": <number 0-100, weighted overall impression>,
  "feedback": <string, strengths and weaknesses of the answer>,
  "weak_topics": [<string>, ...],
  "mode": "standard" or "devils_advocate",
  "next_question": <string, the next interview question - see rules below>
}}

Base every score strictly on the substance, correctness and depth of the
candidate answer above. A vague, incorrect or incomplete answer must score
noticeably lower than a precise, well-reasoned one. "weak_topics" MUST be
derived only from actual gaps in the candidate's answer above - never from
the Reference Material or any unrelated subject area - and should be an
empty list if there are none.

Rules for "next_question" and "mode":
- If overall_score is 80 or above, set "mode" to "devils_advocate" and make
  "next_question" push back on the candidate's OWN answer above: identify a
  specific edge case, trade-off, or weak point in what THEY actually said,
  and challenge them to defend or refine it. It must reference specifics
  from their real answer, not a generic follow-up.
- Otherwise, set "mode" to "standard" and make "next_question" a genuinely
  new question. Its SUBJECT MATTER must be about one of the Week Syllabus
  Subtopics listed above. Calibrate its difficulty to the candidate's experience
  level (if given) blended with the overall_score you just gave this
  answer: entry-level or a low score should get an easier, single-concept
  question; senior-level or a high score should get a harder question
  probing trade-offs, scale, or failure modes.
"""

        raw = self.client.generate(prompt)
        data = extract_json(raw)

        result = EvalAgentResult(
            technical_score=float(data["technical_score"]),
            communication_score=float(data["communication_score"]),
            behavioral_score=float(data["behavioral_score"]),
            confidence_score=float(data["confidence_score"]),
            star_score=float(data["star_score"]),
            overall_score=float(data["overall_score"]),
            feedback=str(data["feedback"]),
            weak_topics=[str(t) for t in data.get("weak_topics", [])],
            fallback_used=False,
        ).model_dump()

        next_question = str(data["next_question"]).strip()
        if not next_question:
            raise ValueError("Combined call returned an empty next_question")

        mode = data.get("mode") if data.get("mode") in ("standard", "devils_advocate") else (
            "devils_advocate" if result["overall_score"] >= DEVILS_ADVOCATE_SCORE_THRESHOLD else "standard"
        )

        # Override standard next questions to strictly follow the weekly syllabus sequence
        if mode == "standard":
            q_list = get_syllabus_questions(role, week)
            current_q_lower = question.lower()
            if q_list[0].lower() in current_q_lower:
                next_question = q_list[1]
            elif q_list[1].lower() in current_q_lower:
                next_question = q_list[2]
            elif q_list[2].lower() in current_q_lower:
                next_question = "Thank you! We have completed all the questions for this week's syllabus. I will now compile your overall performance score."
            else:
                next_question = q_list[0]

        return result, {
            "role": role,
            "difficulty": "Devil's Advocate" if mode == "devils_advocate" else None,
            "question": next_question,
            "mode": mode,
        }