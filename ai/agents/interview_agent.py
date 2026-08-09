import logging

from pydantic import ValidationError

from ai.agents.granite_client import GraniteClient
from ai.agents.llm_json import extract_json
from ai.rag.retriever import retrieve
from backend.schemas.interview import EvalAgentResult
from ai.agents.question_bank import QUESTION_BANK

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
        initial_topic = "DSA"
        if topic:
            for t_name in QUESTION_BANK.keys():
                if t_name.lower() in topic.lower() or topic.lower() in t_name.lower():
                    initial_topic = t_name
                    break
        else:
            r_lower = role.lower()
            if "data" in r_lower or "ml" in r_lower or "machine learning" in r_lower or "scientist" in r_lower:
                initial_topic = "ML"
            elif "backend" in r_lower:
                initial_topic = "DBMS"
            elif "frontend" in r_lower or "ui" in r_lower or "react" in r_lower:
                initial_topic = "CN"
            elif "python" in r_lower:
                initial_topic = "Python"
            elif "java" in r_lower:
                initial_topic = "Java"

        initial_q = QUESTION_BANK[initial_topic]["Easy"][0]

        return {
            "role": role,
            "difficulty": "Easy",
            "question": initial_q,
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

    def generate_simpler_question(self, role: str, previous_question: str, previous_answer: str, week: int, topic: str) -> str:
        prompt = f"""You are an expert technical interviewer.

Role: {role}
Week {week} Topic: {topic}

The candidate struggled to answer this question:
"{previous_question}"

Their weak/incomplete answer was:
"{previous_answer}"

Since they are struggling with this concept, you need to lower the difficulty.
Generate ONE simpler, basic follow-up question or revisit a prerequisite concept to help them rebuild their confidence and test their fundamental understanding of this topic.

Do NOT use JSON. Keep the question brief and encouraging.
"""
        response = self.client.generate(prompt)
        return response.strip()

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
        history: list = None,
        session_metadata: dict = None,
        duration_seconds: int = 0
    ):
        bg_part = f"Candidate Background (from their resume):\n{candidate_background}" if candidate_background else ""
        exp_part = f"Candidate Experience Level: {experience_level}" if experience_level else ""

        prompt = f"""You are an expert technical interviewer conducting a mock interview for the following candidate profile:

Role: {role}
{exp_part}
{bg_part}

The candidate was just asked:
"{question}"

The candidate answered:
"{answer}"

Evaluate their answer based on:
1. Technical correctness
2. Completeness
3. Communication clarity
4. Confidence
5. Response time (response was completed in {duration_seconds} seconds)
6. Follow-up quality (relevance to the prompt)

Respond with STRICT JSON ONLY. No prose, no markdown code fences, no commentary before or after the JSON object.

The JSON object MUST match exactly this schema:
{{
  "technical_score": <number 0-100>,
  "communication_score": <number 0-100>,
  "behavioral_score": <number 0-100>,
  "confidence_score": <number 0-100>,
  "star_score": <number 0-100>,
  "overall_score": <number 0-100, weighted overall impression>,
  "feedback": <string, detailed strengths and weaknesses of the answer>,
  "weak_topics": [<string>, ...],
  "strong_topics": [<string>, ...],
  "remedial_explanation": <string, if overall_score is < 50, provide a brief 2-3 sentence educational teaching explaining the correct concept. Otherwise, empty string.>
}}
"""
        raw = self.client.generate(prompt)
        data = extract_json(raw)

        # Build EvalResult dictionary
        result = {
            "technical_score": float(data.get("technical_score", 50.0)),
            "communication_score": float(data.get("communication_score", 50.0)),
            "behavioral_score": float(data.get("behavioral_score", 50.0)),
            "confidence_score": float(data.get("confidence_score", 50.0)),
            "star_score": float(data.get("star_score", 50.0)),
            "overall_score": float(data.get("overall_score", 50.0)),
            "feedback": str(data.get("feedback", "No feedback provided.")),
            "weak_topics": [str(t) for t in data.get("weak_topics", [])],
            "strong_topics": [str(t) for t in data.get("strong_topics", [])],
            "remedial_explanation": str(data.get("remedial_explanation", "")),
            "fallback_used": False
        }

        # Retrieve and initialize session metadata
        meta = dict(session_metadata) if session_metadata else {}
        if "current_difficulty" not in meta:
            meta["current_difficulty"] = "Easy"
        if "difficulty_reached" not in meta:
            meta["difficulty_reached"] = "Easy"
        if "weak_topics" not in meta:
            meta["weak_topics"] = []
        if "strong_topics" not in meta:
            meta["strong_topics"] = []
        if "questions_asked" not in meta:
            meta["questions_asked"] = []
        if "live_skill_scores" not in meta:
            meta["live_skill_scores"] = {
                "DSA": 50.0, "DBMS": 50.0, "OS": 50.0, "CN": 50.0, "OOP": 50.0,
                "System Design": 50.0, "ML": 50.0, "Python": 50.0, "Java": 50.0, "Aptitude": 50.0
            }
        if "consecutive_followups" not in meta:
            meta["consecutive_followups"] = 0

        # Register current question in history
        if question not in meta["questions_asked"]:
            meta["questions_asked"].append(question)

        # Add weak/strong topics
        for wt in result["weak_topics"]:
            if wt not in meta["weak_topics"]:
                meta["weak_topics"].append(wt)
        for st in result["strong_topics"]:
            if st not in meta["strong_topics"]:
                meta["strong_topics"].append(st)

        # Match question to primary topic
        matched_topic = "DSA"
        for t_name, difficulties in QUESTION_BANK.items():
            for diff_lvl, q_list in difficulties.items():
                if any(q.lower() in question.lower() or question.lower() in q.lower() for q in q_list):
                    matched_topic = t_name
                    break
            if matched_topic != "DSA":
                break

        # Update skill score for matched topic
        overall_score = result["overall_score"]
        delta = (overall_score - 70.0) * 0.5
        meta["live_skill_scores"][matched_topic] = max(0.0, min(100.0, meta["live_skill_scores"][matched_topic] + delta))

        # Adjust general skill scores matching keywords in weak/strong topics
        TOPICS_LIST = ["DSA", "DBMS", "OS", "CN", "OOP", "System Design", "ML", "Python", "Java", "Aptitude"]
        for topic_key in TOPICS_LIST:
            t_lower = topic_key.lower()
            for wt in result["weak_topics"]:
                if t_lower in wt.lower():
                    meta["live_skill_scores"][topic_key] = max(0.0, meta["live_skill_scores"][topic_key] - 3.0)
            for st in result["strong_topics"]:
                if t_lower in st.lower():
                    meta["live_skill_scores"][topic_key] = min(100.0, meta["live_skill_scores"][topic_key] + 2.0)

        # Update current difficulty
        DIFFICULTY_LEVELS = ["Easy", "Medium", "Hard", "Expert"]
        curr_idx = DIFFICULTY_LEVELS.index(meta["current_difficulty"])
        
        # Difficulty rules
        if overall_score >= 85.0:
            curr_idx = min(3, curr_idx + 1)
        elif overall_score < 50.0:
            curr_idx = max(0, curr_idx - 1)
            
        meta["current_difficulty"] = DIFFICULTY_LEVELS[curr_idx]
        
        # Update difficulty reached
        highest_reached_idx = DIFFICULTY_LEVELS.index(meta["difficulty_reached"])
        if curr_idx > highest_reached_idx:
            meta["difficulty_reached"] = DIFFICULTY_LEVELS[curr_idx]

        # Determine next question path
        next_question = ""
        difficulty_tier = meta["current_difficulty"]
        mode = "standard"

        # 1. Good Answer (Score >= 70) and we can do a Dynamic Follow-up
        if overall_score >= 70.0 and meta["consecutive_followups"] < 1:
            meta["consecutive_followups"] += 1
            mode = "followup"
            difficulty_tier = meta["current_difficulty"]
            
            followup_prompt = f"""You are an expert technical interviewer.
The candidate was asked: "{question}"
They answered: "{answer}"
Which scored {overall_score} (Good answer).

Generate ONE brief, specific technical follow-up question asking them to defend their answer, explain trade-offs, discuss scalability, optimize the implementation, or handle an edge case. Do not be generic.
Do NOT use JSON. Keep the question under 2 sentences.
"""
            next_question = self.client.generate(followup_prompt).strip()

        # 2. Weak Answer (Score < 70)
        elif overall_score < 70.0:
            meta["consecutive_followups"] = 0
            
            # Case 2a: Score < 50 (Step back + Explain prerequisite concept)
            if overall_score < 50.0:
                mode = "remedial"
                unused_q = None
                prereq_diff = "Easy"
                for q_candidate in QUESTION_BANK[matched_topic][prereq_diff]:
                    if q_candidate not in meta["questions_asked"]:
                        unused_q = q_candidate
                        break
                if not unused_q:
                    unused_q = f"Let's go back to the basic principles of {matched_topic}. Can you explain its core concept in simple terms?"
                    
                remedial_explanation = result["remedial_explanation"] or f"In {matched_topic}, it is important to build on solid fundamentals first."
                next_question = f"Let's step back and look at a prerequisite concept. First, a brief explanation: {remedial_explanation}\n\nQuestion: {unused_q}"
                difficulty_tier = "Easy"
                
            # Case 2b: Score 50-69 (Stay at same level, ask another question on same concept)
            else:
                mode = "standard"
                unused_q = None
                for q_candidate in QUESTION_BANK[matched_topic][meta["current_difficulty"]]:
                    if q_candidate not in meta["questions_asked"]:
                        unused_q = q_candidate
                        break
                if not unused_q:
                    unused_q = f"Could you walk me through another scenario involving {matched_topic}?"
                    
                next_question = f"Let's try another question on the same level: {unused_q}"

        # 3. Transition to a new topic (after follow-up or on progression)
        else:
            meta["consecutive_followups"] = 0
            
            # Select next untested topic
            untested_topics = [t for t in TOPICS_LIST if not any(t in q for q in meta["questions_asked"])]
            if untested_topics:
                next_topic = untested_topics[0]
            else:
                # Pick topic with lowest skill score
                next_topic = min(meta["live_skill_scores"], key=meta["live_skill_scores"].get)
                
            # Determine target difficulty based on that topic's current score
            target_diff = "Easy"
            skill_score = meta["live_skill_scores"][next_topic]
            if skill_score >= 85.0:
                target_diff = "Expert"
            elif skill_score >= 70.0:
                target_diff = "Hard"
            elif skill_score >= 50.0:
                target_diff = "Medium"
                
            unused_q = None
            for q_candidate in QUESTION_BANK[next_topic][target_diff]:
                if q_candidate not in meta["questions_asked"]:
                    unused_q = q_candidate
                    break
            
            # Try adjacent difficulties if no question found
            if not unused_q:
                for diff_lvl in DIFFICULTY_LEVELS:
                    for q_candidate in QUESTION_BANK[next_topic][diff_lvl]:
                        if q_candidate not in meta["questions_asked"]:
                            unused_q = q_candidate
                            break
                    if unused_q:
                        break
                        
            if not unused_q:
                unused_q = f"Let's explore your knowledge in {next_topic}. What is the most complex design choice you made in this domain?"
                
            next_question = unused_q
            difficulty_tier = target_diff

        if next_question not in meta["questions_asked"]:
            meta["questions_asked"].append(next_question)

        return result, {
            "role": role,
            "difficulty": difficulty_tier,
            "question": next_question,
            "mode": mode,
        }, meta