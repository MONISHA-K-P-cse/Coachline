from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
import httpx
import json
import os

from core.database import get_db
from core.auth import get_current_user
from core.config import settings
from models.user import User
from models.roadmap import Roadmap
from schemas.roadmap import RoadmapCreate, RoadmapResponse

router = APIRouter(prefix="/roadmap", tags=["Roadmap & Notes Storage"])

MOCK_ROADMAP_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "mocks", "roadmap_agent.json")

def load_mock_roadmap() -> dict:
    if os.path.exists(MOCK_ROADMAP_PATH):
        with open(MOCK_ROADMAP_PATH, "r") as f:
            return json.load(f)
    return {
        "title": "Backend Engineering Roadmap",
        "steps": [
            {"step_number": 1, "title": "Python Basics", "description": "Master fundamentals", "estimated_hours": 10, "status": "completed"},
            {"step_number": 2, "title": "FastAPI & Databases", "description": "Build APIs", "estimated_hours": 15, "status": "in_progress"}
        ]
    }

@router.post("/generate", response_model=RoadmapResponse)
async def generate_roadmap(
    roadmap_in: RoadmapCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    roadmap_data = None
    try:
        async with httpx.AsyncClient(timeout=settings.AGENT_TIMEOUT_SECONDS) as client:
            resp = await client.post(
                f"{settings.P3_AGENT_BASE_URL}/agent/roadmap/generate",
                json={"target_role": roadmap_in.target_role, "user_id": current_user.id}
            )
            if resp.status_code == 200:
                roadmap_data = resp.json()
    except Exception:
        roadmap_data = load_mock_roadmap()

    if not roadmap_data:
        roadmap_data = load_mock_roadmap()

    roadmap = Roadmap(
        user_id=current_user.id,
        title=roadmap_in.title or roadmap_data.get("title", f"{roadmap_in.target_role} Roadmap"),
        target_role=roadmap_in.target_role,
        steps_json=roadmap_data.get("steps", []),
        progress_percentage=25,
    )

    db.add(roadmap)
    db.commit()
    db.refresh(roadmap)

    return roadmap


@router.get("/", response_model=List[RoadmapResponse])
def get_user_roadmaps(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return db.query(Roadmap).filter(Roadmap.user_id == current_user.id).all()


@router.get("/{roadmap_id}", response_model=RoadmapResponse)
def get_roadmap_by_id(
    roadmap_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    roadmap = db.query(Roadmap).filter(
        Roadmap.id == roadmap_id,
        Roadmap.user_id == current_user.id
    ).first()
    if not roadmap:
        raise HTTPException(status_code=404, detail="Roadmap not found")
    return roadmap
