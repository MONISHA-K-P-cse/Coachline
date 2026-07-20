import os
from fastapi.testclient import TestClient
from main import app
from core.database import Base, engine

# Ensure fresh DB tables for test run
Base.metadata.drop_all(bind=engine)
Base.metadata.create_all(bind=engine)

client = TestClient(app)

def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200, response.text
    assert response.json() == {"status": "healthy"}

def test_user_registration_and_login():
    # Register
    reg_payload = {
        "email": "testuser@coachline.ai",
        "password": "SecurePassword123!",
        "full_name": "Test Engineer",
        "target_role": "Backend Engineer"
    }
    response = client.post("/api/auth/register", json=reg_payload)
    assert response.status_code == 201, response.text
    data = response.json()
    assert data["email"] == reg_payload["email"]
    assert data["full_name"] == reg_payload["full_name"]

    # Login
    login_payload = {
        "email": "testuser@coachline.ai",
        "password": "SecurePassword123!"
    }
    response = client.post("/api/auth/login", json=login_payload)
    assert response.status_code == 200, response.text
    token_data = response.json()
    assert "access_token" in token_data
    token = token_data["access_token"]

    # Get /me
    headers = {"Authorization": f"Bearer {token}"}
    me_resp = client.get("/api/auth/me", headers=headers)
    assert me_resp.status_code == 200, me_resp.text
    assert me_resp.json()["email"] == "testuser@coachline.ai"

def test_dashboard_aggregation():
    # Login to get token
    login_payload = {
        "email": "testuser@coachline.ai",
        "password": "SecurePassword123!"
    }
    token_resp = client.post("/api/auth/login", json=login_payload)
    token = token_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    response = client.get("/api/dashboard/", headers=headers)
    assert response.status_code == 200, response.text
    data = response.json()
    assert "latest_resume_score" in data
    assert "roadmap_progress_percentage" in data
    assert "total_notes_count" in data

def test_roadmap_and_notes():
    token_resp = client.post("/api/auth/login", json={"email": "testuser@coachline.ai", "password": "SecurePassword123!"})
    token = token_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Generate roadmap
    rm_resp = client.post("/api/roadmap/generate", json={"target_role": "Backend Engineer"}, headers=headers)
    assert rm_resp.status_code == 200, rm_resp.text
    rm_data = rm_resp.json()
    assert rm_data["target_role"] == "Backend Engineer"
    assert len(rm_data["steps_json"]) > 0

    # Create Note
    note_resp = client.post("/api/notes/", json={
        "topic": "SQL Indexing",
        "title": "B-Tree vs Hash Indexes",
        "content": "B-Tree handles range queries well, Hash is fast for exact match.",
        "is_bookmarked": True
    }, headers=headers)
    assert note_resp.status_code == 201, note_resp.text
    assert note_resp.json()["is_bookmarked"] == True

if __name__ == "__main__":
    test_health_check()
    print("Health check passed.")
    test_user_registration_and_login()
    print("Registration and authentication passed.")
    test_dashboard_aggregation()
    print("Dashboard aggregation passed.")
    test_roadmap_and_notes()
    print("Roadmap generation & notes CRUD passed.")
    print("\nALL VERIFICATION TESTS PASSED SUCCESSFULLY!")
