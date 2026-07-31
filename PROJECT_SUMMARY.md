# Coachline: AI-Powered Career Mentor & Interview Preparation Ecosystem

Coachline is a premium, full-stack web application designed to help software engineers prepare for technical interviews. It analyzes job descriptions, maps skill gaps, builds custom roadmaps, generates personalized study notes adapted to VARK learning styles, runs conversational mentor chats, conducts interactive voice mock interviews, and optimizes resumes with format-preserving PDF downloads.

---

## 1. System Architecture

Below is the end-to-end data flow tracing how a candidate interacts with the frontend interface, backend API endpoints, database structures, and offline agent fallbacks:

```mermaid
graph TD
    %% Frontend Layer
    subgraph Frontend (Vite + React + TS)
        UI[Candidate Dashboard]
        WS[Workspace Panel]
        IC[Interactive Chat]
        MIC[Voice Mock Interview]
        RO[Resume Optimizer Panel]
    end

    %% Backend Layer
    subgraph Backend (FastAPI Web Server)
        API[API Router]
        Auth[JWT Authentication Handler]
        Notes[Notes Agent System]
        Mentor[Mentor Agent System]
        Interview[Interview Pilot Agent]
        Resume[Resume Optimizer & Parser]
    end

    %% Database Layer
    subgraph Storage & Persistence
        DB_DEV[(coachline.db - Dev Database)]
        DB_TEST[(test_coachline.db - Isolated Test DB)]
    end

    %% AI Agent Layer
    subgraph AI Foundation (Granite Client)
        LLM[Granite LLM Client]
        RAG[RAG Retrieval & Vector Store]
        Registry[Topic Registry & Fallbacks]
    end

    %% Connections
    UI <--> API
    WS <--> API
    IC <--> API
    MIC <--> API
    RO <--> API

    API --> Auth
    API --> Notes
    API --> Mentor
    API --> Interview
    API --> Resume

    Notes --> Registry
    Mentor --> Registry
    Interview --> LLM
    Resume --> LLM

    Auth --> DB_DEV
    Auth --> DB_TEST
```

---

## 2. Technology Used

### I. Data Prep Kit
* **Document Processing**: Extracted text blocks, headers, and metadata from raw text transcripts and curriculum files to chunk data uniformly.
* **Resume Parsing**: Utilized `python-docx` and string preprocessing scripts to sanitize, align, and clean leading indents, tabs, and bold highlights in Word and Markdown resume files.

### II. Granite
* **Foundation Models**: Built around **IBM's Granite foundation models** (e.g. `granite-3.0` models like Granite 3B/1B parameters) to generate context-grounded text.
* **Granite client orchestration**: Implemented in [granite_client.py](file:///Users/monisha/Desktop/Coachline/ai/agents/granite_client.py) to manage system prompts, formatting rules, temperature, and offline local Ollama model simulation wrappers.

### III. RAG (Retrieval-Augmented Generation)
* **Cloud Platform**: Powered by **IBM (watsonx.ai)**.
* **Document Retrieval**: Indexes core computer science modules (data structures, DBMS, OOP, systems architecture, machine learning) inside a local `ChromaDB` vector database. It queries the vector space via a SentenceTransformers embedding model (`all-MiniLM-L6-v2`) and appends role-grounded context to Granite prompt templates before final text generation.

### IV. Agentic Frameworks
* **Cloud Platform**: Powered by **IBM (watsonx.ai)**.
* **Specialized AI Agents**: Implemented as cooperative, single-task agents:
  * **Resume Agent**: Validates ATS keyword density and constructs format-preserving PDF layouts.
  * **Interview Pilot Agent**: Coordinates real-time mock interview progress, scoring answers dynamically on technical accuracy, behavioral metrics, and STAR methods.
  * **Notes Agent**: Adapts generation formats dynamically into Visual diagrams, Kinesthetic programming exercises, or Reading summaries.
  * **Mentor Agent**: Contextual chatbot replying dynamically to target role preparational questions.

---

## 3. Core Features & Implementation

### 📋 Resume Upload & ATS Optimization
* **Dual Parsing**: Supports uploading standard text, raw markdown, and Microsoft Word files (`.docx`) using a backend `python-docx` file parser.
* **Side-by-Side Optimizer**: Compares original resumes with Granite-optimized enhancements in real-time, showing the exact wording edits side-by-side.
* **Format-Preserving Exporter**: Generates and downloads the revised resume as a PDF via `ReportLab`. It preserves 100% of original leading margins, text indentation, line breaks, bold markdown, headers, and bullet points.

### 🎙️ Mock Interview Pilot
* **Voice Synthesis (Text-to-Speech)**: Allows candidates to click a **"Read Aloud"** button to hear the interviewer's technical questions spoken out loud using the browser's native `SpeechSynthesis`.
* **Voice Recognition (Speech-to-Text)**: Allows candidates to answer questions hands-free via an **"Answer with Voice"** recording panel powered by the native browser `SpeechRecognition` API.
* **Score Evaluation**: Rates performance on technical logic, communication flow, and STAR structured guidelines, offering feedback and weak-area flags.

### 📚 VARK Multi-Style Study Notes
* **Adaptive Styling**: Generates custom study notes matching the candidate's core VARK profile (Visual flowcharts, Kinesthetic programming labs, Reading prose).
* **Topic-Specific Registry**: Contains custom material for core fields (DBMS isolation levels, DS linked lists and Big O, Docker namespaces, Redis cache-aside caching, JWT stateless authentication, Java OOP pillars, and ML gradient steps).

---

## 4. Database Dev Isolation

To protect manual dev accounts and registered dashboard profiles, the test suite is isolated from the development database:

* **Development DB (`coachline.db`)**: Stores target role choices, dashboard roadmap tasks, saved interview summaries, and custom bookmarks.
* **Test DB (`test_coachline.db`)**: Tests automatically override `DATABASE_URL` during start execution in [test_backend.py](file:///Users/monisha/Desktop/Coachline/test_backend.py). This launches, tests, and drops tables on a separate file, keeping dev database states 100% untouched.

---

## 5. Run & Verification Guide

### Starting the Applications
> [!NOTE]
> Ensure you are inside the Python virtual environment (`venv`) before executing backend tasks.

1. **Start Backend Server**:
   ```bash
   venv/bin/python -m uvicorn backend.main:app --port 8000
   ```
2. **Start Frontend Client**:
   ```bash
   cd frontend
   PORT=8443 npm run dev
   ```
   *The frontend is configured to run securely on port **8443**.*

### Running Automated Verification
To run the automated API suite verifying registration, JD uploads, skill analysis, mentor chats, and dashboard routing:
```bash
PYTHONPATH=. venv/bin/python test_backend.py
```
*Expected output:* `ALL ARCHITECTURE VERIFICATION TESTS PASSED SUCCESSFULLY!`
