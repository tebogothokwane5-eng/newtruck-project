from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from backend.database import get_db
from backend.models.user import Feedback, User

from backend.schemas import FeedbackCreate, FeedbackOut

router = APIRouter(prefix="/feedback", tags=["feedback"])


# ---------------- CREATE FEEDBACK ----------------
@router.post("/", status_code=status.HTTP_201_CREATED)
def submit_feedback(data: FeedbackCreate, db: Session = Depends(get_db)):

    fb = Feedback(**data.dict())
    db.add(fb)
    db.commit()
    db.refresh(fb)

    return {
        "status": "submitted",
        "feedback_id": fb.id
    }


# ---------------- GET FEEDBACK FOR JOB ----------------
@router.get("/job/{job_id}", response_model=List[FeedbackOut])
def get_feedback(job_id: int, db: Session = Depends(get_db)):

    feedbacks = db.query(Feedback).filter(
        Feedback.job_id == job_id
    ).all()

    if not feedbacks:
        raise HTTPException(
            status_code=404,
            detail="No feedback found for this job"
        )

    return feedbacks


# ---------------- ALL FEEDBACK (ADMIN DASHBOARD) ----------------
@router.get("/all-feedback")
def all_feedback(db: Session = Depends(get_db)):

    feedbacks = db.query(Feedback).all()

    output = []

    for f in feedbacks:

        # SAFE RELATION ACCESS
        truck_owner = getattr(f, "truck_owner", None)
        contractor = getattr(f, "contractor", None)

        output.append({
            "id": f.id,
            "job_id": f.job_id,
            "rating": f.rating,
            "comment": f.comment,

            "truck_owner": truck_owner.username if truck_owner else None,
            "contractor": contractor.username if contractor else None
        })

    return output