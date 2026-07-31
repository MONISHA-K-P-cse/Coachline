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
                "Ollama call failed (%s); returning a mock response for the demo.",
                exc,
            )
            return self._generate_mock(prompt)

    def _generate_mock(self, prompt: str) -> str:
        # Check if it is the Resume Agent prompt
        if "ATS Resume Reviewer" in prompt:
            return """{
  "score": 85,
  "ats_score": 88,
  "summary": "Experienced software developer with a strong foundation in backend services and systems integration.",
  "resume_feedback": "Your resume has a very clear structure and highlights key tech stack items. Adding more quantifiable metrics to your projects would make it even stronger.",
  "strengths": ["Clear technical stack definition", "Good project impact statements"],
  "improvements": ["Quantify results with percentages or figures", "Add details on cloud infrastructure deployment"]
}"""
        # Check if it is the Resume Optimizer prompt
        elif "ATS Resume Optimizer" in prompt:
            return """{
  "improved_text": "Monisha - Software Engineer\\n\\nEXPERIENCE\\n* Backend Developer | Stripe\\n  - Optimized distributed cache architecture using Redis, reducing query latencies by 35% and improving platform throughput.\\n  - Deployed microservices using Docker on AWS ECS, ensuring 99.9% uptime with circuit breakers.\\n  - Structured RESTful APIs with Python FastAPI and SQLAlchemy, achieving 40% faster onboarding for new developers through Swagger documentation.",
  "changes_made": [
    "Quantified cache improvements with 'reducing query latencies by 35%'",
    "Explicitly named AWS ECS and Docker for cloud infrastructure",
    "Added metrics for onboarding developer efficiency"
  ]
}"""
        # Check if it is the JD Agent prompt
        elif "JD) Analyzer" in prompt:
            return """{
  "skill_gaps": [
    {
      "category": "Must-Have Technical Skills",
      "missing_skills": ["Distributed Caching (Redis)", "Kafka Event Streaming"],
      "priority": "High"
    },
    {
      "category": "Architecture & Design",
      "missing_skills": ["System Resilience Patterns (Circuit Breakers)"],
      "priority": "Medium"
    }
  ],
  "matched_skills": ["Python FastAPI", "SQLAlchemy", "Alembic Migrations", "RESTful APIs", "JWT Auth"]
}"""
        # Check if it is the Roadmap Agent prompt
        elif "learning roadmap" in prompt:
            return """Week 1: Git and Version Control
Learn git basics, branching strategy, and pull request workflows.

Week 2: Backend Framework Basics
Build REST APIs, understand routing, and configure database connections.

Week 3: Database Design and Migrations
Learn schema design, index optimization, and database migrations.

Week 4: Authentication and Security
Implement JWT, user registration, login, and secure endpoints.

Week 5: API Documentation and Testing
Write unit tests, integration tests, and set up Swagger/OpenAPI.

Week 6: Caching and Performance
Use Redis for caching and query optimization.

Week 7: Containerization and Deployment
Dockerize the application and deploy it to cloud platforms.

Week 8: Advanced Topics and Final Project
Learn message queues, system design, and complete a final capstone project."""

        # Check if it is the Career Mentor prompt
        elif "career mentor" in prompt:
            import re
            
            msg_lower = ""
            match = re.search(r'Candidate message:\s*\n([^\n]+)', prompt)
            if match:
                msg_lower = match.group(1).strip().lower()
            
            if any(greet in msg_lower for greet in ["hi", "hello", "hey", "hola"]):
                return "Hello! I'm your career mentor. I'm here to help you get interview-ready! You can ask me about resume feedback, study roadmap topics, mock sessions, or general tech prep advice."
            elif any(keyword in msg_lower for keyword in ["prep", "prepare", "start", "what to", "study", "guidance", "begin"]):
                return "To prepare effectively, I recommend focusing on three core areas: 1) Data structures and algorithm basics, 2) DB transaction locks & scaling, and 3) Containerization tools (like Docker). We can review your strengths next, or start a mock session! What would you like to focus on first?"
            else:
                return "That is a very good question! Mastering that technical concept requires a solid balance of understanding core architectural properties (like ACID parameters or separation of concerns) and writing real, containerized prototype scripts. Which specific area should we drill down into next?"

        # Check if it is the Evaluation Agent prompt
        elif "technical_score" in prompt:
            return """{
  "technical_score": 80.0,
  "communication_score": 85.0,
  "behavioral_score": 75.0,
  "confidence_score": 80.0,
  "star_score": 85.0,
  "overall_score": 81.0,
  "feedback": "Great overview of the technical components. Try to add more details about memory limits or database constraints in your answers.",
  "weak_topics": ["Database Scaling"]
}"""
        # Check if it is the Notes Agent prompt
        elif "learning style" in prompt or "VARK" in prompt:
            import re
            import json
            
            topic = "Selected Topic"
            match = re.search(r'Topic:\s*\n([^\n]+)', prompt)
            if match:
                topic = match.group(1).strip()
            
            topic_lower = topic.lower()
            
            # ─── Dynamic Registry of Predefined Core CS Topics ───
            if "dbms" in topic_lower or "database" in topic_lower:
                if "VISUAL" in prompt:
                    blocks_data = [
                        {
                            "type": "text",
                            "content": "### Database Management Systems (DBMS)\n\nDBMS acts as the central interface managing data, transactions, access control, and storage engines."
                        },
                        {
                            "type": "diagram",
                            "content": "graph TD\n    App[Application client] --> Engine[SQL Parser/Optimizer]\n    Engine --> Concur[Lock/Concurrency Manager]\n    Concur --> Buff[Buffer/Cache Pool]\n    Buff --> Disk[(Physical Tablespaces)]"
                        }
                    ]
                elif "KINESTHETIC" in prompt:
                    blocks_data = [
                        {
                            "type": "text",
                            "content": "### Practical SQL Transactions\n\nLet's write a resilient, ACID-compliant multi-statement transaction in DBMS."
                        },
                        {
                            "type": "exercise",
                            "content": "**Task:** Write a transaction transferring balance between accounts safely.\n\n**Solution Walkthrough:**\n```sql\nBEGIN TRANSACTION;\nUPDATE accounts SET balance = balance - 150 WHERE id = 1;\nUPDATE accounts SET balance = balance + 150 WHERE id = 2;\nCOMMIT;\n```"
                        }
                    ]
                else:
                    blocks_data = [
                        {
                            "type": "text",
                            "content": "### Deep-Dive: Database Management Systems (DBMS)\n\n* **ACID Qualities**:\n  - **Atomicity**: Complete rollback on failure.\n  - **Consistency**: Data conforms to active constraint rules.\n  - **Isolation**: Concurrent queries execute without race conditions.\n  - **Durability**: Written transaction records survive crashes.\n* **Normalization**: Organizing schemas into 1NF, 2NF, and 3NF to mitigate write anomalies."
                        }
                    ]
            elif "ds" == topic_lower or "data structure" in topic_lower or "algorithm" in topic_lower:
                if "VISUAL" in prompt:
                    blocks_data = [
                        {
                            "type": "text",
                            "content": "### Memory Layout: Arrays vs Linked Lists\n\nData structures represent organized schemas for optimal memory access."
                        },
                        {
                            "type": "diagram",
                            "content": "graph LR\n    subgraph Array (Contiguous memory)\n    A[0: NodeA] --- B[1: NodeB] --- C[2: NodeC]\n    end\n    subgraph Linked List (Pointer referenced)\n    D[Val: NodeA] --> E[Val: NodeB] --> F[Val: NodeC]\n    end"
                        }
                    ]
                elif "KINESTHETIC" in prompt:
                    blocks_data = [
                        {
                            "type": "text",
                            "content": "### Algorithm Lab: Linked List Reversal\n\nLet's implement a pointer reversal exercise in-place."
                        },
                        {
                            "type": "exercise",
                            "content": "**Task:** Reverse a singly linked list in Python.\n\n**Solution:**\n```python\ndef reverse(head):\n    prev, curr = None, head\n    while curr:\n        nxt = curr.next\n        curr.next = prev\n        prev = curr\n        curr = nxt\n    return prev\n```"
                        }
                    ]
                else:
                    blocks_data = [
                        {
                            "type": "text",
                            "content": "### Deep-Dive: Data Structures & Complexity\n\n* **Linear Structures**: Arrays offer constant time O(1) indexing, whereas Linked Lists excel at O(1) head insertion.\n* **Hierarchical Trees**: Binary Search Trees (BST), AVL, and Red-Black trees maintain order for fast search operations.\n* **Big O Notation**: Standard complexity bounds used to rate execution (O(1), O(log n), O(n), O(n log n), O(n^2)) and spatial overhead."
                        }
                    ]
            elif "docker" in topic_lower or "container" in topic_lower:
                if "VISUAL" in prompt:
                    blocks_data = [
                        {
                            "type": "text",
                            "content": "### Visualizing Container Virtualization\n\nContainers isolate runtimes while sharing the host OS kernel directly."
                        },
                        {
                            "type": "diagram",
                            "content": "graph TD\n    Dockerfile[Dockerfile Configuration] --> Build[docker build] --> Image[Docker Image Template]\n    Image --> Run[docker run] --> Active[Running Isolated Container]"
                        }
                    ]
                elif "KINESTHETIC" in prompt:
                    blocks_data = [
                        {
                            "type": "text",
                            "content": "### Lab: Building a Production Dockerfile\n\nLet's write a container configuration Dockerfile for a local server."
                        },
                        {
                            "type": "exercise",
                            "content": "**Task:** Dockerize a python service.\n\n**Solution Configuration:**\n```dockerfile\nFROM python:3.10-slim\nWORKDIR /app\nCOPY requirements.txt .\nRUN pip install -r requirements.txt\nCOPY . .\nCMD [\"uvicorn\", \"main:app\", \"--host\", \"0.0.0.0\"]\n```"
                        }
                    ]
                else:
                    blocks_data = [
                        {
                            "type": "text",
                            "content": "### Deep-Dive: Containerization & Docker\n\n* **Container Isolation**: Uses Linux cgroups and namespaces to isolate resource bounds and process directories.\n* **Layer Caching**: Docker caches build instructions, accelerating image deployment.\n* **Volume Mounting**: Mount host folders to keep container databases persistent."
                        }
                    ]
            elif "redis" in topic_lower or "cache" in topic_lower:
                if "VISUAL" in prompt:
                    blocks_data = [
                        {
                            "type": "text",
                            "content": "### Cache-Aside (Lazy Loading) Sequence\n\nCaching stores query outputs in fast RAM to speed up read latency."
                        },
                        {
                            "type": "diagram",
                            "content": "graph LR\n    App[Client App] --> Check{In Cache?}\n    Check -- Yes (Hit) --> Ret[Return Data]\n    Check -- No (Miss) --> DB[(PostgreSQL)] --> Cache[Save to Redis Cache] --> Ret"
                        }
                    ]
                elif "KINESTHETIC" in prompt:
                    blocks_data = [
                        {
                            "type": "text",
                            "content": "### Exercise: Caching Python Functions\n\nLet's implement a standard database getter wrapper with Redis."
                        },
                        {
                            "type": "exercise",
                            "content": "**Task:** Implement fallback caching.\n\n**Solution Python Code:**\n```python\ndef query_user(uid):\n    cached = redis.get(f'user:{uid}')\n    if cached:\n        return json.loads(cached)\n    user = db.fetch(uid)\n    redis.setex(f'user:{uid}', 300, json.dumps(user))\n    return user\n```"
                        }
                    ]
                else:
                    blocks_data = [
                        {
                            "type": "text",
                            "content": "### Deep-Dive: Memory Caching Systems\n\n* **Cache Eviction (LRU/LFU)**: Discards least recently/frequently used keys when size bounds are reached.\n* **Time-to-Live (TTL)**: Automatically clears records to maintain content freshness.\n* **Cache Writing Patterns**: Cache-aside loads on-demand; Write-Through commits to cache and DB synchronously."
                        }
                    ]
            elif "jwt" in topic_lower or "auth" in topic_lower:
                if "VISUAL" in prompt:
                    blocks_data = [
                        {
                            "type": "text",
                            "content": "### JSON Web Token Authentication Cycle\n\nJWT provides secure authorization for RESTful endpoints."
                        },
                        {
                            "type": "diagram",
                            "content": "graph TD\n    Client[Client Browser] --> Login[POST /auth/login]\n    Login --> Server[Validate & Sign JWT]\n    Server --> ReturnJWT[Return Access Token]\n    Client --> APIReq[GET /data with Auth Header] --> SignCheck{Valid Secret?} --> Data[Access Granted]"
                        }
                    ]
                elif "KINESTHETIC" in prompt:
                    blocks_data = [
                        {
                            "type": "text",
                            "content": "### Lab: Token Encoding & Verification\n\nLet's write a helper to encode user credentials into a token payload."
                        },
                        {
                            "type": "exercise",
                            "content": "**Task:** Write a Python function signing a JWT.\n\n**Solution Script:**\n```python\nimport jwt, datetime\ndef generate_jwt(user_id):\n    payload = {\n        'sub': user_id,\n        'exp': datetime.datetime.utcnow() + datetime.timedelta(hours=1)\n    }\n    return jwt.encode(payload, SECRET_KEY, algorithm='HS256')\n```"
                        }
                    ]
                else:
                    blocks_data = [
                        {
                            "type": "text",
                            "content": "### Deep-Dive: JSON Web Tokens (JWT)\n\n* **Token Segments**: Encoded header (algorithm config), payload (user claims), and sign checksum.\n* **Stateless Authorization**: Eliminates session storage by letting the server verify tokens cryptographically.\n* **Security Recommendations**: Use HTTPS, keep expiration times short, and store tokens securely in HTTP-only cookies."
                        }
                    ]
            elif "ai" == topic_lower or "artificial intelligence" in topic_lower or "machine learning" in topic_lower or "ml" == topic_lower:
                if "VISUAL" in prompt:
                    blocks_data = [
                        {
                            "type": "text",
                            "content": "### Artificial Intelligence & Machine Learning\n\nAI systems learn patterns from inputs to make decisions or generate responses. Let's trace a neural network layer flow."
                        },
                        {
                            "type": "diagram",
                            "content": "graph LR\n    Input[Input Features] --> Dense1[Dense Hidden Layer 1]\n    Dense1 --> Dense2[Dense Hidden Layer 2]\n    Dense2 --> Activation[Softmax Activation]\n    Activation --> Output[Prediction Label]"
                        }
                    ]
                elif "KINESTHETIC" in prompt:
                    blocks_data = [
                        {
                            "type": "text",
                            "content": "### Coding Lab: Training a Simple Classifier\n\nLet's write a simple linear model optimization step in Python."
                        },
                        {
                            "type": "exercise",
                            "content": "**Task:** Write a gradient update step for weights.\n\n**Solution Code:**\n```python\ndef update_weights(w, x, y, lr=0.01):\n    prediction = w * x\n    error = prediction - y\n    gradient = error * x\n    w = w - lr * gradient\n    return w\n```"
                        }
                    ]
                else:
                    blocks_data = [
                        {
                            "type": "text",
                            "content": "### Deep-Dive: Artificial Intelligence & Neural Networks\n\n* **Supervised Learning**: Training models on paired inputs and labels to learn predictions (e.g. regression, classification).\n* **Deep Neural Networks (DNN)**: Runtimes composed of interconnected layers of artificial neurons optimizing weights via backpropagation.\n* **Generative AI & LLMs**: Transformers analyzing token probability distributions to predict and generate sequential text."
                        }
                    ]
            elif "java" in topic_lower or "oop" in topic_lower or "object oriented" in topic_lower:
                if "VISUAL" in prompt:
                    blocks_data = [
                        {
                            "type": "text",
                            "content": "### Java & OOP Inheritance Structure\n\nJava is a strongly typed, class-based object-oriented programming language."
                        },
                        {
                            "type": "diagram",
                            "content": "graph TD\n    Abstract[Abstract: Asset] --> Class1[Class: RealEstate]\n    Abstract --> Class2[Class: Stock]\n    Class1 --> Inst1[Instance: 123 Main St]\n    Class2 --> Inst2[Instance: GOOGL]"
                        }
                    ]
                elif "KINESTHETIC" in prompt:
                    blocks_data = [
                        {
                            "type": "text",
                            "content": "### Implementing a Custom Java Interface\n\nLet's write a standard class inheritance and interface implementation in Java."
                        },
                        {
                            "type": "exercise",
                            "content": "**Task:** Implement the Runnable interface in Java.\n\n**Solution Class:**\n```java\npublic class CustomWorker implements Runnable {\n    @Override\n    public void run() {\n        System.out.println(\"Worker thread executing.\");\n    }\n}\n```"
                        }
                    ]
                else:
                    blocks_data = [
                        {
                            "type": "text",
                            "content": "### Deep-Dive: Java & OOP Foundations\n\n* **Core Java Runtimes**: Compiled source code (.java) translates to platform-independent bytecode (.class) executed by the Java Virtual Machine (JVM).\n* **Four pillars of OOP**:\n  - **Encapsulation**: Hiding internal state via private variables and public getters/setters.\n  - **Inheritance**: Subclasses sharing and expanding parental definitions.\n  - **Polymorphism**: Interface functions executing custom subclass actions dynamically.\n  - **Abstraction**: Defining contracts (interfaces/abstract classes) hiding implementation details."
                        }
                    ]
            else:
                if "VISUAL" in prompt:
                    blocks_data = [
                        {
                            "type": "text",
                            "content": f"### Architectural Framework of {topic}\n\nLet's trace the service boundaries and database connections for **{topic}**."
                        },
                        {
                            "type": "diagram",
                            "content": f"graph TD\n    A[Client User] --> B[Controller Interface]\n    B --> C[Service Logic: {topic}]\n    C --> D[Data Persistence]"
                        }
                    ]
                elif "KINESTHETIC" in prompt:
                    blocks_data = [
                        {
                            "type": "text",
                            "content": f"### Coding Lab: {topic}\n\nLet's construct a simple functional model or script for **{topic}**."
                        },
                        {
                            "type": "exercise",
                            "content": f"**Task:** Write a config module setting up dependencies for **{topic}**.\n\n**Solution Checklist:**\n1. Define environment variables.\n2. Bind listener connections.\n3. Run connectivity checks."
                        }
                    ]
                else:
                    blocks_data = [
                        {
                            "type": "text",
                            "content": f"### Core Specifications: {topic}\n\n* **Primary Function**: **{topic}** represents a modular software design pattern in distributed system engineering.\n* **Key Strengths**:\n  - Promotes separation of concerns and high modularity.\n  - Reduces data dependencies between components.\n* **Deployment Best Practices**:\n  - Implement resource health checks.\n  - Set alert limits based on memory consumption metrics."
                        }
                    ]
            
            return json.dumps({"blocks": blocks_data})
        # Check if it is the Interview Agent prompt
        elif "technical interviewer" in prompt:
            return "How does horizontal database scaling differ from vertical database scaling, and what are the primary trade-offs of sharding?"

        # Default fallback
        return "This is a default AI response for the mock/offline environment."

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
    