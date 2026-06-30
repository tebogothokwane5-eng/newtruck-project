import os
import requests
from fastapi import APIRouter, HTTPException

router = APIRouter(prefix="/payments", tags=["payments"])

# ==============================
# PAYSTACK CONFIG
# ==============================
PAYSTACK_SECRET_KEY = os.getenv("PAYSTACK_SECRET_KEY")


def initiate_paystack(email: str, amount: float):
    url = "https://api.paystack.co/transaction/initialize"

    headers = {
        "Authorization": f"Bearer {PAYSTACK_SECRET_KEY}",
        "Content-Type": "application/json"
    }

    data = {
        "email": email,
        "amount": int(amount * 100),
        "currency": "ZAR"
    }

    response = requests.post(url, json=data, headers=headers)

    if response.status_code != 200:
        raise Exception("Paystack initialization failed")

    return response.json()


# ==============================
# PAYPAL CONFIG
# ==============================
PAYPAL_CLIENT_ID = os.getenv("PAYPAL_CLIENT_ID")
PAYPAL_SECRET = os.getenv("PAYPAL_SECRET")
PAYPAL_BASE = "https://api-m.sandbox.paypal.com"


def get_paypal_token():
    url = f"{PAYPAL_BASE}/v1/oauth2/token"

    response = requests.post(
        url,
        auth=(PAYPAL_CLIENT_ID, PAYPAL_SECRET),
        data={"grant_type": "client_credentials"}
    )

    if response.status_code != 200:
        raise Exception("PayPal auth failed")

    return response.json()["access_token"]


def initiate_paypal(amount: float):
    access_token = get_paypal_token()

    url = f"{PAYPAL_BASE}/v2/checkout/orders"

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {access_token}"
    }

    data = {
        "intent": "CAPTURE",
        "purchase_units": [
            {
                "amount": {
                    "currency_code": "USD",
                    "value": str(amount)
                }
            }
        ],
        "application_context": {
            "return_url": "https://newtruck-project.onrender.com/payments/paypal/success",
            "cancel_url": "https://newtruck-project.onrender.com/payments/paypal/cancel"
        }
    }

    response = requests.post(url, json=data, headers=headers)

    if response.status_code not in [200, 201]:
        raise HTTPException(status_code=400, detail="PayPal order creation failed")

    return response.json()


# ==============================
# API ENDPOINTS (THIS WAS MISSING)
# ==============================

@router.post("/paystack/initiate")
def paystack_route(email: str, amount: float):
    return initiate_paystack(email, amount)


@router.post("/paypal/initiate")
def paypal_route(amount: float):
    return initiate_paypal(amount)