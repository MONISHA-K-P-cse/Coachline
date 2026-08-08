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
                    "Hello! I'm your AI career mentor. I can help you practice coding, design system architectures, refine your resume, or simulate mock interviews. What role are you preparing for?",
                    "Hi there! Great to connect. Ready to level up your interview preparation today? What topic or target company are we focusing on?",
                    "Hello! How is your interview preparation going? Let me know if you want to run a mock interview, review a topic, or look at your roadmap."
                ]
                return greetings[GraniteClient._mock_counter % len(greetings)]
            
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
                    "For behavioral questions, use the STAR method: Situation, Task, Action, Result. Focus 70% of your time on the Actions you took, and always finish with a quantified Result. Let's practice one: tell me about a time you resolved a technical conflict.",
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
                    "You're very welcome! Keep practicing and staying structured. Let me know what else you'd like to dive into next.",
                    "Glad that was helpful! Keep drilling those concepts. What should we tackle next?",
                    "Anytime! I'm here to support you until you feel 100% ready for the real thing. What's the next step on your mind?"
                ]
                return thanks_tips[GraniteClient._mock_counter % len(thanks_tips)]
            
            else:
                clean_msg = msg[:60] + "..." if len(msg) > 60 else msg
                general_responses = [
                    f"That's an interesting question regarding '{clean_msg}'. In technical interviews, candidates often focus too much on the happy path. I'd recommend thinking about what happens when services crash, network connections drop, or the database becomes saturated. How would you handle those edge cases?",
                    f"I see you're drilling down into '{clean_msg}'. It's vital to know the performance trade-offs here. For instance, caching helps read latency but adds complexity to write validation and cache invalidation. How would you handle cache consistency in this scenario?",
                    f"Regarding '{clean_msg}', a common follow-up interviewers ask is about metrics and observability. How would you set up alerting, dashboarding, or tracing to detect if this system is failing in production?",
                    f"That's a solid point about '{clean_msg}'. When designing code or infrastructure for this, consider how to keep it modular and testable. How would you mock dependencies to write clean unit tests for this logic?",
                    f"When discussing '{clean_msg}' with senior developers, they like to see solid database decision-making. Would you opt for a relational database like PostgreSQL or a NoSQL database like MongoDB for this kind of data model, and why?",
                    f"That ties back to scalability constraints for '{clean_msg}'. If your traffic suddenly scaled 100x overnight, where would the bottleneck be? Would it be CPU, memory, database IOPS, or network bandwidth?",
                    f"That's a helpful perspective. Let's think about how to frame this experience during a behavioral question. How would you describe a challenge you faced related to '{clean_msg}' using the STAR method?"
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
                matched = False
                for weak, strong in rewrites.items():
                    if weak in line.lower():
                        improved_lines.append(strong)
                        changes_made.append(f"Optimized phrase '{weak}' into a quantified impact statement.")
                        matched = True
                        break
                if not matched:
                    if "responsible for" in line.lower():
                        line = line.replace("responsible for", "Spearheaded design and delivery of")
                        changes_made.append("Upgraded passive duty statement to active leadership verb.")
                    improved_lines.append(line)

            if not changes_made:
                improved_lines.append("\n**Key Technical Projects (Optimized)**\n- Developed high-concurrency microservices utilizing FastAPI, Redis Caching, and Docker containers, improving request throughput by 45%.\n- Integrated comprehensive monitoring and alerting infrastructure using Prometheus and Grafana for backend API services.")
                changes_made.append("Appended optimized, impact-focused project achievements.")

            improved_text = "\n".join(improved_lines)

            import json
            return json.dumps({
                "improved_text": improved_text,
                "changes_made": changes_made
            })
        # ResumeAgent - analyze_resume
        elif "resume score" in prompt_lower or "ats resume optimizer" in prompt_lower:
            return """{
              "score": 85,
              "ats_score": 82,
              "summary": "The candidate has strong software engineering foundations with hands-on experience building APIs and database systems.",
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
                ("API Design & RESTful Standards", "Master REST constraints, status codes, query filtering, pagination, and OpenAPI specifications."),
                ("Database Scaling & Indexes", "Deep dive into composite indexes, query optimization, sharding, replication, and SQL vs NoSQL trade-offs."),
                ("Caching Strategies & Stampedes", "Master Redis cache-aside pattern, eviction policies (LRU, LFU), TTL strategies, and cache stampede mitigations."),
                ("Concurrency & Thread Pools", "Understand CPU-bound vs I/O-bound tasks, multithreading, asyncio event loops, locks, and thread pool scaling."),
                ("Message Queues & Event-Driven Design", "Integrate RabbitMQ/Kafka, pub-sub architectures, consumer groups, message durability, and backpressure."),
                ("Microservices & Distributed Transactions", "Understand API gateways, service discovery, saga pattern, two-phase commits, and circuit breakers."),
                ("Containerization & Orchestration", "Learn multi-stage Docker builds, resource constraints, Kubernetes pods, services, and config maps."),
                ("High Availability & Reliability Engineering", "Study rate-limiting, load balancers, database failover, health checks, and monitoring with Prometheus/Grafana.")
            ]

            syllabus_frontend = [
                ("Advanced JS/TS & Clean Code", "Deep dive into JS closures, prototype chains, event loop, TS advanced types (mapped, conditional, utility)."),
                ("React Architecture & Render Lifecycle", "Understand Virtual DOM, React Fiber reconciler, component mounts, hooks rendering patterns, and concurrent mode."),
                ("Web Performance & Code Splitting", "Optimize Core Web Vitals, critical rendering path, lazy loading, dynamic import(), and bundler optimizations."),
                ("State Management & Data Flow", "Master local vs global states, React context, Zustand, Redux Toolkit, and atomic states like Recoil."),
                ("Browser APIs & Security", "Learn about service workers, offline storage (IndexedDB), CORS policy, XSS, CSRF, and CSP headers."),
                ("CSS layouts & Responsive Design", "Master Flexbox, CSS Grid, container queries, Tailwind utility classes, and CSS-in-JS variables."),
                ("Testing & CI/CD for Frontend", "Write unit tests with Vitest, component tests with Testing Library, and E2E automation with Playwright."),
                ("SSR, SSG & Modern Frameworks", "Master Next.js App Router, server components, static generation, dynamic hydration, and edge middleware.")
            ]

            syllabus_ds = [
                ("Feature Engineering & Analytics", "Clean datasets, impute missing values, scale variables, and run exploratory data analyses."),
                ("Supervised & Unsupervised Learning", "Compare linear/logistic regression, tree-based models, clustering techniques, and metrics like F1 and ROC-AUC."),
                ("Deep Learning & Frameworks", "Build neural networks using PyTorch/TensorFlow, optimize weights, prevent overfitting, and use transfer learning."),
                ("LLMs & NLP Tuning", "Learn transformer architectures, tokenize text corpora, vector embeddings, semantic search, and prompt engineering."),
                ("Model Deployment & APIs", "Containerize machine learning models using Docker, build FastAPI endpoints, and serve inference results."),
                ("Big Data & Cloud Pipelines", "Write PySpark data transformations, build ETL pipelines, and query datasets using Snowflake/Redshift."),
                ("A/B Testing & Experimentation", "Formulate null hypotheses, calculate sample sizes, run power analyses, and evaluate statistical significance."),
                ("MLOps & Lifecycle Monitoring", "Set up MLflow model registries, track experiments, detect data drift, and automate pipeline trigger schedules.")
            ]

            syllabus_default = [
                ("Computer Science Fundamentals", "Review Big O complexity, dynamic programming, sorting/searching, and basic memory management."),
                ("Data Structures in Practice", "Master arrays, hash maps, linked lists, trees, and graphs, focusing on traversal algorithms."),
                ("Design Patterns & Architecture", "Study creational, structural, and behavioral patterns, alongside SOLID engineering principles."),
                ("System Design Basics", "Understand vertical vs horizontal scaling, load balancing, DNS routing, and monolithic vs microservices."),
                ("Database & Transactions", "Master ACID guarantees, isolation levels, database normalization, and query performance optimizations."),
                ("Networking & Protocols", "Deep dive into HTTP/HTTPS, TCP/IP, websockets, DNS lookups, and load balancer configurations."),
                ("CI/CD & Version Control", "Master advanced Git workflows (rebase, cherry-pick), automation pipelines, and infrastructure deployment."),
                ("Security & Reliability", "Learn about encryption, HTTPS, OAuth2 authorization flows, rate limiting, and system failure recovery.")
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
                title, desc = active_syllabus[(i - 1) % len(active_syllabus)]
                steps.append({
                    "step_number": i,
                    "title": title,
                    "description": desc,
                    "estimated_hours": 15
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

            # Define topic-specific keywords
            topic_keywords = {
                "database": ["index", "query", "sql", "nosql", "postgres", "mongodb", "acid", "transaction", "scale", "normalization"],
                "index": ["b-tree", "hash", "scan", "lookup", "composite", "primary", "secondary", "write", "read"],
                "cache": ["redis", "memcached", "eviction", "ttl", "hit", "miss", "consistency", "invalidation", "stampede"],
                "api": ["rest", "fastapi", "http", "endpoint", "status", "json", "request", "response", "latency", "grpc"],
                "python": ["gil", "async", "await", "thread", "process", "memory", "decorator", "generator", "yield"],
                "concurrency": ["thread", "lock", "asyncio", "semaphore", "race", "deadlock", "process", "safety"],
                "microservice": ["service", "communication", "grpc", "event", "kafka", "queue", "discovery", "latency"]
            }

            # Gather keywords based on topics in the question
            matched_keywords = []
            for topic, keywords in topic_keywords.items():
                if topic in q_clean:
                    matched_keywords.extend(keywords)

            general_quality_terms = [
                "trade-off", "performance", "scalability", "latency", "throughput", "redundancy",
                "bottleneck", "optimization", "monitoring", "metric", "consistency", "reliability",
                "robust", "security", "thread-safe"
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
                tech_base = 50.0 + (hits * 8.0) + (quality_hits * 5.0)
                tech = max(45.0, min(95.0, tech_base))

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
            for line in prompt.splitlines():
                if "role:" in line.lower():
                    parts = prompt.split(line)
                    if len(parts) > 1:
                        lines_after = parts[1].strip().splitlines()
                        if lines_after:
                            role = lines_after[0].strip()
                elif "week:" in line.lower():
                    parts = line.split(":", 1)
                    if len(parts) > 1 and parts[1].strip().isdigit():
                        week = int(parts[1].strip())
                elif "topic:" in line.lower():
                    parts = line.split(":", 1)
                    if len(parts) > 1:
                        topic = parts[1].strip()

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
    