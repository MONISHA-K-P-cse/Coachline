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

        try:
            blocks = self._generate_text_blocks(topic, context, target_role)
            if blocks is None:
                blocks = [{"type": "text", "content": FALLBACK_TEXT_TEMPLATE.format(topic=topic)}]

            supplement_type = SUPPLEMENT_BLOCK_TYPE.get(style)
            if supplement_type and blocks:
                supplement = self._generate_supplement_block(topic, context, target_role, supplement_type)
                if supplement:
                    blocks.append(supplement)
        except Exception as exc:
            logger.warning("Notes agent generation failed (%s); returning mock CS topic fallback.", exc)
            blocks = self._generate_mock_notes(topic, style)

        return {
            "topic": topic,
            "title": f"{topic} Notes",
            "learning_style": style,
            "blocks": blocks,
            "note_type": "detailed_note",
            "category": "AI Generated",
            "is_bookmarked": False,
        }

    def _generate_mock_notes(self, topic: str, style: str):
        topic_lower = topic.lower()
        if "dbms" in topic_lower or "database" in topic_lower:
            if style == "visual":
                return [
                    {"type": "text", "content": "### Database Scaling & High Availability\n\nScalability requires dividing data or replicating servers. Let's trace how SQL queries reach master and replica nodes."},
                    {"type": "diagram", "content": "graph TD\n    App[App Client] --> proxy[Proxy / Router]\n    proxy -- Reads --> Replica[(Read-Only Replica)]\n    proxy -- Writes --> Master[(Write Master)]\n    Master -- Replicates --> Replica"}
                ]
            elif style == "kinesthetic":
                return [
                    {"type": "text", "content": "### Coding Lab: PostgreSQL Transaction Isolation\n\nLet's construct a standard SQL transaction block demonstrating isolation behavior."},
                    {"type": "exercise", "content": "**Task:** Implement a safe transaction with serializable isolation level in SQL.\n\n**Solution Steps:**\n```sql\nBEGIN TRANSACTION ISOLATION LEVEL SERIALIZABLE;\nUPDATE accounts SET balance = balance - 100 WHERE id = 1;\nUPDATE accounts SET balance = balance + 100 WHERE id = 2;\nCOMMIT;\n```"}
                ]
            else:
                return [
                    {"type": "text", "content": "### Deep-Dive: Database Management Systems (DBMS)\n\n* **ACID Transactions**: Guarantees reliability via Atomicity, Consistency, Isolation, and Durability.\n* **Normalization**: Organizing schemas (1NF, 2NF, 3NF) to eliminate redundant data and avoid update anomalies.\n* **Indexes**: Utilizing B-Trees or Hash Indexes to speed up queries, with the trade-off of slower write speeds."}
                ]
        elif "ds" == topic_lower or "data structure" in topic_lower or "algorithm" in topic_lower:
            if style == "visual":
                return [
                    {"type": "text", "content": "### Data Structure Memory Allocations\n\nHow data is laid out in memory changes search and insertion time complexity."},
                    {"type": "diagram", "content": "graph LR\n    subgraph Array (Contiguous memory)\n    A[0: NodeA] --- B[1: NodeB] --- C[2: NodeC]\n    end\n    subgraph Linked List (Pointer referenced)\n    D[Val: NodeA] --> E[Val: NodeB] --> F[Val: NodeC]\n    end"}
                ]
            elif style == "kinesthetic":
                return [
                    {"type": "text", "content": "### Algorithm Lab: Linked List Reversal\n\nLet's implement a pointer reversal exercise in-place."},
                    {"type": "exercise", "content": "**Task:** Reverse a singly linked list in Python.\n\n**Solution:**\n```python\ndef reverse(head):\n    prev, curr = None, head\n    while curr:\n        nxt = curr.next\n        curr.next = prev\n        prev = curr\n        curr = nxt\n    return prev\n```"}
                ]
            else:
                return [
                    {"type": "text", "content": "### Deep-Dive: Data Structures & Complexity\n\n* **Linear Structures**: Arrays offer constant time O(1) indexing, whereas Linked Lists excel at O(1) head insertion.\n* **Hierarchical Trees**: Binary Search Trees (BST), AVL, and Red-Black trees maintain order for fast search operations.\n* **Big O Notation**: Standard complexity bounds used to rate execution (O(1), O(log n), O(n), O(n log n), O(n^2)) and spatial overhead."}
                ]
        elif "docker" in topic_lower or "container" in topic_lower:
            if style == "visual":
                return [
                    {"type": "text", "content": "### Visualizing Container Virtualization\n\nContainers isolate runtimes while sharing the host OS kernel directly."},
                    {"type": "diagram", "content": "graph TD\n    Dockerfile[Dockerfile Configuration] --> Build[docker build] --> Image[Docker Image Template]\n    Image --> Run[docker run] --> Active[Running Isolated Container]"}
                ]
            elif style == "kinesthetic":
                return [
                    {"type": "text", "content": "### Lab: Building a Production Dockerfile\n\nLet's write a container configuration Dockerfile for a local server."},
                    {"type": "exercise", "content": "**Task:** Dockerize a python service.\n\n**Solution Configuration:**\n```dockerfile\nFROM python:3.10-slim\nWORKDIR /app\nCOPY requirements.txt .\nRUN pip install -r requirements.txt\nCOPY . .\nCMD [\"uvicorn\", \"main:app\", \"--host\", \"0.0.0.0\"]\n```"}
                ]
            else:
                return [
                    {"type": "text", "content": "### Deep-Dive: Containerization & Docker\n\n* **Container Isolation**: Uses Linux cgroups and namespaces to isolate resource bounds and process directories.\n* **Layer Caching**: Docker caches build instructions, accelerating image deployment.\n* **Volume Mounting**: Mount host folders to keep container databases persistent."}
                ]
        elif "redis" in topic_lower or "cache" in topic_lower:
            if style == "visual":
                return [
                    {"type": "text", "content": "### Cache-Aside (Lazy Loading) Sequence\n\nCaching stores query outputs in fast RAM to speed up read latency."},
                    {"type": "diagram", "content": "graph LR\n    App[Client App] --> Check{In Cache?}\n    Check -- Yes (Hit) --> Ret[Return Data]\n    Check -- No (Miss) --> DB[(PostgreSQL)] --> Cache[Save to Redis Cache] --> Ret"}
                ]
            elif style == "kinesthetic":
                return [
                    {"type": "text", "content": "### Coding Lab: Implementing Cache-Aside Caching\n\nLet's write a cache lookup and database fallback in Python."},
                    {"type": "exercise", "content": "**Task:** Implement a cache retrieval helper using redis-py.\n\n**Solution Helper:**\n```python\nimport json\n\ndef get_user(user_id, r_client, db_conn):\n    cached = r_client.get(f\"user:{user_id}\")\n    if cached:\n        return json.loads(cached)\n    user = db_conn.query(\"SELECT * FROM users WHERE id = %s\", (user_id,))\n    r_client.setex(f\"user:{user_id}\", 3600, json.dumps(user))\n    return user\n```"}
                ]
            else:
                return [
                    {"type": "text", "content": "### Deep-Dive: Cache Patterns & Redis\n\n* **Memory Storage**: Redis keeps all datasets in memory to provide sub-millisecond response read times.\n* **Cache-Aside Pattern**: Applications query the cache first; on a miss, they load from database and write back to cache.\n* **Eviction Policies**: Employs algorithms (like LRU, LFU, TTL) to free up memory when limits are met."}
                ]
        elif "jwt" in topic_lower or "auth" in topic_lower:
            if style == "visual":
                return [
                    {"type": "text", "content": "### JWT Token-Based Flow Architecture\n\nStateless tokens let backend clients authenticate without matching session databases."},
                    {"type": "diagram", "content": "graph TD\n    Client[Web Client] -- 1. Credentials --> AuthServer[Auth Service]\n    AuthServer -- 2. Issues Signed JWT --> Client\n    Client -- 3. Request + Authorization Header --> API[Backend API]\n    API -- 4. Cryptographic Validation (No DB check) --> Client"}
                ]
            elif style == "kinesthetic":
                return [
                    {"type": "text", "content": "### Coding Lab: JWT Signing in Python\n\nLet's write a token generation method using PyJWT."},
                    {"type": "exercise", "content": "**Task:** Write a Python method signing a user payload.\n\n**Solution Code:**\n```python\nimport jwt\nimport datetime\n\ndef generate_token(user_id, secret):\n    payload = {\n        \"sub\": user_id,\n        \"exp\": datetime.datetime.utcnow() + datetime.timedelta(hours=24)\n    }\n    return jwt.encode(payload, secret, algorithm=\"HS256\")\n```"}
                ]
            else:
                return [
                    {"type": "text", "content": "### Deep-Dive: JSON Web Tokens (JWT)\n\n* **Token Segments**: Encoded header (algorithm config), payload (user claims), and sign checksum.\n* **Stateless Authorization**: Eliminates session storage by letting the server verify tokens cryptographically.\n* **Security Recommendations**: Use HTTPS, keep expiration times short, and store tokens securely in HTTP-only cookies."}
                ]
        elif "ai" == topic_lower or "artificial intelligence" in topic_lower or "machine learning" in topic_lower or "ml" == topic_lower:
            if style == "visual":
                return [
                    {"type": "text", "content": "### Artificial Intelligence & Machine Learning\n\nAI systems learn patterns from inputs to make decisions or generate responses. Let's trace a neural network layer flow."},
                    {"type": "diagram", "content": "graph LR\n    Input[Input Features] --> Dense1[Dense Hidden Layer 1]\n    Dense1 --> Dense2[Dense Hidden Layer 2]\n    Dense2 --> Activation[Softmax Activation]\n    Activation --> Output[Prediction Label]"}
                ]
            elif style == "kinesthetic":
                return [
                    {"type": "text", "content": "### Coding Lab: Training a Simple Classifier\n\nLet's write a simple linear model optimization step in Python."},
                    {"type": "exercise", "content": "**Task:** Write a gradient update step for weights.\n\n**Solution Code:**\n```python\ndef update_weights(w, x, y, lr=0.01):\n    prediction = w * x\n    error = prediction - y\n    gradient = error * x\n    w = w - lr * gradient\n    return w\n```"}
                ]
            else:
                return [
                    {"type": "text", "content": "### Deep-Dive: Artificial Intelligence & Neural Networks\n\n* **Supervised Learning**: Training models on paired inputs and labels to learn predictions (e.g. regression, classification).\n* **Deep Neural Networks (DNN)**: Runtimes composed of interconnected layers of artificial neurons optimizing weights via backpropagation.\n* **Generative AI & LLMs**: Transformers analyzing token probability distributions to predict and generate sequential text."}
                ]
        elif "java" in topic_lower or "oop" in topic_lower or "object oriented" in topic_lower:
            if style == "visual":
                return [
                    {"type": "text", "content": "### Java & OOP Inheritance Structure\n\nJava is a strongly typed, class-based object-oriented programming language."},
                    {"type": "diagram", "content": "graph TD\n    Abstract[Abstract: Asset] --> Class1[Class: RealEstate]\n    Abstract --> Class2[Class: Stock]\n    Class1 --> Inst1[Instance: 123 Main St]\n    Class2 --> Inst2[Instance: GOOGL]"}
                ]
            elif style == "kinesthetic":
                return [
                    {"type": "text", "content": "### Implementing a Custom Java Interface\n\nLet's write a standard class inheritance and interface implementation in Java."},
                    {"type": "exercise", "content": "**Task:** Implement the Runnable interface in Java.\n\n**Solution Class:**\n```java\npublic class CustomWorker implements Runnable {\n    @Override\n    public void run() {\n        System.out.println(\"Worker thread executing.\");\n    }\n}\n```"}
                ]
            else:
                return [
                    {"type": "text", "content": "### Deep-Dive: Java & OOP Foundations\n\n* **Core Java Runtimes**: Compiled source code (.java) translates to platform-independent bytecode (.class) executed by the Java Virtual Machine (JVM).\n* **Four pillars of OOP**:\n  - **Encapsulation**: Hiding internal state via private variables and public getters/setters.\n  - **Inheritance**: Subclasses sharing and expanding parental definitions.\n  - **Polymorphism**: Interface functions executing custom subclass actions dynamically.\n  - **Abstraction**: Defining contracts (interfaces/abstract classes) hiding implementation details."}
                ]
        else:
            if style == "visual":
                return [
                    {"type": "text", "content": f"### Architectural Framework of {topic}\n\nLet's trace the service boundaries and database connections for **{topic}**."},
                    {"type": "diagram", "content": f"graph TD\n    A[Client User] --> B[Controller Interface]\n    B --> C[Service Logic: {topic}]\n    C --> D[Data Persistence]"}
                ]
            elif style == "kinesthetic":
                return [
                    {"type": "text", "content": f"### Coding Lab: {topic}\n\nLet's construct a simple functional model or script for **{topic}**."},
                    {"type": "exercise", "content": f"**Task:** Write a config module setting up dependencies for **{topic}**.\n\n**Solution Checklist:**\n1. Define environment variables.\n2. Bind listener connections.\n3. Run connectivity checks."}
                ]
            else:
                return [
                    {"type": "text", "content": f"### Core Specifications: {topic}\n\n* **Primary Function**: **{topic}** represents a modular software design pattern in distributed system engineering.\n* **Key Strengths**:\n  - Promotes separation of concerns and high modularity.\n  - Reduces data dependencies between components.\n* **Deployment Best Practices**:\n  - Implement resource health checks.\n  - Set alert limits based on memory consumption metrics."}
                ]

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
