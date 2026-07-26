from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime, timedelta
from collections import defaultdict

from backend.core.database import get_db
from backend.core.auth import get_current_user
from backend.models.user import User, Profile
from backend.models.resume import Resume
from backend.models.roadmap import Roadmap, Note
from backend.models.interview import InterviewSession
from backend.models.mastery import TopicMastery
from typing import List

from backend.schemas.dashboard import (
    DashboardSummaryResponse,
    InterviewScoreBreakdown,
    ActivityHeatmapResponse,
    ActivityHeatmapEntry,
    TopicMasteryEntry,
)

router = APIRouter(prefix="/dashboard", tags=["Dashboard Aggregation"])

# Same "not ready" threshold core.mastery already uses for weak topics -
# kept consistent across the app rather than inventing a second number.
READINESS_THRESHOLD = 70.0
PANIC_MODE_DAYS_WINDOW = 2  # "48 hours out" per the product's Panic Mode framing

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
    keyword_count = latest_resume.keyword_count if latest_resume else 0

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

    # Interview metrics - only count completed sessions with a real average
    # score, so a session that was started and abandoned doesn't drag the
    # average down to 0.
    interviews = db.query(InterviewSession).filter(
        InterviewSession.user_id == current_user.id,
        InterviewSession.status == "completed",
    ).all()
    total_interviews = len(interviews)

    if total_interviews > 0:
        avg_score = sum(i.average_score for i in interviews) / total_interviews
        avg_tech = sum(i.technical_score for i in interviews) / total_interviews
        avg_comm = sum(i.communication_score for i in interviews) / total_interviews
        avg_behav = sum(i.behavioral_score for i in interviews) / total_interviews
        avg_conf = sum(i.confidence_score for i in interviews) / total_interviews
        avg_star = sum(i.star_score for i in interviews) / total_interviews
    else:
        # Honest "no data yet" state - no interviews means no interview
        # score, not an optimistic placeholder number.
        avg_score = avg_tech = avg_comm = avg_behav = avg_conf = avg_star = 0.0

    # Calculate overall user readiness score (0 - 100%). Each component is
    # 0 until the user has actually done that step - no baseline floor.
    overall_readiness = int(
        (latest_resume_score * 0.3) +
        (roadmap_progress * 0.3) +
        (avg_score * 0.4)
    )
    overall_readiness = max(0, min(100, overall_readiness))

    # Weak topics & Recommendations
    weak_masteries = db.query(TopicMastery).filter(
        TopicMastery.user_id == current_user.id,
        TopicMastery.mastery_score < READINESS_THRESHOLD,
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

    # Panic Mode: interview is imminent (within PANIC_MODE_DAYS_WINDOW days)
    # and overall readiness is still below the "not ready" threshold.
    days_until_interview = None
    if profile and profile.interview_date:
        days_until_interview = (profile.interview_date.date() - datetime.utcnow().date()).days

    panic_mode = (
        days_until_interview is not None
        and 0 <= days_until_interview <= PANIC_MODE_DAYS_WINDOW
        and overall_readiness < READINESS_THRESHOLD
    )
    if panic_mode:
        recommendations.insert(
            0,
            f"Panic Mode: your interview is in {days_until_interview} day(s) and readiness is still "
            f"below {int(READINESS_THRESHOLD)}%. Focus only on your weakest topics now.",
        )

    return DashboardSummaryResponse(
        user_id=current_user.id,
        full_name=current_user.full_name,
        target_role=profile.target_role if profile else None,
        target_company=profile.target_company if profile else None,
        interview_date=profile.interview_date if profile else None,
        days_until_interview=days_until_interview,
        panic_mode=panic_mode,
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


@router.get("/activity-heatmap", response_model=ActivityHeatmapResponse)
def get_activity_heatmap(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    days: int = 90,
):
    """
    Daily activity counts (interviews started, notes created, resumes
    uploaded) over a rolling window, derived entirely from existing
    timestamp columns - no separate activity-log table.
    """
    since = datetime.utcnow() - timedelta(days=days)
    counts = defaultdict(lambda: {"interviews": 0, "notes": 0, "resumes": 0})

    interview_dates = db.query(InterviewSession.started_at).filter(
        InterviewSession.user_id == current_user.id,
        InterviewSession.started_at >= since,
    ).all()
    for (started_at,) in interview_dates:
        counts[started_at.date().isoformat()]["interviews"] += 1

    note_dates = db.query(Note.created_at).filter(
        Note.user_id == current_user.id,
        Note.created_at >= since,
    ).all()
    for (created_at,) in note_dates:
        counts[created_at.date().isoformat()]["notes"] += 1

    resume_dates = db.query(Resume.uploaded_at).filter(
        Resume.user_id == current_user.id,
        Resume.uploaded_at >= since,
    ).all()
    for (uploaded_at,) in resume_dates:
        counts[uploaded_at.date().isoformat()]["resumes"] += 1

    entries = [
        ActivityHeatmapEntry(
            date=day,
            interviews=c["interviews"],
            notes=c["notes"],
            resumes=c["resumes"],
            total=c["interviews"] + c["notes"] + c["resumes"],
        )
        for day, c in sorted(counts.items())
    ]

    return ActivityHeatmapResponse(days=entries)


@router.get("/topic-mastery", response_model=List[TopicMasteryEntry])
def get_topic_mastery(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return (
        db.query(TopicMastery)
        .filter(TopicMastery.user_id == current_user.id)
        .order_by(TopicMastery.mastery_score.asc())
        .all()
    )
