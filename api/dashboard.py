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
from schemas.dashboard import DashboardSummaryResponse, InterviewScoreBreakdown

router = APIRouter(prefix="/dashboard", tags=["Dashboard Aggregation"])

@router.get("/", response_model=DashboardSummaryResponse)
def get_dashboard_summary(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    profile = db.query(Profile).filter(Profile.user_id == current_user.id).first()
    
    # Resume metrics
    latest_resume = db.query(Resume).filter(
        Resume.user_id == current_user.id
    ).order_by(Resume.uploaded_at.desc()).first()
    latest_resume_score = latest_resume.score if latest_resume else 0
    latest_ats_score = latest_resume.ats_score if latest_resume else 0
    keyword_count = latest_resume.keyword_count if latest_resume else 44

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
    
    if total_interviews > 0:
        avg_score = sum(i.average_score for i in interviews) / total_interviews
        avg_tech = sum(i.technical_score for i in interviews) / total_interviews
        avg_comm = sum(i.communication_score for i in interviews) / total_interviews
        avg_behav = sum(i.behavioral_score for i in interviews) / total_interviews
        avg_conf = sum(i.confidence_score for i in interviews) / total_interviews
        avg_star = sum(i.star_score for i in interviews) / total_interviews
    else:
        avg_score, avg_tech, avg_comm, avg_behav, avg_conf, avg_star = 82.0, 88.0, 79.0, 79.0, 74.0, 80.0

    # Calculate overall user readiness score (0 - 100%)
    overall_readiness = int(
        (latest_resume_score * 0.3) +
        (roadmap_progress * 0.3) +
        (avg_score * 0.4)
    )
    overall_readiness = max(0, min(100, overall_readiness if overall_readiness > 0 else 72))

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
        recommendations.append("Update resume keywords to improve your ATS score.")

    if not recommendations:
        recommendations.append("Keep completing your roadmap steps to maintain 100% readiness!")

    return DashboardSummaryResponse(
        user_id=current_user.id,
        full_name=current_user.full_name,
        target_role=profile.target_role if profile else "Backend Engineer",
        target_company=profile.target_company if profile else "Target Tech Company",
        interview_date=profile.interview_date if profile else None,
        overall_readiness_score=overall_readiness,
        latest_resume_score=latest_resume_score,
        latest_ats_score=latest_ats_score,
        keyword_count=keyword_count,
        roadmap_progress_percentage=roadmap_progress,
        total_notes_count=total_notes,
        bookmarked_notes_count=bookmarked_notes,
        total_interviews_conducted=total_interviews,
        interview_scores=InterviewScoreBreakdown(
            overall_score=round(avg_score, 1),
            technical_score=round(avg_tech, 1),
            communication_score=round(avg_comm, 1),
            behavioral_score=round(avg_behav, 1),
            confidence_score=round(avg_conf, 1),
            star_score=round(avg_star, 1)
        ),
        weak_topics=weak_topics,
        recommendations=recommendations,
    )
