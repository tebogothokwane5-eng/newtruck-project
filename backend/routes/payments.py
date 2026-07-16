# ---------------- IMPORTS ----------------
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel

from backend.database import get_db
from backend.models.user import Job, JobApplication, ApplicationStatus, User
from backend.models.payment import Payment

# ---------------- ROUTER ----------------
router = APIRouter(prefix="/payments", tags=["Payments"])


# ---------------- REQUEST MODELS ----------------
class PaymentRequest(BaseModel):
    method: str  # "paystack" or "paypal"


class PaystackRequest(BaseModel):
    email: str
    amount: float


class PaypalRequest(BaseModel):
    amount: float


# ============================
# DEPENDENCIES (LAZY IMPORTS)
# ============================

def get_current_user_dep():
    from backend.routes.auth import get_current_user
    return get_current_user


def get_payment_services():
    from backend.payments_service import initiate_paystack, initiate_paypal
    return initiate_paystack, initiate_paypal


# ============================
# MAIN PAYMENT ENDPOINT
# ============================
@router.post("/initiate/{job_id}")
def initiate_payment(
    job_id: int,
    data: PaymentRequest,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user_dep())
):
    method = data.method.lower()

    initiate_paystack, initiate_paypal = get_payment_services()

    # ---------------- GET JOB ----------------
    job = db.query(Job).filter(Job.id == job_id).first()

    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    if job.status.value.lower() != "completed":
        raise HTTPException(status_code=400, detail="Job not completed")

    # ---------------- CREATE PAYMENT RECORD ----------------
    approved_app = db.query(JobApplication).filter(
        JobApplication.job_id == job.id,
        JobApplication.status == ApplicationStatus.approved
    ).first()

    if not approved_app:
        raise HTTPException(status_code=400, detail="No approved truck owner for this job")

    payment = Payment(
        truck_owner_id=approved_app.truck_owner_id,
        job_id=job.id,
        contractor_id=current_user.id,
        amount=job.price,
        status="pending"
    )

    db.add(payment)
    db.commit()
    db.refresh(payment)

    # ================= PAYSTACK =================
    if method == "paystack":
        res = initiate_paystack(current_user.email, job.price)

        print("🔵 PAYSTACK RAW RESPONSE:", res)

        # 🔴 FIX: expose real error
        if not res:
            raise HTTPException(status_code=500, detail="Empty response from Paystack")

        if res.get("error"):
            raise HTTPException(
                status_code=res.get("status", 500),
                detail=res.get("message")
            )

        if "data" not in res:
            raise HTTPException(status_code=500, detail=f"Invalid Paystack response: {res}")

        payment.reference = res["data"]["reference"]
        db.commit()

        return {
            "payment_url": res["data"]["authorization_url"],
            "reference": payment.reference
        }

    # ================= PAYPAL =================
    elif method == "paypal":
        res = initiate_paypal(job.price)

        print("🟡 PAYPAL RAW RESPONSE:", res)

        if not res:
            raise HTTPException(status_code=500, detail="Empty response from PayPal")

        if "links" not in res:
            raise HTTPException(status_code=500, detail=f"Invalid PayPal response: {res}")

        approval_url = next(
            (link["href"] for link in res["links"] if link["rel"] == "approve"),
            None
        )

        if not approval_url:
            raise HTTPException(status_code=500, detail="No approval URL from PayPal")

        payment.reference = res["id"]
        db.commit()

        return {
            "payment_url": approval_url,
            "reference": payment.reference
        }

    # ================= INVALID METHOD =================
    else:
        raise HTTPException(status_code=400, detail="Invalid payment method")


# ============================
# PAYSTACK TEST ROUTE (FIXED)
# ============================
@router.post("/paystack/initiate")
def paystack_route(data: PaystackRequest):
    initiate_paystack, _ = get_payment_services()

    res = initiate_paystack(data.email, data.amount)

    print("🔵 TEST PAYSTACK RESPONSE:", res)

    # 🔴 FIX: expose real Paystack error
    if not res:
        raise HTTPException(status_code=500, detail="Empty response from Paystack")

    if res.get("error"):
        raise HTTPException(
            status_code=res.get("status", 500),
            detail=res.get("message")
        )

    if "data" not in res:
        raise HTTPException(status_code=500, detail=f"Invalid response: {res}")

    return res


# ============================
# PAYPAL TEST ROUTE
# ============================
@router.post("/paypal/initiate")
def paypal_route(data: PaypalRequest):
    _, initiate_paypal = get_payment_services()

    res = initiate_paypal(data.amount)

    print("🟡 TEST PAYPAL RESPONSE:", res)

    if not res:
        raise HTTPException(status_code=500, detail="Empty response from PayPal")

    return res

# ============================
# MY PAYMENTS (TRUCK OWNER)
# ============================
@router.get("/my-payments")
def my_payments(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user_dep())
):
    payments = db.query(Payment).filter(
        Payment.truck_owner_id == current_user.id
    ).all()

    return [
        {
            "job_id": p.job_id,
            "status": p.status,
            "amount": p.amount,
            "reference": p.reference,
            "created_at": p.created_at.isoformat() if p.created_at else None
        }
        for p in payments
    ]


# ============================
# PAYOUT TO TRUCK OWNER (ADMIN ONLY)
# ============================
@router.post("/payout/{payment_id}")
def payout_truck_owner(
    payment_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user_dep())
):
    from backend.payments_service import create_transfer_recipient, initiate_payout

    role = getattr(current_user.role, "value", str(current_user.role))
    if role != "admin":
        raise HTTPException(status_code=403, detail="Admin access only")

    payment = db.query(Payment).filter(Payment.id == payment_id).first()
    if not payment:
        raise HTTPException(status_code=404, detail="Payment not found")

    if payment.status != "pending":
        raise HTTPException(status_code=400, detail=f"Payment already {payment.status}")

    truck_owner = db.query(User).filter(User.id == payment.truck_owner_id).first()
    if not truck_owner:
        raise HTTPException(status_code=404, detail="Truck owner not found")

    if not all([truck_owner.bank_code, truck_owner.bank_account_number, truck_owner.bank_account_name]):
        raise HTTPException(status_code=400, detail="Truck owner has not set up bank details")

    # Step 1: Create transfer recipient
    recipient_res = create_transfer_recipient(
        account_number=truck_owner.bank_account_number,
        bank_code=truck_owner.bank_code,
        account_name=truck_owner.bank_account_name
    )

    if recipient_res.get("error"):
        raise HTTPException(status_code=400, detail=recipient_res.get("message"))

    recipient_code = recipient_res["data"]["recipient_code"]

    # Step 2: Initiate payout
    payout_res = initiate_payout(
        recipient_code=recipient_code,
        amount=payment.amount,
        reason=f"Payout for job {payment.job_id}"
    )

    if payout_res.get("error"):
        raise HTTPException(status_code=400, detail=payout_res.get("message"))

    payment.status = "completed"
    db.commit()
    db.refresh(payment)

    return {
        "message": "Payout initiated successfully",
        "payment_id": payment.id,
        "status": payment.status,
        "transfer_details": payout_res
    }


# ============================
# PAYSTACK WEBHOOK
# ============================
import hmac
import hashlib
import os
from fastapi import Request

@router.post("/webhook/paystack")
async def paystack_webhook(request: Request, db: Session = Depends(get_db)):
    PAYSTACK_SECRET_KEY = os.getenv("PAYSTACK_SECRET_KEY")

    if not PAYSTACK_SECRET_KEY:
        raise HTTPException(status_code=500, detail="Missing PAYSTACK_SECRET_KEY")

    body = await request.body()
    signature = request.headers.get("x-paystack-signature")

    expected_signature = hmac.new(
        PAYSTACK_SECRET_KEY.encode("utf-8"),
        body,
        hashlib.sha512
    ).hexdigest()

    if not signature or not hmac.compare_digest(expected_signature, signature):
        raise HTTPException(status_code=401, detail="Invalid signature")

    payload = await request.json()
    event = payload.get("event")
    data = payload.get("data", {})

    print("🔔 PAYSTACK WEBHOOK EVENT:", event)

    if event == "charge.success":
        reference = data.get("reference")

        payment = db.query(Payment).filter(Payment.reference == reference).first()

        if payment and payment.status != "completed":
            payment.status = "completed"
            db.commit()
            print(f"✅ Payment {payment.id} marked completed via webhook")

    return {"status": "received"}
