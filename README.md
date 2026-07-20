# Coachline - Backend & Infrastructure

Backend service powering the **Coachline** platform. Built with **FastAPI**, **SQLAlchemy 2.0**, **Alembic**, **JWT Authentication**, and **WebSockets**.

---

## 🔄 User Workflow & API Mapping

The backend is explicitly designed around the core end-to-end user journey:

```
    ┌─────────────────────────┐
    │       User Joins        │  ---> POST /api/auth/register & POST /api/auth/login
    └────────────┬────────────┘
                 │
                 ▼
    ┌─────────────────────────┐
    │   AI Understands Goal   │  ---> POST /api/resume/upload (pdfplumber + Resume Agent)
    └────────────┬────────────┘
                 │
                 ▼
    ┌─────────────────────────┐
    │Builds Preparation Roadmap│ ---> POST /api/roadmap/generate & GET /api/roadmap/
    └────────────┬────────────┘
                 │
                 ▼
    ┌─────────────────────────┐
    │         Teaches         │  ---> GET /api/notes/ & POST /api/notes/ (Refresher Notes)
    └────────────┬────────────┘
                 │
                 ▼
    ┌─────────────────────────┐
    │    Conducts Interview   │  ---> WS /api/interview/ws/{user_id} (Turn-by-turn)
    └────────────┬────────────┘
                 │
                 ▼
    ┌─────────────────────────┐
    │   Analyzes Performance  │  ---> Evaluation Agent scoring & weak topics extraction
    └────────────┬────────────┘
                 │
                 ▼
    ┌─────────────────────────┐
    │     Updates Roadmap     │  ---> core/mastery.py feedback loop updates TopicMastery
    └────────────┬────────────┘       & generates targeted notes for weak topics
                 │
                 ▼
    ┌─────────────────────────┐
    │  Repeats Until Ready    │  ---> GET /api/dashboard/ tracks overall readiness %
    └─────────────────────────┘
```

---

## 📂 Project Structure

```
Coachline/
├── main.py               # FastAPI entrypoint, CORS & docs
├── requirements.txt      # Dependencies
├── alembic.ini           # Alembic config
├── alembic/              # Database migration scripts
├── core/
│   ├── config.py         # App settings & env variables
│   ├── database.py       # SQLAlchemy engine & session setup
│   ├── auth.py           # JWT auth & password hashing
│   └── mastery.py        # Agentic feedback loop logic
├── models/               # SQLAlchemy ORM models
│   ├── user.py
│   ├── resume.py
│   ├── roadmap.py
│   ├── interview.py
│   └── mastery.py
├── schemas/              # Pydantic request/response schemas
├── api/                  # API Routers
│   ├── auth.py
│   ├── resume.py
│   ├── roadmap.py
│   ├── notes.py
│   ├── interview.py
│   └── dashboard.py
├── mocks/                # P3 Agent resilient offline mocks
└── test_backend.py       # Automated verification test suite
```

---

## 🛠️ Quick Start

```bash
# 1. Activate virtual environment
source venv/bin/activate

# 2. Run database migrations
alembic upgrade head

# 3. Start Uvicorn development server
uvicorn main.py:app --reload --port 8000
```

Access interactive API documentation at **`http://127.0.0.1:8000/docs`**.
