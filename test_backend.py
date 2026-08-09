import os
# Use a separate SQLite database for tests to prevent overwriting development data
os.environ["DATABASE_URL"] = "sqlite:///./test_coachline.db"

from fastapi.testclient import TestClient
from backend.main import app
from backend.core.database import Base, engine

# Reset DB for test run
Base.metadata.drop_all(bind=engine)
Base.metadata.create_all(bind=engine)

client = TestClient(app)

def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200, response.text
    assert response.json() == {"status": "healthy"}

def test_user_registration_and_login():
    reg_payload = {
        "email": "archtest@coachline.ai",
        "password": "SecurePassword123!",
        "full_name": "Architecture Engineer",
        "target_role": "Backend Lead",
        "target_company": "Stripe"
    }
    response = client.post("/api/auth/register", json=reg_payload)
    assert response.status_code == 201, response.text
    data = response.json()
    assert data["email"] == reg_payload["email"]
    assert data["profile"]["target_company"] == "Stripe"

    login_payload = {
        "email": "archtest@coachline.ai",
        "password": "SecurePassword123!"
    }
    response = client.post("/api/auth/login", json=login_payload)
    assert response.status_code == 200, response.text
    return response.json()["access_token"]

def test_job_description_upload(token: str):
    headers = {"Authorization": f"Bearer {token}"}
    jd_payload = {
        "target_role": "Backend Lead",
        "company_name": "Stripe",
        "jd_text": "We are seeking a Backend Lead with extensive experience in distributed systems and Redis."
    }
    response = client.post("/api/job-description/upload", json=jd_payload, headers=headers)
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["company_name"] == "Stripe"
    assert len(data["skill_gaps"]) > 0

def test_mentor_chat(token: str):
    headers = {"Authorization": f"Bearer {token}"}
    chat_payload = {"message": "How do I prepare for distributed caching interview questions?"}
    response = client.post("/api/mentor/chat", json=chat_payload, headers=headers)
    assert response.status_code == 200, response.text
    messages = response.json()
    assert len(messages) == 2
    assert messages[0]["sender"] == "user"
    assert messages[1]["sender"] == "mentor"

def test_dashboard_aggregation(token: str):
    headers = {"Authorization": f"Bearer {token}"}
    response = client.get("/api/dashboard/", headers=headers)
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["target_company"] == "Stripe"
    assert "recommendations" in data

def test_roadmap_practice_questions_and_remediation(token: str):
    headers = {"Authorization": f"Bearer {token}"}
    
    # 1. Generate roadmap
    gen_res = client.post("/api/roadmap/generate", json={"target_role": "Backend Lead"}, headers=headers)
    assert gen_res.status_code == 200, gen_res.text
    roadmap = gen_res.json()
    assert "steps_json" in roadmap
    steps = roadmap["steps_json"]
    assert len(steps) > 0

    # Verify every step has a syllabus and at least 5 practice questions
    for step in steps:
        assert "syllabus" in step and len(step["syllabus"]) > 0
        assert "questions" in step and len(step["questions"]) >= 5

    # 2. Evaluate a practice question with an incomplete/poor answer (scoring < 50%)
    step1_q1 = steps[0]["questions"][0]
    eval_payload = {
        "question": step1_q1,
        "user_answer": "idk"
    }
    eval_res = client.post(
        f"/api/roadmap/{roadmap['id']}/steps/1/evaluate-question",
        json=eval_payload,
        headers=headers
    )
    assert eval_res.status_code == 200, eval_res.text
    eval_data = eval_res.json()
    assert eval_data["score"] < 50.0
    assert eval_data["passed"] is False
    assert eval_data["generated_new_question"] is not None
    assert len(eval_data["step_questions"]) > len(steps[0]["questions"])

if __name__ == "__main__":
    test_health_check()
    print("Health check passed.")
    token = test_user_registration_and_login()
    print("Registration with Target Company passed.")
    test_job_description_upload(token)
    print("JD Upload & Skill Gap Analysis passed.")
    test_mentor_chat(token)
    print("Career Mentor Chat passed.")
    test_dashboard_aggregation(token)
    print("Dashboard Aggregation with Recommendations passed.")
    test_roadmap_practice_questions_and_remediation(token)
    print("Roadmap 5+ Practice Questions & Adaptive Question Generation (<50% score) passed.")
    print("\nALL ARCHITECTURE VERIFICATION TESTS PASSED SUCCESSFULLY!")

