# ---------------- IMPORTS ----------------
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel

from backend.database import get_db
from backend.models.user import Job
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