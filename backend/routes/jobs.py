import os
import time
import shutil
import traceback
from sqlalchemy.orm import Session
from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, Form
from fastapi.responses import FileResponse

from backend.schemas import JobCreate, JobStatusUpdate, AssignOrderPayload
from backend.database import get_db
from backend.routes.auth import get_current_user
from backend.utils.storage import upload_file
from backend.utils.push import send_push_notification

from backend.models.user import (
    User,
    Job,
    JobStatus,
    JobApplication,
    DeliverySlip,
    ApplicationStatus,
    JobComment,
    JobLike
)


router = APIRouter(prefix="/jobs", tags=["Jobs"])

# ----------------- CONFIG -----------------
BASE_URL = "https://newtruck-project.onrender.com"

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

UPLOAD_DIR = os.path.join(BASE_DIR, "uploads", "truck_packs")
UPLOAD_SLIP_DIR = os.path.join(BASE_DIR, "uploads", "delivery_slips")

os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(UPLOAD_SLIP_DIR, exist_ok=True)

# ----------------- HELPERS -----------------
def contractor_required(user: User):
    role = getattr(user.role, "value", str(user.role))
    if role not in ["main_contractor", "admin"]:
        raise HTTPException(status_code=403, detail="Contractor access only")


def truck_owner_required(user: User):
    role = getattr(user.role, "value", str(user.role))
    if role != "truck_owner":
        raise HTTPException(status_code=403, detail="Truck owner access only")

# ✅ FIXED URLS (CRITICAL)
def truck_pack_url(filename: str):
    if filename and filename.startswith("http"):
        return filename
    return f"{BASE_URL}/jobs/uploads/truck_packs/{filename}"

def slip_url(filename: str):
    if filename and filename.startswith("http"):
        return filename
    return f"{BASE_URL}/jobs/uploads/delivery_slips/{filename}"


def slip_url(filename: str):
    return f"{BASE_URL}/jobs/uploads/delivery_slips/{filename}"


# ----------------- FILE SERVING -----------------
@router.get("/uploads/truck_packs/{filename}", include_in_schema=False)
def serve_truck_pack(filename: str):
    path = os.path.join(UPLOAD_DIR, filename)
    if os.path.exists(path):
        return FileResponse(path)
    raise HTTPException(status_code=404, detail="Truck pack not found")


@router.get("/uploads/delivery_slips/{filename}", include_in_schema=False)
def serve_slip(filename: str):
    path = os.path.join(UPLOAD_SLIP_DIR, filename)
    if os.path.exists(path):
        return FileResponse(path)
    raise HTTPException(status_code=404, detail="Slip not found")


# ----------------- CREATE JOB -----------------
@router.post("/")
def create_job(job: JobCreate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    contractor_required(current_user)

    new_job = Job(
        title=job.title.strip(),
        description=job.description,
        contractor_id=current_user.id,
        target_limit=job.target_limit,
        price=job.price,
        status=JobStatus.pending
    )

    db.add(new_job)
    db.commit()
    db.refresh(new_job)
    return new_job


# ----------------- LIST JOBS -----------------
@router.get("/")
def list_jobs(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    contractor_required(current_user)

    jobs = db.query(Job).filter(Job.contractor_id == current_user.id).all()

    output = []

    for job in jobs:
        applications = db.query(JobApplication).filter(JobApplication.job_id == job.id).all()

        apps_data = [
            {
                "application_id": app.id,
                "truck_pack_url": truck_pack_url(app.truck_pack) if app.truck_pack else None,
                "location": getattr(app, "location", None)
            }
            for app in applications
        ]

        created_at = job.created_at.isoformat() if getattr(job, "created_at", None) else None

        output.append({
            "id": job.id,
            "title": job.title or "",
            "description": job.description or "",
            "status": job.status.value if hasattr(job.status, "value") else str(job.status),
            "applicant_count": job.applicant_count or 0,
            "target_limit": job.target_limit or 0,
            "created_at": created_at,
            "applications": apps_data
        })

    return output


# ----------------- AVAILABLE JOBS -----------------
@router.get("/available")
def available_jobs(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    truck_owner_required(current_user)

    jobs = db.query(Job).filter(Job.status == JobStatus.pending).all()

    output = []

    for job in jobs:
        applications = db.query(JobApplication).filter(JobApplication.job_id == job.id).all()

        apps_data = [
            {
                "application_id": app.id,
                "truck_pack_url": truck_pack_url(app.truck_pack) if app.truck_pack else None,
                "location": app.location,
                "order_number": app.order_number,
                "status": app.status.value if hasattr(app.status, "value") else str(app.status)
            }
            for app in applications
        ]

        job_app = applications[0] if applications else None

        output.append({
            "id": job.id,
            "title": job.title or "",
            "description": job.description or "",
            "contractor_id": job.contractor_id,
            "target_limit": job.target_limit or 0,
            "status": job.status.value if hasattr(job.status, "value") else str(job.status),
            "applicant_count": job.applicant_count or 0,
            "created_at": job.created_at.isoformat() if getattr(job, "created_at", None) else None,
            "order_number": getattr(job_app, "order_number", None),
            "location": getattr(job_app, "location", None) if job_app else getattr(job, "address", None),
            "applications": apps_data
        })

    return output

# ----------------- APPLY -----------------
@router.post("/apply-with-truck-pack")
def apply_with_truck_pack(
    job_id: int = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    truck_owner_required(current_user)

    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    if job.target_limit and (job.applicant_count or 0) >= job.target_limit:
        raise HTTPException(status_code=400, detail="This job's slots are full")

    filename = f"{int(time.time())}_{file.filename.replace(' ', '_')}"
    truck_pack_url_result = upload_file(file.file, f"truck_packs/{filename}", file.content_type)

    app_entry = JobApplication(
        job_id=job.id,
        truck_owner_id=current_user.id,
        status=ApplicationStatus.pending,
        truck_pack=truck_pack_url_result
    )
    db.add(app_entry)

    job.applicant_count = (job.applicant_count or 0) + 1

    db.commit()
    db.refresh(app_entry)

    return {
        "message": "Truck pack uploaded",
        "application_id": app_entry.id,
        "file_url": app_entry.truck_pack
    }


# ----------------- TRUCK PACKS BY TRUCK OWNER -----------------
@router.get("/truck-owners/{truck_owner_id}/truck-packs")
def get_truck_owner_truck_packs(
    truck_owner_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    contractor_required(current_user)

    owner = db.query(User).filter(User.id == truck_owner_id).first()
    if not owner:
        raise HTTPException(status_code=404, detail="Truck owner not found")

    applications = (
        db.query(JobApplication)
        .filter(JobApplication.truck_owner_id == truck_owner_id)
        .filter(JobApplication.truck_pack.isnot(None))
        .all()
    )

    return [
        {
            "application_id": app.id,
            "job_id": app.job_id,
            "job_title": app.job.title if app.job else None,
            "truck_pack_url": truck_pack_url(app.truck_pack),
            "status": app.status.value if hasattr(app.status, "value") else str(app.status),
        }
        for app in applications
    ]


# ----------------- ALL TRUCK PACKS FOR A JOB -----------------
@router.get("/{job_id}/truck-packs")
def get_job_truck_packs(
    job_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    contractor_required(current_user)

    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    if job.contractor_id != current_user.id:
        raise HTTPException(status_code=403, detail="You do not own this job")

    applications = (
        db.query(JobApplication)
        .filter(JobApplication.job_id == job_id)
        .filter(JobApplication.truck_pack.isnot(None))
        .all()
    )

    result = []
    for app in applications:
        owner = db.query(User).filter(User.id == app.truck_owner_id).first()
        result.append({
            "application_id": app.id,
            "truck_owner_id": app.truck_owner_id,
            "truck_owner_username": owner.username if owner else "Unknown",
            "truck_pack_url": truck_pack_url(app.truck_pack),
            "status": app.status.value if hasattr(app.status, "value") else str(app.status),
        })

    return result


# ----------------- MY APPLICATIONS -----------------
@router.get("/my-applications")
def my_applications(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    apps = db.query(JobApplication).filter(JobApplication.truck_owner_id == current_user.id).all()

    return [
        {
            "id": app.id,
            "job_id": app.job_id,
            "status": app.status.value if hasattr(app.status, "value") else str(app.status),
            "truck_pack_url": truck_pack_url(app.truck_pack) if app.truck_pack else None,
            "location": getattr(app, "location", None)
        }
        for app in apps
    ]


# ----------------- STATUS UPDATE -----------------
@router.patch("/{job_id}/status")
def update_job_status(job_id: int, payload: JobStatusUpdate,
                      db: Session = Depends(get_db),
                      current_user: User = Depends(get_current_user)):

    job = db.query(Job).filter(Job.id == job_id).first()

    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    job.status = JobStatus(payload.status)

    db.commit()
    db.refresh(job)

    return {"message": "Status updated", "job_id": job.id, "status": job.status.value}
# ----------------- UPLOAD SLIP -----------------
@router.post("/applications/{application_id}/upload-slip")
def upload_delivery_slip(
    application_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    truck_owner_required(current_user)

    app_entry = db.query(JobApplication).filter(JobApplication.id == application_id).first()
    if not app_entry:
        raise HTTPException(status_code=404, detail="Application not found")

    filename = f"{int(time.time())}_{file.filename.replace(' ', '_')}"
    slip_url_result = upload_file(file.file, f"delivery_slips/{filename}", file.content_type)

    new_slip = DeliverySlip(application_id=application_id, file_path=slip_url_result)

    db.add(new_slip)
    db.commit()
    db.refresh(new_slip)

    return {
        "message": "Slip uploaded successfully",
        "file_url": new_slip.file_path
    }

# ----------------- SLIPS -----------------
@router.get("/applications/{application_id}/slips")
def get_delivery_slips(
    application_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    try:
        print("👉 Fetching slips for:", application_id)

        app_entry = db.query(JobApplication).filter(
            JobApplication.id == application_id
        ).first()

        if not app_entry:
            raise HTTPException(status_code=404, detail="Application not found")

        slips = db.query(DeliverySlip).filter(
            DeliverySlip.application_id == application_id
        ).all()

        response = []
        for slip in slips:
            if not slip.file_path:
                print(f"⚠️ Slip {slip.id} has no file_path")
                continue

            try:
                created_at = (
                    slip.created_at.isoformat()
                    if slip.created_at else None
                )
            except Exception as e:
                print(f"⚠️ created_at error for slip {slip.id}:", e)
                created_at = None

            response.append({
                "id": slip.id,
                "file_url": slip.file_path,
                "created_at": created_at
            })

        print("✅ Returning slips:", response)
        return response

    except HTTPException:
        raise

    except Exception as e:
        print("🔥 SLIPS ENDPOINT CRASH:", repr(e))
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail="Internal server error")


# ----------------- JOB COMMENTS -----------------
@router.get("/{job_id}/comments")
def get_job_comments(
    job_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    comments = (
        db.query(JobComment)
        .filter(JobComment.job_id == job_id)
        .order_by(JobComment.created_at.asc())
        .all()
    )

    result = []
    for c in comments:
        author = db.query(User).filter(User.id == c.user_id).first()
        result.append({
            "id": c.id,
            "job_id": c.job_id,
            "user_id": c.user_id,
            "username": author.username if author else "Unknown",
            "role": getattr(author.role, "value", str(author.role)) if author else None,
            "content": c.content,
            "created_at": c.created_at.isoformat() if c.created_at else None,
        })

    return result


@router.post("/{job_id}/comments")
def add_job_comment(
    job_id: int,
    payload: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    content_text = (payload.get("content") or "").strip()
    if not content_text:
        raise HTTPException(status_code=400, detail="Comment content is required")

    comment = JobComment(
        job_id=job_id,
        user_id=current_user.id,
        content=content_text
    )
    db.add(comment)
    db.commit()
    db.refresh(comment)

    # ---- PUSH NOTIFICATIONS ----
    try:
        commenter_role = getattr(current_user.role, "value", str(current_user.role))
        if commenter_role == "main_contractor":
            applicants = db.query(JobApplication).filter(JobApplication.job_id == job_id).all()
            notified = set()
            for app_entry in applicants:
                if app_entry.truck_owner_id in notified:
                    continue
                notified.add(app_entry.truck_owner_id)
                owner = db.query(User).filter(User.id == app_entry.truck_owner_id).first()
                if owner and owner.fcm_token:
                    send_push_notification(
                        owner.fcm_token,
                        title=f"New comment on {job.title}",
                        body=f"{current_user.username}: {content_text[:80]}",
                        data={"job_id": str(job_id), "type": "comment"}
                    )
        else:
            contractor = db.query(User).filter(User.id == job.contractor_id).first()
            if contractor and contractor.fcm_token:
                send_push_notification(
                    contractor.fcm_token,
                    title=f"New comment on {job.title}",
                    body=f"{current_user.username}: {content_text[:80]}",
                    data={"job_id": str(job_id), "type": "comment"}
                )
    except Exception as e:
        print("PUSH NOTIFICATION ERROR (comment):", e)

    return {
        "id": comment.id,
        "job_id": comment.job_id,
        "user_id": comment.user_id,
        "username": current_user.username,
        "role": getattr(current_user.role, "value", str(current_user.role)),
        "content": comment.content,
        "created_at": comment.created_at.isoformat() if comment.created_at else None,
    }


# ----------------- JOB LIKES -----------------
@router.get("/{job_id}/likes")
def get_job_likes(
    job_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    count = db.query(JobLike).filter(JobLike.job_id == job_id).count()
    liked_by_me = db.query(JobLike).filter(
        JobLike.job_id == job_id,
        JobLike.user_id == current_user.id
    ).first() is not None

    return {"job_id": job_id, "like_count": count, "liked_by_me": liked_by_me}


@router.post("/{job_id}/likes/toggle")
def toggle_job_like(
    job_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    existing = db.query(JobLike).filter(
        JobLike.job_id == job_id,
        JobLike.user_id == current_user.id
    ).first()

    if existing:
        db.delete(existing)
        db.commit()
        liked = False
    else:
        db.add(JobLike(job_id=job_id, user_id=current_user.id))
        db.commit()
        liked = True

    count = db.query(JobLike).filter(JobLike.job_id == job_id).count()

    return {"job_id": job_id, "like_count": count, "liked_by_me": liked}


# ----------------- MONITORING -----------------
@router.get("/monitoring")
def monitoring_jobs(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    contractor_required(current_user)

    applications = (
        db.query(JobApplication)
        .join(Job)
        .filter(Job.contractor_id == current_user.id)
        .all()
    )

    return [
        {
            "application_id": app.id,
            "job_title": app.job.title if app.job else "Unknown",
            "truck_owner": app.truck_owner.email if app.truck_owner else "Unknown",
            "status": app.status.value if hasattr(app.status, "value") else str(app.status),
        }
        for app in applications
    ]

# ----------------- ASSIGN ORDER -----------------


@router.patch("/applications/{application_id}/assign-order")
def assign_order(
    application_id: int,
    payload: AssignOrderPayload,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    contractor_required(current_user)

    app_entry = db.query(JobApplication).filter(JobApplication.id == application_id).first()

    if not app_entry:
        raise HTTPException(status_code=404, detail="Application not found")

    app_entry.order_number = payload.order_number
    app_entry.location = payload.location

    db.commit()
    db.refresh(app_entry)

    # ---- PUSH NOTIFICATION ----
    try:
        owner = db.query(User).filter(User.id == app_entry.truck_owner_id).first()
        if owner and owner.fcm_token:
            send_push_notification(
                owner.fcm_token,
                title="Order assigned",
                body=f"Order #{app_entry.order_number} assigned - location: {app_entry.location}",
                data={"application_id": str(app_entry.id), "type": "order_assigned"}
            )
    except Exception as e:
        print("PUSH NOTIFICATION ERROR (assign order):", e)

    return {
        "message": "Order assigned successfully",
        "application_id": app_entry.id,
        "order_number": app_entry.order_number,
        "location": app_entry.location
    }


# ----------------- APPROVE / REJECT APPLICATION -----------------
@router.patch("/applications/{application_id}/approve")
def approve_application(
    application_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    contractor_required(current_user)

    app_entry = db.query(JobApplication).filter(JobApplication.id == application_id).first()
    if not app_entry:
        raise HTTPException(status_code=404, detail="Application not found")

    job = db.query(Job).filter(Job.id == app_entry.job_id).first()
    if not job or job.contractor_id != current_user.id:
        raise HTTPException(status_code=403, detail="You do not own this job")

    app_entry.status = ApplicationStatus.approved
    db.commit()
    db.refresh(app_entry)

    return {
        "message": "Application approved",
        "application_id": app_entry.id,
        "status": app_entry.status.value
    }


@router.patch("/applications/{application_id}/reject")
def reject_application(
    application_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    contractor_required(current_user)

    app_entry = db.query(JobApplication).filter(JobApplication.id == application_id).first()
    if not app_entry:
        raise HTTPException(status_code=404, detail="Application not found")

    job = db.query(Job).filter(Job.id == app_entry.job_id).first()
    if not job or job.contractor_id != current_user.id:
        raise HTTPException(status_code=403, detail="You do not own this job")

    app_entry.status = ApplicationStatus.rejected
    db.commit()
    db.refresh(app_entry)

    return {
        "message": "Application rejected",
        "application_id": app_entry.id,
        "status": app_entry.status.value
    }


# ----------------- LIST APPLICATIONS FOR A JOB -----------------
@router.get("/{job_id}/applications")
def get_job_applications(
    job_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    contractor_required(current_user)

    job = db.query(Job).filter(Job.id == job_id).first()
    if not job or job.contractor_id != current_user.id:
        raise HTTPException(status_code=403, detail="You do not own this job")

    applications = db.query(JobApplication).filter(JobApplication.job_id == job_id).all()

    result = []
    for a in applications:
        truck_owner = db.query(User).filter(User.id == a.truck_owner_id).first()
        result.append({
            "application_id": a.id,
            "truck_owner_id": a.truck_owner_id,
            "truck_owner_username": truck_owner.username if truck_owner else "Unknown",
            "status": a.status.value if hasattr(a.status, "value") else str(a.status),
            "truck_pack_url": a.truck_pack,
            "order_number": a.order_number,
            "location": a.location
        })

    return result