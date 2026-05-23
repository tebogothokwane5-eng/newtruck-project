import os
import time
import shutil
from sqlalchemy.orm import Session
from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, Form
from fastapi.responses import FileResponse

from backend.schemas import JobCreate, JobStatusUpdate, AssignOrderPayload
from backend.database import get_db
from backend.routes.auth import get_current_user
from backend.models.user import Job, JobStatus, JobApplication, User, DeliverySlip

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
    return f"{BASE_URL}/jobs/uploads/truck_packs/{filename}"


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

    app_entry = db.query(JobApplication).filter(
        JobApplication.job_id == job_id,
        JobApplication.truck_owner_id == current_user.id
    ).first()

    if not app_entry:
        app_entry = JobApplication(
            job_id=job.id,
            truck_owner_id=current_user.id,
            status=JobStatus.pending
        )
        db.add(app_entry)
        job.applicant_count = (job.applicant_count or 0) + 1

    filename = f"{int(time.time())}_{file.filename.replace(' ', '_')}"
    file_path = os.path.join(UPLOAD_DIR, filename)

    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    app_entry.truck_pack = filename

    db.commit()
    db.refresh(app_entry)

    return {
        "message": "Truck pack uploaded",
        "application_id": app_entry.id,
        "file_url": truck_pack_url(filename)
    }


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
    file_path = os.path.join(UPLOAD_SLIP_DIR, filename)

    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    new_slip = DeliverySlip(application_id=application_id, file_path=filename)

    db.add(new_slip)
    db.commit()
    db.refresh(new_slip)

    return {
        "message": "Slip uploaded successfully",
        "file_url": slip_url(filename)
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

            file_path = os.path.join(UPLOAD_SLIP_DIR, slip.file_path)

            if not os.path.exists(file_path):
                print(f"⚠️ File missing on disk: {file_path}")
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
                "file_url": slip_url(slip.file_path),
                "created_at": created_at
            })

        print("✅ Returning slips:", response)
        return response

    except Exception as e:
        print("🔥 SLIPS ENDPOINT CRASH:", str(e))
        raise HTTPException(status_code=500, detail="Internal server error")


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

    return {
        "message": "Order assigned successfully",
        "application_id": app_entry.id,
        "order_number": app_entry.order_number,
        "location": app_entry.location
    }