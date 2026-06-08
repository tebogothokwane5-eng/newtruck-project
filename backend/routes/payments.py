# ---------------- IMPORTS ----------------
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from datetime import datetime
import os
import requests

from backend.database import get_db
from backend.auth_utils import get_current_user
from backend.payments_service import initiate_paystack, initiate_paypal, get_paypal_token
from backend.models import Job, Payment


# ---------------- ROUTER ----------------
router = APIRouter(prefix="/payments", tags=["Payments"])


# ============================
# ✅ PUT YOUR FUNCTION HERE
# ============================
@router.post("/initiate/{job_id}")
def initiate_payment(
    job_id: int,
    method: str,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    job = db.query(Job).filter(Job.id == job_id).first()

    if not job:
        raise HTTPException(404, "Job not found")

    if job.status != "completed":
        raise HTTPException(400, "Job not completed")

    payment = Payment(
        job_id=job.id,
        contractor_id=current_user.id,
        truck_owner_id=job.truck_owner_id,
        amount=job.price,
        status="pending"
    )

    db.add(payment)
    db.commit()
    db.refresh(payment)

    if method == "paystack":
        res = initiate_paystack(current_user.email, job.price)
        payment.reference = res["data"]["reference"]
        db.commit()
        return {"payment_url": res["data"]["authorization_url"]}

    elif method == "paypal":
        res = initiate_paypal(job.price)

        approval_url = None
        for link in res["links"]:
            if link["rel"] == "approve":
                approval_url = link["href"]

        payment.reference = res["id"]
        db.commit()

        return {"payment_url": approval_url}

    else:
        raise HTTPException(400, "Invalid payment method")
