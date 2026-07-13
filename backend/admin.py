# backend/routes/admin.py
import os
import mimetypes
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models.user import User, Job, JobApplication, Feedback
from backend.models.payment import Payment
from backend.routes.auth import get_current_user
from backend.utils.email import send_email

# ---------------- ROUTER ----------------
router = APIRouter(prefix="/jobs/admin", tags=["admin"])

BASE_URL ="https://newtruck-project.onrender.com"
UPLOAD_DIR = "backend/uploads/truck_packs"
os.makedirs(UPLOAD_DIR, exist_ok=True)

# ---------------- HELPERS ----------------
def admin_required(current_user: User = Depends(get_current_user)):
    role = getattr(current_user.role, "value", str(current_user.role))
    if role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access only")
    return current_user

# ---------------- USERS ----------------
@router.get("/all-users")
def get_all_users(db: Session = Depends(get_db), current_user: User = Depends(admin_required)):
    users = db.query(User).all()
    return [
        {
            "id": u.id,
            "username": u.username,
            "email": u.email,
            "role": getattr(u.role, "value", str(u.role)),
            "is_active": u.is_active
        }
        for u in users
    ]

@router.get("/users")
def get_all_users_alias(db: Session = Depends(get_db), current_user: User = Depends(admin_required)):
    return get_all_users(db, current_user)

@router.put("/users/{user_id}/approve")
def approve_user(user_id: int, db: Session = Depends(get_db), current_user: User = Depends(admin_required)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    user.is_active = True
    db.commit()
    db.refresh(user)
    return {"detail": "User approved"}

@router.put("/users/{user_id}/evaluate")
def evaluate_user(user_id: int, background_tasks: BackgroundTasks, db: Session = Depends(get_db), current_user: User = Depends(admin_required)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    user.is_active = False
    db.commit()
    db.refresh(user)
    subject = "Your documents are under verification"
    body = f"Hello {user.username},\n\nYour submitted documents are being verified. You will receive another email once your account is approved."
    background_tasks.add_task(send_email, user.email, subject, body)
    return {"detail": "User set to under verification and notification will be sent"}

@router.delete("/users/{user_id}/delete")
def delete_user(user_id: int, db: Session = Depends(get_db), current_user: User = Depends(admin_required)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    db.delete(user)
    db.commit()
    return {"detail": "User deleted"}

# ---------------- JOBS ----------------
@router.get("/all-jobs")
def get_all_jobs(db: Session = Depends(get_db), current_user: User = Depends(admin_required)):
    jobs = db.query(Job).all()
    return [
        {
            "id": job.id,
            "title": job.title,
            "description": job.description,
            "contractor_id": job.contractor_id,
            "target_limit": job.target_limit,
            "status": getattr(job.status, "value", str(job.status)),
            "applicant_count": job.applicant_count
        }
        for job in jobs
    ]

# ---------------- APPLICATIONS ----------------
@router.get("/all-applications")
def get_all_applications(db: Session = Depends(get_db), current_user: User = Depends(admin_required)):
    applications = db.query(JobApplication).all()
    result = []
    for app in applications:
        filename = os.path.basename(app.truck_pack) if app.truck_pack else None
        result.append({
            "application_id": app.id,
            "job_id": app.job_id,
            "truck_owner_id": app.truck_owner_id,
            "status": app.status,
            "truck_pack": app.truck_pack,
            "truck_pack_url": f"{BASE_URL}/jobs/admin/uploads/truck_packs/{filename}" if filename else None
        })
    return result

# ---------------- FEEDBACK ----------------
@router.get("/all-feedback")
def get_all_feedback(db: Session = Depends(get_db), current_user: User = Depends(admin_required)):
    feedbacks = db.query(Feedback).all()
    return [
        {
            "id": fb.id,
            "job_id": fb.job_id,
            "rating": fb.rating,
            "comment": fb.comment
        }
        for fb in feedbacks
    ]

# ---------------- TRUCK PACK FILE SERVING ----------------
@router.get("/uploads/truck_packs/{filename}", include_in_schema=False)
def serve_truck_pack(filename: str):
    path = os.path.join(UPLOAD_DIR, filename)
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="Truck pack not found")
    media_type, _ = mimetypes.guess_type(path)
    return FileResponse(
        path,
        media_type=media_type or "application/octet-stream",
        headers={"Content-Disposition": f'inline; filename="{filename}"'}
    )

# ---------------- USER DETAIL WITH DOCUMENTS ----------------
@router.get("/users/{user_id}")
def get_user_by_id(user_id: int, db: Session = Depends(get_db), current_user: User = Depends(admin_required)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    applications = db.query(JobApplication).filter(JobApplication.truck_owner_id == user_id).all()
    documents = []

    if user.document:
        documents.append({"type": "Registration Document", "url": user.document})

    for app in applications:
        if app.truck_pack:
            documents.append({"type": f"Truck Pack (App {app.id})", "url": app.truck_pack})

    return {
        "id": user.id,
        "username": user.username,
        "email": user.email,
        "role": getattr(user.role, "value", str(user.role)),
        "is_active": user.is_active,
        "documents": documents
    }

# ---------------- DEBUG ----------------
@router.get("/users-debug")
def users_debug(db: Session = Depends(get_db)):
    return [{"id": u.id, "username": u.username, "email": u.email, "is_active": u.is_active} for u in db.query(User).all()]

# ---------------- PAYMENTS ----------------
@router.get("/all-payments")
def get_all_payments(db: Session = Depends(get_db), current_user: User = Depends(admin_required)):
    payments = db.query(Payment).all()
    return [
        {
            "id": p.id,
            "job_id": p.job_id,
            "contractor_id": p.contractor_id,
            "truck_owner_id": p.truck_owner_id,
            "amount": p.amount,
            "status": p.status,
            "reference": p.reference,
            "created_at": p.created_at.isoformat() if p.created_at else None
        }
        for p in payments
    ]
