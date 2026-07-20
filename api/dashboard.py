from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func

from core.database import get_db
from core.auth import get_current_user
from models.user import User, Profile
from models.resume import Resume
from models.roadmap import Roadmap, Note
from models.interview import InterviewSession
from models.mastery import TopicMastery
from schemas.dashboard import DashboardSummaryResponse

router = APIRouter(prefix="/dashboard", tags=["Dashboard Aggregation"])

@router.get("/", response_model=DashboardSummaryResponse)
def get_dashboard_summary(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    profile = db.query(Profile).filter(Profile.user_id == current_user.id).first()
    
    # Resume score & ATS score
    latest_resume = db.query(Resume).filter(
        Resume.user_id == current_user.id
    ).order_by(Resume.uploaded_at.desc()).first()
    latest_resume_score = latest_resume.score if latest_resume else 0
    latest_ats_score = latest_resume.ats_score if latest_resume else 0

    # Roadmap progress
    latest_roadmap = db.query(Roadmap).filter(
        Roadmap.user_id == current_user.id
    ).order_by(Roadmap.created_at.desc()).first()
    roadmap_progress = latest_roadmap.progress_percentage if latest_roadmap else 0

    # Notes counts
    total_notes = db.query(func.count(Note.id)).filter(Note.user_id == current_user.id).scalar() or 0
    bookmarked_notes = db.query(func.count(Note.id)).filter(
        Note.user_id == current_user.id,
        Note.is_bookmarked == True
    ).scalar() or 0

    # Interview metrics
    interviews = db.query(InterviewSession).filter(InterviewSession.user_id == current_user.id).all()
    total_interviews = len(interviews)
    avg_score = (
        sum(i.average_score for i in interviews) / total_interviews
        if total_interviews > 0
        else 0.0
    )

    # Weak topics & Recommendations
    weak_masteries = db.query(TopicMastery).filter(
        TopicMastery.user_id == current_user.id,
        TopicMastery.mastery_score < 70.0
    ).all()
    weak_topics = [m.topic for m in weak_masteries]

    recommendations = []
    if weak_topics:
        for wt in weak_topics[:2]:
            recommendations.append(f"Review Study Note & take a target practice mock interview on '{wt}'.")
    if total_interviews == 0:
        recommendations.append("Conduct your first AI Mock Interview to assess baseline interview readiness.")
    if latest_resume_score < 80:
        recommendations.append("Update resume metrics to improve your ATS score.")

    if not recommendations:
        recommendations.append("Keep completing your roadmap steps to maintain 100% readiness!")

    return DashboardSummaryResponse(
        user_id=current_user.id,
        full_name=current_user.full_name,
        target_role=profile.target_role if profile else "Backend Engineer",
        target_company=profile.target_company if profile else "Target Tech Company",
        latest_resume_score=latest_resume_score,
        latest_ats_score=latest_ats_score,
        roadmap_progress_percentage=roadmap_progress,
        total_notes_count=total_notes,
        bookmarked_notes_count=bookmarked_notes,
        total_interviews_conducted=total_interviews,
        average_interview_score=round(avg_score, 1),
        weak_topics=weak_topics,
        recommendations=recommendations,
    )
