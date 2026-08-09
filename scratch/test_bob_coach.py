import sys
import os
import asyncio

sys.path.append("/Users/monisha/Desktop/Coachline-1")

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from backend.core.database import Base
from backend.models.user import User, Profile
from backend.models.bob import BobCoachSession
from backend.models.mastery import TopicMastery
from backend.models.roadmap import Roadmap
from backend.api.bob_coach import start_scenario, respond_to_scenario, get_session_details
from backend.schemas.bob_coach import BobCoachStartRequest, BobCoachRespondRequest

def test_bob_coach_flow():
    # Setup in-memory SQLite DB
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)
    
    db = SessionLocal()
    
    # 1. Create user and profile
    user = User(email="architect@coachline.com", hashed_password="pw")
    db.add(user)
    db.commit()
    db.refresh(user)
    
    profile = Profile(user_id=user.id, target_role="Backend Engineer", experience_level="Senior")
    db.add(profile)
    
    # Create empty roadmap
    roadmap = Roadmap(
        user_id=user.id,
        title="Engineering Roadmap",
        target_role="Backend Engineer",
        steps_json=[]
    )
    db.add(roadmap)
    db.commit()
    db.refresh(user)

    print("--- 1. Start Bob Coach Scenario ---")
    
    async def run_start():
        req = BobCoachStartRequest(target_role="Backend Engineer", language="Python")
        res = await start_scenario(req, db=db, current_user=user)
        return res
        
    loop = asyncio.get_event_loop()
    start_res = loop.run_until_complete(run_start())
    session_id = start_res["session_id"]
    print("Start Result:", start_res)
    assert session_id > 0
    assert "next_question" in start_res
    print("START SCENARIO PASSED!")

    print("\n--- 2. Send First Candidate Response (Turn 1) ---")
    
    async def run_respond_1():
        req = BobCoachRespondRequest(session_id=session_id, candidate_response="I would use a doubly linked list and a hash map to implement this cache.")
        res = await respond_to_scenario(req, db=db, current_user=user)
        return res

    respond_res_1 = loop.run_until_complete(run_respond_1())
    print("Turn 1 Result:", respond_res_1)
    assert respond_res_1["completed"] is False
    assert "next_question" in respond_res_1
    print("TURN 1 PASSED!")

    print("\n--- 3. Send Second Candidate Response (Turn 2) ---")
    
    async def run_respond_2():
        req = BobCoachRespondRequest(session_id=session_id, candidate_response="The time complexity of lookup and eviction is O(1). Space complexity is O(Capacity) to store references.")
        res = await respond_to_scenario(req, db=db, current_user=user)
        return res

    respond_res_2 = loop.run_until_complete(run_respond_2())
    print("Turn 2 Result:", respond_res_2)
    assert respond_res_2["completed"] is False
    print("TURN 2 PASSED!")

    print("\n--- 4. Send Third Candidate Response (Turn 3) ---")
    
    async def run_respond_3():
        req = BobCoachRespondRequest(session_id=session_id, candidate_response="If the lookup bounds are null, I will raise a ValueError or return None.")
        res = await respond_to_scenario(req, db=db, current_user=user)
        return res

    respond_res_3 = loop.run_until_complete(run_respond_3())
    print("Turn 3 Result:", respond_res_3)
    assert respond_res_3["completed"] is False
    print("TURN 3 PASSED!")

    print("\n--- 5. Send Fourth Candidate Response (Turn 4) ---")
    
    async def run_respond_4():
        req = BobCoachRespondRequest(session_id=session_id, candidate_response="We would test the happy path eviction sequence and null pointer lookups.")
        res = await respond_to_scenario(req, db=db, current_user=user)
        return res

    respond_res_4 = loop.run_until_complete(run_respond_4())
    print("Turn 4 Result:", respond_res_4)
    assert respond_res_4["completed"] is False
    print("TURN 4 PASSED!")

    print("\n--- 6. Send Fifth Candidate Response (Turn 5 -> Triggers Evaluation) ---")
    
    async def run_respond_5():
        req = BobCoachRespondRequest(session_id=session_id, candidate_response="If memory is tight, I will store keys in memory and values in a partition database stream.")
        res = await respond_to_scenario(req, db=db, current_user=user)
        return res

    respond_res_5 = loop.run_until_complete(run_respond_5())
    print("Final Turn Result:", respond_res_5)
    assert respond_res_5["completed"] is True
    print("FINAL TURN / EVALUATION PASSED!")

    print("\n--- 7. Verify Database Session Evaluation & Mastery/Roadmap updates ---")
    session_details = get_session_details(session_id=session_id, db=db, current_user=user)
    print("Session Score:", session_details["overall_score"])
    print("Evaluation JSON:", session_details["evaluation"])
    
    assert session_details["overall_score"] is not None
    assert "evaluation" in session_details["evaluation"]
    
    # Check topic mastery score updated
    mastery = db.query(TopicMastery).filter(TopicMastery.user_id == user.id).first()
    print("Mastery entry created:", mastery.topic, "Score:", mastery.mastery_score)
    assert mastery is not None
    assert mastery.topic == "System Design"
    
    # Check roadmap step injected
    db.refresh(roadmap)
    print("Roadmap Steps adapted:", roadmap.steps_json)
    assert len(roadmap.steps_json) == 1
    assert "Remedial Practice" in roadmap.steps_json[0]["title"]
    
    print("VERIFICATION COMPLETED SUCCESSFULLY!")
    db.close()

if __name__ == "__main__":
    test_bob_coach_flow()
