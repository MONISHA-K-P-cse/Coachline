import concurrent.futures
import logging
import os

logger = logging.getLogger("granite_client")

DEFAULT_OLLAMA_MODEL = "granite4:1b"
DEFAULT_WATSONX_MODEL_ID = "ibm/granite-3-8b-instruct"
DEFAULT_WATSONX_URL = "https://us-south.ml.cloud.ibm.com"


class GraniteClient:
    """
    Wrapper for IBM Granite LLM calls.

    Provider is selected via the LLM_PROVIDER env var:
      - "watsonx" (default): calls IBM watsonx.ai. If the call errors or
        times out (missing credentials, network issue, etc.) it falls back
        to a local Ollama Granite model so demos stay reliable offline.
      - "ollama": always uses the local Ollama Granite model directly -
        useful for offline dev/demo without watsonx credentials.
    """
    _mock_counter = 0

    def __init__(self, model: str = None, provider: str = None):
        self.provider = (provider or os.getenv("LLM_PROVIDER", "watsonx")).lower()
        # GRANITE_MODEL is the single knob for swapping the local demo model
        # (e.g. granite4:1b vs granite4:3b) without touching code; OLLAMA_MODEL
        # is kept as a fallback name for backwards compatibility.
        self.ollama_model = (
            model
            or os.getenv("GRANITE_MODEL")
            or os.getenv("OLLAMA_MODEL", DEFAULT_OLLAMA_MODEL)
        )
        self.watsonx_model_id = os.getenv("WATSONX_MODEL_ID", DEFAULT_WATSONX_MODEL_ID)
        self.watsonx_timeout = float(os.getenv("WATSONX_TIMEOUT_SECONDS", "30"))
        # Generous but still finite: on CPU-only inference a single call can
        # legitimately take 100-170s+ for longer prompts (e.g. resume
        # analysis with rewrite suggestions), so this needs real headroom
        # above observed worst-case latency, not just the "typical" case -
        # the point is bounding a genuine hang, not racing normal slowness.
        self.ollama_timeout = float(os.getenv("OLLAMA_TIMEOUT_SECONDS", "240"))
        # How long Ollama keeps the model resident in memory after a call
        # before unloading it. Ollama's own default is 5m; a demo doing many
        # back-to-back calls benefits from holding it much longer so a gap
        # between requests doesn't force a multi-second-to-multi-minute
        # reload. "-1" means keep loaded indefinitely.
        self.ollama_keep_alive = os.getenv("OLLAMA_KEEP_ALIVE", "30m")
        self._watsonx_model = None

    def generate(self, prompt: str) -> str:
        if self.provider == "watsonx":
            try:
                return self._generate_watsonx(prompt)
            except Exception as exc:
                logger.warning(
                    "watsonx.ai call failed (%s); falling back to local Ollama Granite model '%s'.",
                    exc,
                    self.ollama_model,
                )

        try:
            return self._generate_ollama(prompt)
        except Exception as exc:
            logger.warning(
                "Ollama call failed (%s); falling back to offline mock mode.",
                exc,
            )
            return self._generate_mock(prompt)

    def _generate_mock(self, prompt: str) -> str:
        prompt_lower = prompt.lower()

        # 1.1 IBM Bob Agent
        if "ibm bob" in prompt_lower or "bob_audit" in prompt_lower:
            challenge_id = "sql_injection"
            if "concurrency" in prompt_lower or "threading" in prompt_lower:
                challenge_id = "concurrency_race"
            elif "cors" in prompt_lower or "security" in prompt_lower:
                challenge_id = "cors_security"
            elif "xss" in prompt_lower or "scripting" in prompt_lower:
                challenge_id = "xss_scripting"
            elif "traversal" in prompt_lower or "path" in prompt_lower:
                challenge_id = "path_traversal"

            candidate_code = ""
            if "candidate code:" in prompt_lower:
                parts = prompt.split("Candidate Code:", 1)
                if len(parts) > 1:
                    code_part = parts[1]
                    if "respond with" in code_part.lower():
                        candidate_code = code_part.split("Respond with", 1)[0].strip()
                    else:
                        candidate_code = code_part.strip()

            import json
            
            if challenge_id == "concurrency_race":
                has_lock = ("lock" in candidate_code.lower() and "threading" in candidate_code.lower()) or "acquire" in candidate_code.lower()
                if has_lock:
                    return json.dumps({
                        "plan": [
                            "Trace global counter reference access path.",
                            "Verify threading synchronization lock patterns.",
                            "Verify atomic increments are thread-safe."
                        ],
                        "vulnerabilities": [],
                        "refactored_code": candidate_code,
                        "score": 100
                    })
                else:
                    return json.dumps({
                        "plan": [
                            "Trace global counter reference access path.",
                            "Detect lack of thread synchronization locks during context-switched operations.",
                            "Formulate lock synchronization strategy to ensure atomic execution."
                        ],
                        "vulnerabilities": [{
                            "severity": "Medium",
                            "line": 4,
                            "issue": "Race condition due to shared global state accessed without synchronization locks.",
                            "fix": "Implement threading.Lock context manager."
                        }],
                        "refactored_code": "import threading\n\ncounter = 0\ncounter_lock = threading.Lock()\n\ndef increment_counter():\n    global counter\n    with counter_lock:\n        counter += 1",
                        "score": 50
                    })
            elif challenge_id == "cors_security":
                has_restricted_cors = "origin" in candidate_code.lower() and "*" not in candidate_code
                if has_restricted_cors:
                    return json.dumps({
                        "plan": [
                            "Analyze Express middleware configuration settings.",
                            "Verify restricted origin values match security headers."
                        ],
                        "vulnerabilities": [],
                        "refactored_code": candidate_code,
                        "score": 100
                    })
                else:
                    return json.dumps({
                        "plan": [
                            "Analyze Express middleware configuration settings.",
                            "Identify wildcard CORS policy headers.",
                            "Structure restricted whitelist configuration values."
                        ],
                        "vulnerabilities": [{
                            "severity": "High",
                            "line": 2,
                            "issue": "Wildcard origin ('*') allows any site to make cross-origin calls, exposing sensitive APIs.",
                            "fix": "Define an explicit list of trusted origin domains."
                        }],
                        "refactored_code": "const allowedOrigins = ['https://trusted.coachline.app'];\napp.use((req, res, next) => {\n    const origin = req.headers.origin;\n    if (allowedOrigins.includes(origin)) {\n        res.setHeader('Access-Control-Allow-Origin', origin);\n    }\n    res.setHeader('Access-Control-Allow-Methods', 'GET, POST, PUT, DELETE');\n    next();\n});",
                        "score": 30
                    })
            elif challenge_id == "xss_scripting":
                has_sanitize = "escape" in candidate_code.lower() or "sanitize" in candidate_code.lower() or "replace" in candidate_code.lower()
                if has_sanitize:
                    return json.dumps({
                        "plan": [
                            "Analyze HTML dynamic tag rendering.",
                            "Verify user-supplied inputs are escaped before rendering in div."
                        ],
                        "vulnerabilities": [],
                        "refactored_code": candidate_code,
                        "score": 100
                    })
                else:
                    return json.dumps({
                        "plan": [
                            "Analyze Express response rendering calls.",
                            "Identify unescaped HTML content insertion vectors.",
                            "Implement safe escaping middleware or utility libraries."
                        ],
                        "vulnerabilities": [{
                            "severity": "High",
                            "line": 2,
                            "issue": "Unsanitized dynamic input outputted directly to HTML response allows Cross-Site Scripting (XSS).",
                            "fix": "Escape HTML tags or use sanitization helpers before outputting."
                        }],
                        "refactored_code": "const escapeHTML = (str) => str.replace(/[&<>'\"/]/g, tag => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', \"'\": '&#39;', '\"': '&quot;', '/': '&#x2F;' }[tag] || tag));\nconst userComment = req.query.comment;\nres.send(`<div>${escapeHTML(userComment)}</div>`);",
                        "score": 35
                    })
            elif challenge_id == "path_traversal":
                has_path_check = "basename" in candidate_code.lower() or "abspath" in candidate_code.lower() or "path.join" in candidate_code.lower()
                if has_path_check:
                    return json.dumps({
                        "plan": [
                            "Analyze file paths access operations.",
                            "Verify filename parameter is sanitized using os.path.basename."
                        ],
                        "vulnerabilities": [],
                        "refactored_code": candidate_code,
                        "score": 100
                    })
                else:
                    return json.dumps({
                        "plan": [
                            "Identify path resolution methods.",
                            "Analyze lack of bounds safety checking in dynamic file path concatenation.",
                            "Structure sanitization using os.path.basename to strip path traversal sequences."
                        ],
                        "vulnerabilities": [{
                            "severity": "High",
                            "line": 2,
                            "issue": "Dynamic filepath joining without path validation allows directory traversal (../../etc/passwd).",
                            "fix": "Verify filepath bounds using os.path.basename or validate path directories."
                        }],
                        "refactored_code": "import os\n\ndef read_user_file(filename):\n    safe_filename = os.path.basename(filename)\n    filepath = os.path.join(\"/var/www/uploads\", safe_filename)\n    with open(filepath, \"r\") as f:\n        return f.read()",
                        "score": 40
                    })
            else:
                # SQL Injection
                has_bind = ":" in candidate_code or "?" in candidate_code or "%s" in candidate_code or "execute(query, {" in candidate_code.lower() or "execute(query, (" in candidate_code.lower()
                no_fstring = "f\"" not in candidate_code.lower() and "f'" not in candidate_code.lower()
                if has_bind and no_fstring:
                    return json.dumps({
                        "plan": [
                            "Analyze syntax tree of target database handler.",
                            "Verify query binding and bind parameters are structured correctly."
                        ],
                        "vulnerabilities": [],
                        "refactored_code": candidate_code,
                        "score": 100
                    })
                else:
                    return json.dumps({
                        "plan": [
                            "Analyze syntax tree of database handler.",
                            "Identify dynamic SQL string formatting pattern.",
                            "Formulate plan to replace raw format interpolations with prepared statement parameters."
                        ],
                        "vulnerabilities": [{
                            "severity": "High",
                            "line": 2,
                            "issue": "Direct string interpolation into database query allows SQL Injection.",
                            "fix": "Use parameterized bind variables instead of f-strings."
                        }],
                        "refactored_code": "def get_user_data(username):\n    query = \"SELECT * FROM users WHERE username = :username\"\n    return db.execute(query, {\"username\": username})",
                        "score": 40
                    })

        # 1. Mentor Agent
        if "career mentor" in prompt_lower or "candidate preparing for" in prompt_lower:
            msg = ""
            for line in prompt.splitlines():
                if "candidate message" in line.lower():
                    parts = prompt.split(line)
                    if len(parts) > 1:
                        msg = parts[1].strip()
                    break

            if msg:
                # Omit any instruction lines that follow the message in the prompt template
                for marker in ["reply directly", "be specific", "do not repeat"]:
                    if marker in msg.lower():
                        msg = msg.lower().split(marker)[0].strip()
                # strip trailing punctuation/newliness that might result from splitting
                msg = msg.split("\n")[0].strip()

            # Increment class-level counter to ensure rotating responses
            GraniteClient._mock_counter += 1

            msg_l = msg.lower()
            if any(w in msg_l for w in ["hello", "hi", "hey"]):
                greetings = [
                    "Hello! I'm your AI career mentor. I can help you review career paths, practice resume bullet formats, check your study roadmap, or share system design tips. How can I help you today?",
                    "Hi there! Great to connect. Ready to level up your career goals today? What specific doubts or topics are we focusing on?",
                    "Hello! How is your interview preparation going? Let me know if you want to run through prep strategy, discuss target roles, or check your roadmap."
                ]
                return greetings[GraniteClient._mock_counter % len(greetings)]
            
            elif any(w in msg_l for w in ["career", "path", "track", "grow", "become", "lead", "manager", "architect"]):
                career_responses = [
                    "Navigating career paths is about aligning your strengths. If you enjoy deep technical focus, the Individual Contributor (IC) track toward Architect is great. If you enjoy enabling people, tech lead or manager roles fit well. What track feels more exciting to you?",
                    "To transition to senior engineer roles, focus on scope of impact: designing systems that multiple engineers use, mentoring juniors, and aligning projects with product goals. What is your current role or target milestone?",
                    "Whether backend, frontend, or full-stack, choose the path that makes you curious. A successful career starts with solid engineering fundamentals, which make picking up new stacks easy. Let me know what technologies you are curious about!"
                ]
                return career_responses[GraniteClient._mock_counter % len(career_responses)]

            elif any(w in msg_l for w in ["doubt", "nervous", "scared", "fail", "anxious", "confidence", "stuck", "gap"]):
                doubt_responses = [
                    "It is completely normal to feel nervous or experience imposter syndrome. Even principal engineers get stuck! Focus on explaining your thought process out loud—interviewers value structured thinking over instant perfect answers.",
                    "If you encounter a question you don't know the answer to, don't guess blindly. Say: 'I haven't worked directly with that technology, but based on my knowledge of similar systems, I would approach it like this...' This shows maturity and problem-solving skills.",
                    "Confidence comes from structured preparation, not memorization. Focus on mastering templates like the STAR method for behavioral questions and requirement gathering for system design. You've got this!"
                ]
                return doubt_responses[GraniteClient._mock_counter % len(doubt_responses)]
            
            elif "resume" in msg_l or "cv" in msg_l:
                resume_tips = [
                    "A strong resume is crucial. Focus on quantifying your impact: instead of saying 'built microservices', say 'designed 5 microservices handling 10k RPS'. Would you like me to review a specific bullet point?",
                    "For tech resumes, always place your skills section near the top and align your experience bullet points with keywords from the target JD. Have you uploaded your resume to our optimizer yet?",
                    "Remember to keep your resume under two pages and focus on technologies you can confidently speak about in a live interview. What stack or projects are you currently highlighting?"
                ]
                return resume_tips[GraniteClient._mock_counter % len(resume_tips)]
            
            elif any(w in msg_l for w in ["system design", "architecture", "design", "scale", "latency", "caching"]):
                design_tips = [
                    "For system design, always start by gathering requirements (RPS, storage volume, latency SLAs). Then draft a high-level component diagram before deep diving into database indexing, replication, and caching trade-offs. What specific system are you designing?",
                    "In system design, failure modes are key. Always explain how your system handles a single point of failure (SPOF) using redundant servers, load balancers, and master-slave DB configurations. Let's design one: how would you build a URL shortener?",
                    "Remember to mention partitioning and sharding strategy when storage requirements scale. Do you have a preference between horizontal database partitioning versus vertical partitioning for high-traffic scenarios?"
                ]
                return design_tips[GraniteClient._mock_counter % len(design_tips)]
            
            elif any(w in msg_l for w in ["behavioral", "star method", "tell me about yourself", "experience"]):
                behavioral_tips = [
                    "For behavioral questions, use the STAR method: Situation, Task, Action, Result. Focus 70% of your response time on the Actions you took, and always finish with a quantified Result. Let's practice one: tell me about a time you resolved a technical conflict.",
                    "Interviewers look for leadership, conflict resolution, and ownership in behavioral answers. Try to frame challenges as learning opportunities. Tell me about a time you made a technical mistake and how you handled it.",
                    "Avoid saying 'we' too much in behavioral answers; the interviewer wants to know what YOU did. What is a complex project you owned from end to end?"
                ]
                return behavioral_tips[GraniteClient._mock_counter % len(behavioral_tips)]
            
            elif any(w in msg_l for w in ["coding", "algorithm", "leetcode", "dsa", "complexity", "big o"]):
                coding_tips = [
                    "When coding, explain your thought process out loud before writing a line. Start with a brute-force approach, state its Big-O complexity, and then optimize. Do you want to try a mock coding question?",
                    "For DSA interviews, make sure to state your assumptions, declare variable types, and write clean, modular helper functions rather than one giant block of code. What data structures are you most comfortable with?",
                    "Don't forget to walk through test cases with the interviewer before declaring your solution complete. Would you like to practice optimizing a specific sorting or searching algorithm?"
                ]
                return coding_tips[GraniteClient._mock_counter % len(coding_tips)]
            
            elif any(w in msg_l for w in ["start", "ok start", "let's begin", "let's start"]):
                start_tips = [
                    "Awesome! Let's get started. Tell me what role you're targeting (e.g., Backend Developer, Systems Engineer) and we can begin a tailored mock session or discuss your prep roadmap.",
                    "Let's dive in! What is the first topic you want to tackle: resume optimization, system design fundamentals, coding practice, or behavioral interview simulation?",
                    "Let's do it! To kick things off, what's your current experience level (Entry, Intermediate, Senior) and what target companies are you applying to?"
                ]
                return start_tips[GraniteClient._mock_counter % len(start_tips)]
            
            elif any(w in msg_l for w in ["python", "fastapi", "sqlalchemy", "django", "postgres"]):
                stack_tips = [
                    "Python backends require understanding GIL, async/await event loops, database connection pooling, and ORM N+1 query problems. Let me know if you want to drill into any of these concepts!",
                    "When using FastAPI, take advantage of Pydantic validation, dependency injection, and automatic OpenAPI docs. Do you prefer SQL database integration or async ORMs like Tortoise or SQLModel?",
                    "PostgreSQL indexing is crucial for backend developers. Make sure you understand B-Tree index structure, composite indexes, and when to use EXPLAIN ANALYZE. What's your experience optimization strategy?"
                ]
                return stack_tips[GraniteClient._mock_counter % len(stack_tips)]
            
            elif any(w in msg_l for w in ["thanks", "thank you", "perfect"]):
                thanks_tips = [
                    "You're very welcome! Keep practicing and staying structured. Let me know what else you'd like to discuss or verify next.",
                    "Glad that was helpful! Keep drilling those concepts. What else should we tackle on your career journey?",
                    "Anytime! I'm here to support you until you feel 100% ready for the real thing. What's the next step on your mind?"
                ]
                return thanks_tips[GraniteClient._mock_counter % len(thanks_tips)]
            
            else:
                clean_msg = msg[:60] + "..." if len(msg) > 60 else msg
                general_responses = [
                    f"That's a very common concern about '{clean_msg}'. As your career coach, I suggest breaking this down: focus first on mastering core engineering fundamentals (system designs, database choices), then move to behavioral structures. Don't worry about memorizing everything; showing a structured approach is what matters most.",
                    f"Regarding '{clean_msg}', my best advice is to build a consistent daily habit. Even 30 minutes of focused practice or resume optimization per day adds up faster than cramming. What's the biggest roadblock you're facing with this right now?",
                    f"When dealing with '{clean_msg}', remember that interviewers look for collaboration and adaptability as much as direct coding skills. If you get stuck in a session, explain your assumptions out loud. It shows how you work with a team.",
                    f"That's a helpful perspective about '{clean_msg}'. In my experience coaching engineering candidates, the key is aligning your past projects directly with target role requirements. Focus on demonstrating ownership and the business value of your work."
                ]
                return general_responses[GraniteClient._mock_counter % len(general_responses)]

        # 2. ResumeAgent - improve_resume
        elif "expert ats resume optimizer" in prompt_lower and "improvements to address" in prompt_lower:
            resume_text = ""
            parts = prompt.split("Resume:")
            if len(parts) > 1:
                resume_text = parts[1].strip()

            rewrites = {
                "worked on backend": "Designed and deployed containerized REST APIs with FastAPI and Docker, reducing deployment cycle times by 30%.",
                "built apis": "Architected high-throughput RESTful endpoints using FastAPI and SQLAlchemy, increasing service reliability to 99.9%.",
                "database setup": "Optimized database schema normalization and created composite index strategies in PostgreSQL, improving query response times by 40%.",
                "frontend development": "Refactored core frontend state management using React and TypeScript, boosting page responsiveness and interaction metrics by 25%.",
                "team player": "Collaborated in an agile cross-functional squad of 6 developers, driving sprint goals and leading bi-weekly system design workshops."
            }

            improved_lines = []
            changes_made = []

            for line in resume_text.splitlines():
                modified_line = line
                for weak, strong in rewrites.items():
                    if weak in modified_line.lower():
                        start_idx = modified_line.lower().find(weak)
                        if start_idx != -1:
                            end_idx = start_idx + len(weak)
                            modified_line = modified_line[:start_idx] + strong + modified_line[end_idx:]
                            changes_made.append(f"Optimized phrase '{weak}' into a quantified impact statement.")
                
                if "responsible for" in modified_line.lower():
                    start_idx = modified_line.lower().find("responsible for")
                    if start_idx != -1:
                        end_idx = start_idx + len("responsible for")
                        modified_line = modified_line[:start_idx] + "Spearheaded design and delivery of" + modified_line[end_idx:]
                        changes_made.append("Upgraded passive duty statement to active leadership verb.")
                
                improved_lines.append(modified_line)

            improved_text = "\n".join(improved_lines)

            import json
            return json.dumps({
                "improved_text": improved_text,
                "changes_made": changes_made
            })
        # ResumeAgent - analyze_resume
        elif "resume score" in prompt_lower or "ats resume optimizer" in prompt_lower or "ats resume reviewer" in prompt_lower:
            return """{
              "score": 85,
              "ats_score": 82,
              "summary": "The candidate has strong software engineering foundations with hands-on experience building APIs and database systems.",
              "resume_feedback": "The overall resume layout is professional and covers core programming concepts well, but lacks quantified metrics on past project impacts.",
              "strengths": [
                "Proficient with Python/FastAPI and database integration",
                "Solid understanding of software testing and modular architecture"
              ],
              "improvements": [
                "Quantify project impact with explicit metrics",
                "Highlight system architecture design and cloud deployments"
              ],
              "rewrite_suggestions": [
                {
                  "original": "Worked on backend APIs",
                  "rewritten": "Designed and implemented robust backend APIs using FastAPI and SQLAlchemy, increasing service reliability to 99.9%",
                  "reason": "Quantifies engineering impact and details the tech stack"
                }
              ]
            }"""

        # 3. JobDescriptionAgent (JD Analyzer)
        elif "job description (jd) analyzer" in prompt_lower or "skill gaps" in prompt_lower:
            return """{
              "skill_gaps": [
                {
                  "category": "Core Technologies",
                  "missing_skills": ["Redis Caching", "Docker", "CI/CD Pipelines"],
                  "priority": "High"
                },
                {
                  "category": "Advanced Systems",
                  "missing_skills": ["System Design", "Distributed Systems"],
                  "priority": "Medium"
                }
              ],
              "matched_skills": ["Python", "FastAPI", "SQLAlchemy"]
            }"""

        # 4. RoadmapAgent
        elif "learning roadmap tailored to" in prompt_lower or "steps" in prompt_lower:
            import re
            weeks = 8
            match = re.search(r"(\d+)-week learning roadmap", prompt_lower)
            if match:
                weeks = int(match.group(1))

            # Parse role from prompt if present
            role = "software engineer"
            for line in prompt.splitlines():
                if "role:" in line.lower() or "target role" in line.lower():
                    role = line.split(":", 1)[1].strip().lower()
                    break

            # Define topic progression maps
            syllabus_backend = [
                (
                    "API Design & RESTful Standards", 
                    "Master REST constraints, status codes, query filtering, pagination, and OpenAPI specifications.",
                    [
                        "What is the difference between PUT and PATCH, and when would you use each?",
                        "How would you design a robust API pagination strategy for a high-volume endpoint?",
                        "What are idempotency keys, and how do they ensure safe request retries in payment APIs?"
                    ]
                ),
                (
                    "Database Scaling & Indexes", 
                    "Deep dive into composite indexes, query optimization, sharding, replication, and SQL vs NoSQL trade-offs.",
                    [
                        "Explain the difference between a clustered and non-clustered index, and how they impact write operations.",
                        "How do database replica lags occur in primary-replica setups, and how do you handle read-after-write consistency?",
                        "Under what conditions is database sharding preferred over vertical scaling and replication?"
                    ]
                ),
                (
                    "Caching Strategies & Stampedes", 
                    "Master Redis cache-aside pattern, eviction policies (LRU, LFU), TTL strategies, and cache stampede mitigations.",
                    [
                        "What is cache stampede (thundering herd) and how do you mitigate it using mutual exclusion or background warming?",
                        "Compare the Cache-Aside, Write-Through, and Write-Back caching strategies.",
                        "How does Redis handle eviction when memory is full, and what is the difference between volatile-lru and allkeys-lru?"
                    ]
                ),
                (
                    "Concurrency & Thread Pools", 
                    "Understand CPU-bound vs I/O-bound tasks, multithreading, asyncio event loops, locks, and thread pool scaling.",
                    [
                        "What is the difference between a process and a thread, and how does the GIL affect concurrency in Python?",
                        "How do you identify and resolve thread deadlocks in high-concurrency systems?",
                        "Explain the event loop model in asynchronous frameworks compared to multi-threaded worker pools."
                    ]
                ),
                (
                    "Message Queues & Event-Driven Design", 
                    "Integrate RabbitMQ/Kafka, pub-sub architectures, consumer groups, message durability, and backpressure.",
                    [
                        "How does Kafka guarantee message ordering within a topic, and what happens when a consumer group rebalances?",
                        "What is the difference between at-least-once, at-most-once, and exactly-once delivery guarantees?",
                        "How do you handle consumer backpressure when message ingress rates exceed processing capabilities?"
                    ]
                ),
                (
                    "Microservices & Distributed Transactions", 
                    "Understand API gateways, service discovery, saga pattern, two-phase commits, and circuit breakers.",
                    [
                        "What is the Saga pattern, and how does it maintain data consistency compared to two-phase commits (2PC)?",
                        "How does a circuit breaker prevent cascading failures in a microservices mesh?",
                        "Compare service discovery models: client-side discovery vs server-side discovery."
                    ]
                ),
                (
                    "Containerization & Orchestration", 
                    "Learn multi-stage Docker builds, resource constraints, Kubernetes pods, services, and config maps.",
                    [
                        "Why should you use multi-stage Docker builds, and how do they impact image footprint security?",
                        "What is the difference between a Kubernetes Pod, ReplicaSet, and Deployment?",
                        "How do Kubernetes readiness probes differ from liveness probes, and why are they critical during rollouts?"
                    ]
                ),
                (
                    "High Availability & Reliability Engineering", 
                    "Study rate-limiting, load balancers, database failover, health checks, and monitoring with Prometheus/Grafana.",
                    [
                        "How would you design a distributed token-bucket rate limiter that scales across multiple servers?",
                        "What is the difference between active-passive and active-active failover strategies?",
                        "How do you monitor key metrics like latency, throughput, error rates, and saturation (Golden Signals)?"
                    ]
                )
            ]

            syllabus_frontend = [
                (
                    "Advanced JS/TS & Clean Code", 
                    "Deep dive into JS closures, prototype chains, event loop, TS advanced types (mapped, conditional, utility).",
                    [
                        "What is a closure in JavaScript, and how can it lead to memory leaks?",
                        "How does the JavaScript event loop handle call stack, microtask queue, and macrotask queue priorities?",
                        "Explain TypeScript utility types like Omit, Pick, and Exclude, and how they ensure type safety."
                    ]
                ),
                (
                    "React Architecture & Render Lifecycle", 
                    "Understand Virtual DOM, React Fiber reconciler, component mounts, hooks rendering patterns, and concurrent mode.",
                    [
                        "What is React Fiber, and how does it enable concurrent rendering and interruptible updates?",
                        "How do you prevent unnecessary re-renders in deep React component trees?",
                        "Compare React state hooks (useState, useReducer) with ref hooks (useRef) in terms of rendering triggers."
                    ]
                ),
                (
                    "Web Performance & Code Splitting", 
                    "Optimize Core Web Vitals, critical rendering path, lazy loading, dynamic import(), and bundler optimizations.",
                    [
                        "What are Core Web Vitals (LCP, FID, CLS, INP), and how do you optimize them?",
                        "How does dynamic import() enable code splitting, and how do you implement route-level lazy loading?",
                        "How do resource hints like prefetch, preload, and preconnect optimize the critical rendering path?"
                    ]
                ),
                (
                    "State Management & Data Flow", 
                    "Master local vs global states, React context, Zustand, Redux Toolkit, and atomic states like Recoil.",
                    [
                        "Compare the data flow models of Redux vs Zustand vs Recoil in state architectures.",
                        "What is prop drilling, and how does React Context API solve it? What are Context's performance trade-offs?",
                        "How do you synchronize local state changes with server database states (e.g. using React Query / SWR)?"
                    ]
                ),
                (
                    "Browser APIs & Security", 
                    "Learn about service workers, offline storage (IndexedDB), CORS policy, XSS, CSRF, and CSP headers.",
                    [
                        "How does a Service Worker enable offline capabilities and background sync in Progressive Web Apps?",
                        "Explain cross-site scripting (XSS) and cross-site request forgery (CSRF), and how modern frontends defend against them.",
                        "What is Content Security Policy (CSP), and how do nonce tokens secure inline scripts?"
                    ]
                ),
                (
                    "CSS layouts & Responsive Design", 
                    "Master Flexbox, CSS Grid, container queries, Tailwind utility classes, and CSS-in-JS variables.",
                    [
                        "Compare CSS Flexbox (1D) vs CSS Grid (2D), and when is each layout model preferred?",
                        "How do CSS container queries differ from traditional viewport-based media queries?",
                        "What are the pros and cons of utility-first CSS frameworks like Tailwind compared to CSS Modules?"
                    ]
                ),
                (
                    "Testing & CI/CD for Frontend", 
                    "Write unit tests with Vitest, component tests with Testing Library, and E2E automation with Playwright.",
                    [
                        "What is the difference between unit testing, component testing, and end-to-end (E2E) testing?",
                        "How do you mock API calls in component tests using tools like Mock Service Worker (MSW)?",
                        "What are the key stages of a frontend deployment pipeline (linting, build verification, asset hosting)?"
                    ]
                ),
                (
                    "SSR, SSG & Modern Frameworks", 
                    "Master Next.js App Router, server components, static generation, dynamic hydration, and edge middleware.",
                    [
                        "Compare Server-Side Rendering (SSR), Static Site Generation (SSG), and Client-Side Rendering (CSR).",
                        "How do React Server Components (RSC) differ from standard client components, and how do they reduce bundle sizes?",
                        "What is progressive hydration, and how does it optimize Time to Interactive (TTI)?"
                    ]
                )
            ]

            syllabus_ds = [
                (
                    "Feature Engineering & Analytics", 
                    "Clean datasets, impute missing values, scale variables, and run exploratory data analyses.",
                    [
                        "How do you handle collinear features in linear regression models?",
                        "Explain the difference between L1 (Lasso) and L2 (Ridge) regularization.",
                        "What is the target leakage in ML pipelines, and how do you prevent it?"
                    ]
                ),
                (
                    "Supervised & Unsupervised Learning", 
                    "Compare linear/logistic regression, tree-based models, clustering techniques, and metrics like F1 and ROC-AUC.",
                    [
                        "Why is the ROC-AUC score preferred over classification accuracy for imbalanced datasets?",
                        "How does a Random Forest model determine feature importances?",
                        "What are the differences between K-Means and DBSCAN clustering algorithms?"
                    ]
                ),
                (
                    "Deep Learning & Frameworks", 
                    "Build neural networks using PyTorch/TensorFlow, optimize weights, prevent overfitting, and use transfer learning.",
                    [
                        "What is the vanishing gradient problem, and how do activation functions like ReLU mitigate it?",
                        "Explain the role of Dropout layers during training vs inference.",
                        "What is the difference between SGD, Adam, and RMSprop optimizers?"
                    ]
                ),
                (
                    "LLMs & NLP Tuning", 
                    "Learn transformer architectures, tokenize text corpora, vector embeddings, semantic search, and prompt engineering.",
                    [
                        "Explain the self-attention mechanism in Transformer architectures.",
                        "What is the difference between fine-tuning a model and utilizing RAG templates?",
                        "How do temperature and top-p sampling impact text generation output randomness?"
                    ]
                ),
                (
                    "Model Deployment & APIs", 
                    "Containerize machine learning models using Docker, build FastAPI endpoints, and serve inference results.",
                    [
                        "How do you structure a high-throughput inference API for ML models using FastAPI?",
                        "What is model drift, and how do you monitor performance changes in production?",
                        "Under what scenarios would you choose batch prediction over real-time API inference?"
                    ]
                ),
                (
                    "Big Data & Cloud Pipelines", 
                    "Write PySpark data transformations, build ETL pipelines, and query datasets using Snowflake/Redshift.",
                    [
                        "How does PySpark manage data partitioning and shuffle operations during joins?",
                        "Explain the difference between ETL and ELT pipelines, and when to use Snowflake vs Redshift.",
                        "How do you handle schema evolution in streaming data lakes?"
                    ]
                ),
                (
                    "A/B Testing & Experimentation", 
                    "Formulate null hypotheses, calculate sample sizes, run power analyses, and evaluate statistical significance.",
                    [
                        "How do you determine the required sample size for an A/B test based on statistical power?",
                        "What is the p-value, and what does it mean to achieve a 95% confidence interval?",
                        "How do you identify and control for skew and bias in user assignment metrics?"
                    ]
                ),
                (
                    "MLOps & Lifecycle Monitoring", 
                    "Set up MLflow model registries, track experiments, detect data drift, and automate pipeline trigger schedules.",
                    [
                        "What are the core components of an MLOps pipeline, and how does model registry versioning work?",
                        "How do you detect feature drift in a model's inputs over time?",
                        "What is continuous training (CT) and when should it be automated?"
                    ]
                )
            ]

            syllabus_default = [
                (
                    "Computer Science Fundamentals", 
                    "Review Big O complexity, dynamic programming, sorting/searching, and basic memory management.",
                    [
                        "What is the difference between quicksort and mergesort in terms of time and space complexity?",
                        "Explain how dynamic programming optimization differs from memoization techniques.",
                        "What is a pointer, and how does garbage collection manage reference counts in modern runtimes?"
                    ]
                ),
                (
                    "Data Structures in Practice", 
                    "Master arrays, hash maps, linked lists, trees, and graphs, focusing on traversal algorithms.",
                    [
                        "How do hash map collisions occur, and how do separate chaining and open addressing resolve them?",
                        "What is the difference between depth-first search (DFS) and breadth-first search (BFS) on graphs?",
                        "What is a binary search tree, and how do you balance a tree in-place?"
                    ]
                ),
                (
                    "Design Patterns & Architecture", 
                    "Study creational, structural, and behavioral patterns, alongside SOLID engineering principles.",
                    [
                        "Explain the Single Responsibility Principle and the Dependency Inversion Principle.",
                        "What is the Singleton pattern, and how do you implement a thread-safe singleton?",
                        "Compare the Strategy design pattern with the State design pattern."
                    ]
                ),
                (
                    "System Design Basics", 
                    "Understand vertical vs horizontal scaling, load balancing, DNS routing, and monolithic vs microservices.",
                    [
                        "What is the difference between vertical scaling and horizontal scaling?",
                        "How does a DNS query resolution loop execute from client to root server?",
                        "What is the role of a reverse proxy vs a load balancer?"
                    ]
                ),
                (
                    "Database & Transactions", 
                    "Master ACID guarantees, isolation levels, database normalization, and query performance optimizations.",
                    [
                        "What are ACID transactions, and what is the role of Write-Ahead Logging (WAL)?",
                        "Explain the difference between Read Committed and Serializable transaction isolation levels.",
                        "Under what scenarios is a NoSQL document database preferred over a normalized relational database?"
                    ]
                ),
                (
                    "Networking & Protocols", 
                    "Deep dive into HTTP/HTTPS, TCP/IP, websockets, DNS lookups, and load balancer configurations.",
                    [
                        "How does a TCP 3-way handshake establish a connection, and how does TLS handshake secure it?",
                        "Explain how WebSockets enable full-duplex communication over a single TCP connection.",
                        "What is HTTP/2 multiplexing, and how does it optimize page asset loading?"
                    ]
                ),
                (
                    "CI/CD & Version Control", 
                    "Master advanced Git workflows (rebase, cherry-pick), automation pipelines, and infrastructure deployment.",
                    [
                        "Compare Git merge vs Git rebase workflows, and when to use each.",
                        "How do you design a secure, automated CI/CD pipeline that enforces testing gates?",
                        "What is Git cherry-pick, and under what conditions is it used?"
                    ]
                ),
                (
                    "Security & Reliability", 
                    "Learn about encryption, HTTPS, OAuth2 authorization flows, rate limiting, and system failure recovery.",
                    [
                        "What is the difference between symmetric and asymmetric encryption, and how are they used in SSL/TLS?",
                        "Explain the OAuth2 authorization code grant flow with PKCE.",
                        "How does a token-bucket rate limiter enforce traffic bounds on APIs?"
                    ]
                )
            ]

            active_syllabus = syllabus_default
            if "backend" in role:
                active_syllabus = syllabus_backend
            elif "frontend" in role or "ui" in role or "react" in role:
                active_syllabus = syllabus_frontend
            elif "data scientist" in role or "machine learning" in role or "ds" in role or "ml" in role:
                active_syllabus = syllabus_ds

            steps = []
            for i in range(1, weeks + 1):
                title, desc, questions = active_syllabus[(i - 1) % len(active_syllabus)]
                steps.append({
                    "step_number": i,
                    "title": title,
                    "description": desc,
                    "estimated_hours": 15,
                    "questions": questions
                })

            import json
            return json.dumps({"steps": steps})

        # 5. NotesAgent - core blocks
        elif "computer science tutor" in prompt_lower or "study notes" in prompt_lower:
            topic = "this topic"
            lines = prompt.splitlines()
            for idx, line in enumerate(lines):
                line_stripped = line.strip()
                if line_stripped.lower().startswith("topic:"):
                    parts = line_stripped.split(":", 1)
                    if len(parts) > 1 and parts[1].strip():
                        topic = parts[1].strip()
                    elif idx + 1 < len(lines):
                        topic = lines[idx + 1].strip()
                    break
                elif "write study notes on" in line.lower():
                    parts = line.split('"')
                    if len(parts) > 1:
                        topic = parts[1].strip()
                    break

            topic = topic.replace('"', '').replace("'", "").strip()

            topic_clean = topic.lower()

            notes_db = {
                "cache": [
                    "### Overview of Caching\nCaching is the process of storing copies of data in a high-speed data storage layer (like RAM) to serve future requests faster. It is primarily used to reduce read latency and decrease load on primary databases.",
                    "### Key Caching Paradigms\n- **Cache-Aside**: The application queries the cache. If a cache miss occurs, it queries the database and writes the data to the cache.\n- **Eviction Policies**: When RAM is full, the cache removes old data using policies like Least Recently Used (LRU) or Least Frequently Used (LFU).\n- **Cache Consistency**: Ensuring the cache reflects database updates. Solved using Write-Through or TTL (Time-To-Live) expiration.",
                    "### Interview Tips\n- Explain the **Cache Stampede** problem: when many concurrent requests cache-miss at once and overwhelm the database. Solve it using locking or pre-populating keys."
                ],
                "database": [
                    "### Overview of Databases\nDatabases are organized collections of data, generally split into Relational (SQL) and Non-Relational (NoSQL) stores. Selecting the right database depends on consistency needs, query patterns, and write throughput.",
                    "### Key DBMS Concepts\n- **ACID Transactions**: Atomicity, Consistency, Isolation, and Durability ensure reliable transaction execution.\n- **Indexes**: Data structures (like B-Trees) that speed up reads at the cost of slower writes.\n- **Scaling**: Scaling databases horizontally via Sharding/Partitioning, or vertically by upgrading hardware.",
                    "### Interview Tips\n- Be prepared to discuss **Isolation Levels** (Read Uncommitted, Read Committed, Repeatable Read, Serializable) and how they prevent dirty reads or phantom reads."
                ],
                "sql": [
                    "### Overview of SQL Databases\nStructured Query Language (SQL) databases are relational databases that store structured data in rows and tables. They enforce schema constraints and support complex multi-table joins.",
                    "### Relational Concepts\n- **Foreign Keys & Joins**: Establishing relations between tables using primary and foreign keys, joining them using INNER, LEFT, or RIGHT joins.\n- **Normalization**: Reducing data redundancy by organizing fields into normal forms (1NF, 2NF, 3NF).\n- **Query Optimization**: Using EXPLAIN/EXPLAIN ANALYZE to locate table scans and optimizing queries with appropriate indexes.",
                    "### Interview Tips\n- Explain the trade-offs of normalization: while it reduces storage requirements, it can slow down complex analytical queries due to multi-table joins."
                ],
                "concurrency": [
                    "### Overview of Concurrency\nConcurrency is the ability to execute multiple execution paths (threads or tasks) out of order or in parallel. It is key for high-concurrency APIs but introduces thread-safety challenges.",
                    "### Core Concurrency Challenges\n- **Race Conditions**: When multiple threads read and write shared state simultaneously without proper synchronization.\n- **Locks and Semaphores**: Synchronization tools. Mutexes ensure mutual exclusion; semaphores count available resource permits.\n- **Deadlocks**: When two or more threads are blocked forever, each waiting for a lock held by the other.",
                    "### Interview Tips\n- In Python, discuss the Global Interpreter Lock (GIL), which prevents multiple native threads from executing Python bytecodes at once, necessitating multiprocessing for CPU-bound tasks."
                ],
                "microservice": [
                    "### Overview of Microservices\nMicroservices architecture structures an application as a collection of loosely coupled, independently deployable services. It enhances team autonomy but increases network and operational complexity.",
                    "### Architectural Considerations\n- **Service Communication**: Can be synchronous (HTTP/gRPC) or asynchronous (message queues like RabbitMQ or Kafka).\n- **Service Discovery**: Resolving dynamic service addresses using registries like Consul or Eureka.\n- **Distributed Transactions**: Handled using patterns like Saga (compensating transactions) or 2-Phase Commit.",
                    "### Interview Tips\n- Always emphasize observability: distributed tracing (Jaeger/Zipkin) and centralized logging are non-negotiable for debugging microservice chains."
                ],
                "api": [
                    "### Overview of API Design\nApplication Programming Interfaces (APIs) are contracts that allow systems to communicate. Designing high-quality REST or gRPC APIs is key to backend engineering.",
                    "### RESTful Best Practices\n- **HTTP Verbs**: GET for reads, POST for creation, PUT for replacement, PATCH for updates, DELETE for removal.\n- **Status Codes**: 200 OK, 201 Created, 400 Bad Request, 401 Unauthenticated, 403 Forbidden, 404 Not Found, 500 Internal Error.\n- **Idempotency**: Ensuring making the same request multiple times has the same side-effects as a single request (e.g. GET, PUT, DELETE are idempotent).",
                    "### Interview Tips\n- Detail how you handle API versioning (URI versioning like `/v1/`, header versioning) and pagination for large list endpoints to protect memory."
                ],
                "ai": [
                    "### Overview of AI and LLMs\nArtificial Intelligence, specifically LLMs (Large Language Models) like Granite, has revolutionized software by enabling natural language understanding, reasoning, and code generation.",
                    "### LLM Integration Paradigms\n- **Retrieval-Augmented Generation (RAG)**: Feeding external vector search results into the LLM prompt to ground its answers in private data.\n- **Fine-Tuning**: Re-training existing weights on a custom dataset to adapt the model to specialized domains.\n- **Structured Output**: Enforcing JSON schemas (using tools like Pydantic) so model outputs can be parsed programmatically.",
                    "### Interview Tips\n- Mention latency mitigation strategies: using streaming responses (WebSockets/SSE), caching embeddings, or using smaller specialized models (like Granite-8b vs larger models)."
                ],
                "technical terms": [
                    "### Overview of Technical Terminology\nMastering technical terminology is essential for communicating clearly with engineering teams and interviewers. It shows you understand industry standards and can discuss system constraints using standard vocabulary.",
                    "### Crucial Software Engineering Terms\n- **Idempotency**: Ensuring an operation can be performed multiple times without changing the result beyond the first application.\n- **Statelessness**: Designing services so they do not store user session data on the server, making them trivially easy to scale horizontally.\n- **SLA/SLO/SLI**: Service Level Agreements, Objectives, and Indicators that measure system reliability and performance.",
                    "### Interview Tips\n- Avoid using buzzwords without understanding them. If you mention a term like 'thread-safety' or 'eventual consistency', be prepared to explain the exact locking or replication mechanism behind it."
                ],
                "architectural knowledge": [
                    "### Overview of System Architecture\nArchitectural knowledge involves understanding how different software components, databases, and network layers coordinate to build reliable, high-performance systems at scale.",
                    "### Architectural Design Patterns\n- **Layered (n-tier) Architecture**: Separating presentation, business logic, and database access into clean, independent tiers.\n- **Event-Driven Architecture**: Decoupling services using asynchronous events and message brokers to improve scalability and system resilience.\n- **Service-Oriented & Microservices**: Building modular services that own their own databases and communicate via gRPC or REST APIs.",
                    "### Interview Tips\n- When asked architectural questions, always sketch out the data flow from client to database, and discuss how you would design for high availability and prevent single points of failure (SPOFs)."
                ]
            }

            if not any(k in topic_clean for k in notes_db):
                topic_val = sum(ord(c) for c in topic_clean) % 3
                if topic_val == 0:
                    content1 = f"### Exploring {topic.capitalize()}\n{topic.capitalize()} represents a core component of modern software engineering. It defines how data streams, objects, or interfaces interact across the system."
                    content2 = f"### Core Pillars of {topic.capitalize()}\n- **Modular Integration**: Ensuring components are decoupled and follow solid interface boundaries.\n- **Efficiency**: Reducing memory footprints and CPU runtime cycles.\n- **Error Resilience**: Gracefully handling exceptions and input boundary errors."
                    content3 = f"### Expert Interview Guidance\n- Focus on clean code standards: Explain how you would write unit tests for your {topic} logic to verify coverage."
                elif topic_val == 1:
                    content1 = f"### Guide to {topic.capitalize()} Best Practices\nProper configuration and architecture of {topic} is critical to preventing latency spikes and resource starvation in distributed environments."
                    content2 = f"### Implementation Considerations\n- **Scalability Path**: Scaling the throughput dynamically under high concurrent connection loads.\n- **State Management**: Knowing when to store state locally versus using a centralized storage layer.\n- **Resource Cleanup**: Ensuring connection sockets, database handles, and temporary buffers are cleaned up."
                    content3 = f"### Expert Interview Guidance\n- When asked about {topic}, walk the interviewer through the setup complexity and mention how you monitor throughput metrics."
                else:
                    content1 = f"### Deep Dive: {topic.capitalize()}\nThis section focuses on the operational details, common configuration patterns, and production challenges when deploying {topic}."
                    content2 = f"### Critical Aspects\n- **Latency Profiles**: Analyzing read and write latency patterns under simulated peak traffic.\n- **Security Posture**: Enforcing authorization boundaries and sanitizing parameters passed to {topic}.\n- **Configuration Drift**: Avoiding inconsistent environmental settings across staging and production."
                    content3 = f"### Expert Interview Guidance\n- Emphasize performance trade-offs: Never suggest {topic} is free. Always define the architectural complexity overhead."

                blocks = [
                    {"type": "text", "content": content1},
                    {"type": "text", "content": content2},
                    {"type": "text", "content": content3}
                ]
            else:
                matched_key = next(k for k in notes_db if k in topic_clean)
                blocks = [
                    {"type": "text", "content": notes_db[matched_key][0]},
                    {"type": "text", "content": notes_db[matched_key][1]},
                    {"type": "text", "content": notes_db[matched_key][2]}
                ]

            import json
            return json.dumps({"blocks": blocks})

        # 5.1 NotesAgent - supplement block (diagram or exercise)
        elif "mermaid" in prompt_lower or "worked example" in prompt_lower or "practice problem" in prompt_lower:
            topic = "this topic"
            for line in prompt.splitlines():
                if line.strip().lower().startswith("topic:"):
                    topic = line.split(":", 1)[1].strip()
                    break

            topic_clean = topic.lower()

            if "mermaid" in prompt_lower or "diagram" in prompt_lower:
                if "cache" in topic_clean or "redis" in topic_clean:
                    flow = "graph TD\n    A[Client] -->|1. Get Data| B(Redis Cache)\n    B -->|2. Cache Hit| A\n    B -->|3. Cache Miss| C(Database)\n    C -->|4. Return Data| B\n    B -->|5. Return Data| A"
                elif "database" in topic_clean or "sql" in topic_clean:
                    flow = "graph TD\n    A[Write Request] --> B[Primary Database]\n    B -->|Async Replication| C[Read Replica 1]\n    B -->|Async Replication| D[Read Replica 2]\n    E[Read Request] --> F[Load Balancer]\n    F --> C\n    F --> D"
                elif "microservice" in topic_clean:
                    flow = "graph TD\n    A[User Request] --> B[API Gateway]\n    B --> C[User Service]\n    B --> D[Order Service]\n    D -->|Publish Event| E[Kafka Broker]\n    E -->|Subscribe Event| F[Notification Service]"
                elif "ai" in topic_clean:
                    flow = "graph TD\n    A[User Query] --> B[Embeddings Generator]\n    B --> C[Vector Database Lookup]\n    C -->|Relevant Context| D[Prompt Enhancer]\n    D -->|Rich Prompt| E[LLM/Granite]\n    E -->|Generated Answer| F[User Response]"
                else:
                    flow = "graph TD\n    A[Client Request] --> B[Load Balancer]\n    B --> C[Application Server]\n    C --> D[Database]"

                mermaid_diagram = f"### System Data Flow ({topic.capitalize()})\n\n```mermaid\n{flow}\n```"
                import json
                return json.dumps({"content": mermaid_diagram})
            else:
                if "cache" in topic_clean or "redis" in topic_clean:
                    exercise = "### Hands-On Exercise: Designing Cache Invalidation\n\n**Problem Statement**:\nAssume you have a product details page with 10k RPS. Database queries take 150ms. You decide to cache details in Redis with a 1-hour TTL. How do you handle update events without stale reads?\n\n**Solution Steps**:\n1. Implement a **Write-Through** pattern: updates write to DB first, then invalidates/updates the cache key.\n2. Add a distributed lock to prevent multiple threads from querying the DB simultaneously on a cache miss (solving Cache Stampede).\n3. Set a randomized jitter (+/- 5%) on TTLs so keys don't expire all at once."
                elif "database" in topic_clean or "sql" in topic_clean:
                    exercise = "### Hands-On Exercise: Database Query Optimization\n\n**Problem Statement**:\nA users query `SELECT * FROM users WHERE status = 'active' ORDER BY created_at DESC LIMIT 20` is running slow on a table of 10M rows. How do you optimize it?\n\n**Solution Steps**:\n1. Run `EXPLAIN ANALYZE` to check for Table Scans.\n2. Create a composite index: `CREATE INDEX idx_users_status_created ON users(status, created_at DESC)`.\n3. Verify the database optimizer uses Index Scan instead of full table scan."
                elif "ai" in topic_clean:
                    exercise = "### Hands-On Exercise: Vector Search Optimization\n\n**Problem Statement**:\nYour RAG pipeline fetches 10 documents for context, but Granite's context window is overloaded, causing slower inference. How do you optimize it?\n\n**Solution Steps**:\n1. Implement **Reranking** (using Cohere/Cross-Encoder) to filter the top 10 down to the top 3 most relevant documents.\n2. Split documents into smaller semantic chunks (e.g. 500 characters with 50-character overlap) rather than entire paragraphs.\n3. Embed metadata filters to query only relevant subcategories."
                else:
                    exercise = f"### Hands-On Exercise: {topic.capitalize()} Walkthrough\n\n**Problem Statement**:\nDesign a basic implementation or trace the execution flow of a component using {topic} under a peak load of 5,000 requests per second with a latency SLA of under 50ms.\n\n**Step-by-Step Solution**:\n1. Determine the resource constraints (memory, CPU, IOPS) under simulated load.\n2. Add clustering or replication to distribute load horizontally.\n3. Set up appropriate rate limiting to prevent resource starvation."

                import json
                return json.dumps({"content": exercise})

        # 6. Evaluation Agent & Combined WebSocket Eval
        elif "technical_score" in prompt_lower:
            q = ""
            ans = ""
            for line in prompt.splitlines():
                if "question:" in line.lower():
                    parts = prompt.split(line)
                    if len(parts) > 1:
                        q_block = parts[1]
                        if "candidate answer" in q_block.lower():
                            q = q_block.lower().split("candidate answer")[0].strip()
                        else:
                            q = q_block.strip()
                elif "candidate answer:" in line.lower() or "candidate answered:" in line.lower():
                    parts = prompt.split(line)
                    if len(parts) > 1:
                        ans = parts[1].strip()
                    break

            if ans:
                for marker in ["respond with", "strict json", "rules for"]:
                    if marker in ans.lower():
                        ans = ans.lower().split(marker)[0].strip()

            q_clean = q.lower()
            ans_clean = ans.lower()
            
            # Define topic-specific keywords covering all core competencies
            topic_keywords = {
                "database": ["index", "query", "sql", "nosql", "postgres", "mongodb", "acid", "transaction", "scale", "normalization", "join", "schema", "dbms"],
                "index": ["b-tree", "hash", "scan", "lookup", "composite", "primary", "secondary", "write", "read"],
                "cache": ["redis", "memcached", "eviction", "ttl", "hit", "miss", "consistency", "invalidation", "stampede"],
                "api": ["rest", "fastapi", "http", "endpoint", "status", "json", "request", "response", "latency", "grpc"],
                "python": ["gil", "async", "await", "thread", "process", "memory", "decorator", "generator", "yield", "list", "dict", "tuple"],
                "java": ["jvm", "garbage", "collection", "multithreading", "oop", "interface", "class", "inheritance", "polymorphism", "encapsulation"],
                "concurrency": ["thread", "lock", "asyncio", "semaphore", "race", "deadlock", "process", "safety", "mutex", "synchronized"],
                "microservice": ["service", "communication", "grpc", "event", "kafka", "queue", "discovery", "latency"],
                "dsa": ["array", "list", "stack", "queue", "tree", "graph", "heap", "hash", "binary", "search", "sort", "complexity", "time", "space", "lifo", "fifo"],
                "oop": ["class", "object", "inheritance", "polymorphism", "encapsulation", "abstraction", "method", "override", "overload"],
                "os": ["process", "thread", "scheduling", "deadlock", "memory", "paging", "virtual", "kernel", "syscall"],
                "cn": ["tcp", "udp", "ip", "http", "dns", "routing", "socket", "packet", "handshake", "layer"],
                "ml": ["model", "feature", "training", "supervised", "unsupervised", "regression", "classification", "neural", "network", "gradient", "loss"],
                "system design": ["scaling", "load", "balancer", "sharding", "replication", "availability", "partition", "latency", "throughput"]
            }

            # Gather keywords based on topics in the question
            matched_keywords = []
            for topic, keywords in topic_keywords.items():
                if topic in q_clean:
                    matched_keywords.extend(keywords)

            # Fallback to general CS keywords if question has no specific keywords mapped
            if not matched_keywords:
                matched_keywords = [
                    "class", "object", "array", "list", "tree", "graph", "hash", "query", "sql", "index", 
                    "process", "thread", "memory", "tcp", "ip", "http", "model", "data", "scale", "load",
                    "cache", "redis", "complexity", "time", "space", "o(n)", "constant", "linear",
                    "algorithm", "function", "variable", "pointer", "reference"
                ]

            general_quality_terms = [
                "trade-off", "performance", "scalability", "latency", "throughput", "redundancy",
                "bottleneck", "optimization", "monitoring", "metric", "consistency", "reliability",
                "robust", "security", "thread-safe", "principle", "implementation"
            ]

            hits = 0
            for kw in matched_keywords:
                if kw in ans_clean:
                    hits += 1

            quality_hits = 0
            for term in general_quality_terms:
                if term in ans_clean:
                    quality_hits += 1

            words = ans.split()
            word_count = len(words)

            is_relevant = True
            if matched_keywords and hits == 0 and not any(w in ans_clean for w in ["hello", "hi", "introduce", "myself", "experience"]):
                # Allow soft matches or general comments
                if word_count < 10:
                    is_relevant = False

            if word_count < 3:
                tech = 30.0
                comm = 40.0
                behav = 40.0
                conf = 40.0
                star = 30.0
                feedback = "The answer is too short to evaluate. Please provide a more complete explanation."
                weak = ["Technical Detail", "Completeness"]
            elif not is_relevant:
                tech = 40.0
                comm = 50.0
                behav = 50.0
                conf = 55.0
                star = 40.0
                feedback = "Your answer doesn't seem directly relevant to the question asked. Please address the question's specific subject matter directly."
                weak = ["Relevance", "Focus"]
            else:
                # Base scoring heavily dependent on depth (word count) and CS hits
                tech_base = 55.0 + (hits * 6.0) + (quality_hits * 5.0)
                if word_count > 20:
                    tech_base += 15.0
                if word_count > 40:
                    tech_base += 15.0
                tech = max(50.0, min(100.0, tech_base))

                comm_base = 60.0 + (word_count * 0.2) + (quality_hits * 3.0)
                comm = max(50.0, min(95.0, comm_base))

                behav_base = 55.0 + (quality_hits * 4.0)
                behav = max(50.0, min(90.0, behav_base))

                conf_base = 60.0 + (hits * 4.0) + (quality_hits * 3.0)
                conf = max(55.0, min(95.0, conf_base))

                star_base = 50.0 + (quality_hits * 5.0)
                star = max(45.0, min(90.0, star_base))

                if hits == 0 and quality_hits == 0:
                    feedback = "You gave a general answer, but it lacks specific technical terms or details related to the question. Try mentioning specific technologies, components, or metrics."
                    weak = ["Technical Terms", "Architectural Knowledge"]
                elif hits < 2 or quality_hits < 1:
                    feedback = "Good start! You mentioned some relevant concepts, but you should explain the trade-offs, architecture design, and scalability aspects in more detail to get a higher score."
                    weak = ["Trade-offs & Constraints"]
                else:
                    feedback = "Excellent answer! You directly addressed the question using precise technical terminology and showed a clear understanding of trade-offs and implementation details."
                    weak = []

            # Parse Role from prompt to customize next follow-up question
            role = "Backend Engineer"
            for line in prompt.splitlines():
                if "role:" in line.lower():
                    parts = prompt.split(line)
                    if len(parts) > 1:
                        lines_after = parts[1].strip().splitlines()
                        if lines_after:
                            role = lines_after[0].strip()
                    break

            role_lower = role.lower()
            if "backend" in role_lower:
                next_q = "That is a solid approach to backend scaling. How would you handle cache invalidation and ensure strong data consistency across your replicas under a high write load?"
            elif "frontend" in role_lower or "ui" in role_lower or "react" in role_lower:
                next_q = "Great points on bundle splitting and lazy loading. How would you manage complex client-side state and prevent unnecessary component re-renders when receiving real-time updates?"
            elif "data scientist" in role_lower or "machine learning" in role_lower or "ds" in role_lower or "ml" in role_lower:
                next_q = "That validation strategy makes sense. Once deployed, how do you handle scaling feature engineering pipelines to process millions of incoming records per hour?"
            elif "devops" in role_lower or "infrastructure" in role_lower or "sre" in role_lower:
                next_q = "Excellent. How would you handle stateful databases and data schema migrations during such a blue-green switchover without dropping ongoing user sessions?"
            elif "ios" in role_lower or "mobile" in role_lower or "android" in role_lower:
                next_q = "Good explanation of reference cycles and memory management. How would you implement an offline-first caching mechanism to ensure a seamless user experience under poor network conditions?"
            elif "manager" in role_lower or "lead" in role_lower:
                next_q = "That's a sound leadership philosophy. How do you measure developer velocity and maintain high code quality standards without causing developer burnout?"
            else:
                next_q = f"That makes sense. Can you build on that by discussing the scalability implications of your design and how you would monitor it in production?"

            overall = round((tech + comm + behav + conf + star) / 5.0, 1)

            import json
            return json.dumps({
                "technical_score": tech,
                "communication_score": comm,
                "behavioral_score": behav,
                "confidence_score": conf,
                "star_score": star,
                "overall_score": overall,
                "feedback": feedback,
                "weak_topics": weak,
                "mode": "standard",
                "next_question": next_q
            })

        # 6b. InterviewAgent - Simpler / Prerequisite Question
        elif "lower the difficulty" in prompt_lower or "simpler" in prompt_lower:
            return "Since we are adjusting the difficulty, let's look at the basic foundations. Can you explain the fundamental concept behind this topic in your own words?"

        # 7. InterviewAgent - Devil's Advocate
        elif "devil's advocate" in prompt_lower:
            role = "Backend Engineer"
            for line in prompt.splitlines():
                if "role:" in line.lower():
                    parts = prompt.split(line)
                    if len(parts) > 1:
                        lines_after = parts[1].strip().splitlines()
                        if lines_after:
                            role = lines_after[0].strip()
                    break

            role_lower = role.lower()
            if "backend" in role_lower:
                return "That's a very solid backend design. However, what happens if the network latency between your application server and database spikes? How would your proposed caching architecture handle a cache stampede in that scenario?"
            elif "frontend" in role_lower or "ui" in role_lower or "react" in role_lower:
                return "Your component hierarchy and bundle optimization look clean. But how would your UI handle a complete network dropout mid-transaction? What optimistic UI updates or retry loops would you use?"
            else:
                return "Your proposed solution covers the happy path. But how does this scale if your payload volume or transaction frequency increases 10x? What latency bottlenecks do you anticipate?"
        else:
            role = "Software Engineer"
            week = 1
            topic = ""
            prompt_lines = prompt.splitlines()
            for idx, line in enumerate(prompt_lines):
                line_stripped = line.strip()
                if line_stripped.lower() == "role:":
                    if idx + 1 < len(prompt_lines):
                        role = prompt_lines[idx + 1].strip()
                elif line_stripped.lower() == "week:":
                    if idx + 1 < len(prompt_lines) and prompt_lines[idx + 1].strip().isdigit():
                        week = int(prompt_lines[idx + 1].strip())
                elif line_stripped.lower() == "topic:":
                    if idx + 1 < len(prompt_lines):
                        topic = prompt_lines[idx + 1].strip()

            role_lower = role.lower()
            topic_lower = topic.lower()
            difficulty = "Easy" if week <= 2 else "Medium" if week <= 5 else "Hard"

            q = f"Welcome to your {role} mock interview! This is a {difficulty} question for Week {week} on the topic of {topic or 'Technical Foundations'}. Can you explain a challenging problem you solved in this domain and the trade-offs you considered?"

            if "backend" in role_lower:
                if "api design" in topic_lower or "rest" in topic_lower:
                    if difficulty == "Easy":
                        q = "Welcome to your Backend mock interview! Let's start with basic REST concepts. Could you explain the difference between PUT and PATCH, and what HTTP status codes you would return for successful resource creation vs validation failure?"
                    elif difficulty == "Medium":
                        q = "Welcome to your Backend mock interview! Let's talk about API design. How would you design a scalable API pagination strategy (offset vs cursor-based) for a high-throughput endpoint?"
                    else:
                        q = "Welcome to your Backend mock interview! Let's discuss advanced API architectures. How would you implement rate limiting (token bucket vs sliding window) across a distributed cluster of API instances?"
                elif "database" in topic_lower or "indexing" in topic_lower:
                    if difficulty == "Easy":
                        q = "Welcome to your Backend mock interview! Let's start with database basics. What is database normalization, and when would you choose to denormalize your schemas?"
                    elif difficulty == "Medium":
                        q = "Welcome to your Backend mock interview! Let's discuss indexes. How do composite indexes work in SQL databases, and how does the column order affect query execution?"
                    else:
                        q = "Welcome to your Backend mock interview! Let's look at database scaling. How do you design write-heavy database sharding keys, and how do you handle cross-shard query joins?"
                elif "caching" in topic_lower or "cache" in topic_lower:
                    if difficulty == "Easy":
                        q = "Welcome to your Backend mock interview! Let's talk about caching. What is the difference between local memory caching and distributed caching like Redis?"
                    elif difficulty == "Medium":
                        q = "Welcome to your Backend mock interview! Let's discuss caching strategies. Could you explain the cache-aside pattern and how you choose key TTL values?"
                    else:
                        q = "Welcome to your Backend mock interview! Let's look at cache stampedes. How do you design high-throughput cache invalidation systems and prevent database crashes when a hot key expires?"
                elif "concurrency" in topic_lower or "thread" in topic_lower:
                    if difficulty == "Easy":
                        q = "Welcome to your Backend mock interview! Let's talk about execution threads. What is the difference between CPU-bound and I/O-bound tasks in a server context?"
                    elif difficulty == "Medium":
                        q = "Welcome to your Backend mock interview! Let's discuss async event loops. How does single-threaded concurrency (like Node.js or Python asyncio) handle thousands of concurrent requests?"
                    else:
                        q = "Welcome to your Backend mock interview! Let's look at deadlocks. How do database locks (optimistic vs pessimistic concurrency control) affect throughput, and how do you resolve circular deadlock dependencies?"
                elif "message queue" in topic_lower or "event-driven" in topic_lower:
                    if difficulty == "Easy":
                        q = "Welcome to your Backend mock interview! Let's start with message exchanges. What is the main difference between synchronous HTTP calls and asynchronous message queues?"
                    elif difficulty == "Medium":
                        q = "Welcome to your Backend mock interview! Let's talk about pub-sub. How do consumer groups in message brokers like Kafka distribute payloads while maintaining order?"
                    else:
                        q = "Welcome to your Backend mock interview! Let's look at delivery guarantees. How do you design an idempotent consumer that processes messages exactly-once even under message duplication?"
                elif "microservices" in topic_lower or "transaction" in topic_lower:
                    if difficulty == "Easy":
                        q = "Welcome to your Backend mock interview! Let's start with service structures. What is the difference between monolithic architecture and microservices?"
                    elif difficulty == "Medium":
                        q = "Welcome to your Backend mock interview! Let's talk about distributed transactions. How does the Saga pattern manage data consistency without using heavy two-phase commits?"
                    else:
                        q = "Welcome to your Backend mock interview! Let's look at network resilience. How do circuit breakers and retry loops prevent cascading failures across service dependencies?"
                elif "container" in topic_lower or "orchestration" in topic_lower:
                    if difficulty == "Easy":
                        q = "Welcome to your Backend mock interview! Let's start with containerization. What is a Docker container, and how is it different from a virtual machine?"
                    elif difficulty == "Medium":
                        q = "Welcome to your Backend mock interview! Let's discuss Kubernetes. How does service discovery work inside a K8s cluster, and what is the role of a Pod?"
                    else:
                        q = "Welcome to your Backend mock interview! Let's look at orchestration scaling. How do you configure rolling updates and liveness/readiness probes to guarantee zero-downtime deployments?"
                elif "high availability" in topic_lower or "reliability" in topic_lower:
                    if difficulty == "Easy":
                        q = "Welcome to your Backend mock interview! Let's start with uptime basics. What does 99.9% availability mean in practice, and how do load balancers contribute to it?"
                    elif difficulty == "Medium":
                        q = "Welcome to your Backend mock interview! Let's discuss failovers. How do you configure active-passive database replication systems to handle automatic backup routing?"
                    else:
                        q = "Welcome to your Backend mock interview! Let's look at disaster recovery. How do you design a multi-region active-active architecture that resolves write conflicts (e.g. vector clocks) during split-brain events?"

            elif "frontend" in role_lower or "ui" in role_lower or "react" in role_lower:
                if "js/ts" in topic_lower or "javascript" in topic_lower:
                    if difficulty == "Easy":
                        q = "Welcome to your Frontend mock interview! Let's start with language basics. What is the difference between let, const, and var declarations in JavaScript?"
                    elif difficulty == "Medium":
                        q = "Welcome to your Frontend mock interview! Let's discuss TS types. What is the difference between an interface and a type alias, and when should you use utility types like Pick or Omit?"
                    else:
                        q = "Welcome to your Frontend mock interview! Let's look at event handling. How does the JS event loop orchestrate the call stack, microtask queue, and macrotask queue?"
                elif "react" in topic_lower or "render" in topic_lower:
                    if difficulty == "Easy":
                        q = "Welcome to your Frontend mock interview! Let's start with React basics. What is the virtual DOM, and how does React use it to optimize updates?"
                    elif difficulty == "Medium":
                        q = "Welcome to your Frontend mock interview! Let's discuss rendering. How do you prevent unnecessary component re-renders when passing callbacks down to child components?"
                    else:
                        q = "Welcome to your Frontend mock interview! Let's look at React Fiber. How does the Fiber reconciler pause and resume work during concurrent rendering phases?"
                elif "performance" in topic_lower or "splitting" in topic_lower:
                    if difficulty == "Easy":
                        q = "Welcome to your Frontend mock interview! Let's start with performance. What are the Core Web Vitals, and why is LCP (Largest Contentful Paint) important?"
                    elif difficulty == "Medium":
                        q = "Welcome to your Frontend mock interview! Let's discuss splitting. How does lazy loading with dynamic imports improve the initial load time of a web page?"
                    else:
                        q = "Welcome to your Frontend mock interview! Let's look at critical rendering path optimization. How do you structure CSS, fonts, and JS delivery to eliminate layout shifts (CLS)?"

            return q

    def _get_watsonx_model(self):
        if self._watsonx_model is not None:
            return self._watsonx_model

        from ibm_watsonx_ai import Credentials
        from ibm_watsonx_ai.foundation_models import ModelInference

        credentials = Credentials(
            url=os.getenv("WATSONX_URL", DEFAULT_WATSONX_URL),
            api_key=os.environ["WATSONX_API_KEY"],
        )

        self._watsonx_model = ModelInference(
            model_id=self.watsonx_model_id,
            credentials=credentials,
            project_id=os.environ["WATSONX_PROJECT_ID"],
        )
        return self._watsonx_model

    def _generate_watsonx(self, prompt: str) -> str:
        model = self._get_watsonx_model()

        # Enforce a hard wall-clock timeout independent of the SDK's own
        # HTTP client, since a hung watsonx call must not block a demo.
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(model.generate_text, prompt=prompt)
            return future.result(timeout=self.watsonx_timeout)

    def _generate_ollama(self, prompt: str) -> str:
        from ollama import chat

        def _call():
            response = chat(
                model=self.ollama_model,
                messages=[
                    {
                        "role": "user",
                        "content": prompt,
                    }
                ],
                keep_alive=self.ollama_keep_alive,
            )
            return response["message"]["content"]

        # Same hard wall-clock timeout pattern as _generate_watsonx above -
        # without this, a stalled Ollama daemon (crashed model worker,
        # network hiccup, wedged connection) blocks the calling thread
        # forever with no way for any caller up the stack to recover.
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(_call)
            return future.result(timeout=self.ollama_timeout)
    