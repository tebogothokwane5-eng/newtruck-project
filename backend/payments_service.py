import os
import requests
from fastapi import HTTPException

# ==============================
# ENV SAFETY CHECKS
# ==============================
PAYSTACK_SECRET_KEY = os.getenv("PAYSTACK_SECRET_KEY")
PAYPAL_CLIENT_ID = os.getenv("PAYPAL_CLIENT_ID")
PAYPAL_SECRET = os.getenv("PAYPAL_SECRET")
PAYPAL_BASE = "https://api-m.sandbox.paypal.com"


# ==============================
# PAYSTACK
# ==============================
def initiate_paystack(email: str, amount: float, subaccount_code: str = None):
    if not PAYSTACK_SECRET_KEY:
        raise HTTPException(status_code=500, detail="Missing PAYSTACK_SECRET_KEY")

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

    if subaccount_code:
        data["subaccount"] = subaccount_code

    response = requests.post(url, json=data, headers=headers)

    # 🔥 show real error from Paystack
    if response.status_code not in [200, 201]:
        return {
            "error": True,
            "status": response.status_code,
            "message": response.text
        }

    return response.json()


# ==============================
# PAYPAL TOKEN
# ==============================
def get_paypal_token():
    if not PAYPAL_CLIENT_ID or not PAYPAL_SECRET:
        raise HTTPException(status_code=500, detail="Missing PayPal credentials")

    url = f"{PAYPAL_BASE}/v1/oauth2/token"

    response = requests.post(
        url,
        auth=(PAYPAL_CLIENT_ID, PAYPAL_SECRET),
        data={"grant_type": "client_credentials"}
    )

    if response.status_code != 200:
        raise HTTPException(
            status_code=400,
            detail=response.text
        )

    return response.json()["access_token"]


# ==============================
# PAYPAL INIT
# ==============================
def initiate_paypal(amount: float, payee_email: str = None):
    access_token = get_paypal_token()

    url = f"{PAYPAL_BASE}/v2/checkout/orders"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {access_token}"
    }

    purchase_unit = {
        "amount": {
            "currency_code": "USD",
            "value": str(amount)
        }
    }

    if payee_email:
        purchase_unit["payee"] = {"email_address": payee_email}

    data = {
        "intent": "CAPTURE",
        "purchase_units": [purchase_unit],
        "application_context": {
            "return_url": "https://newtruck-project.onrender.com/payments/paypal/success",
            "cancel_url": "https://newtruck-project.onrender.com/payments/paypal/cancel"
        }
    }

    response = requests.post(url, json=data, headers=headers)

    if response.status_code not in [200, 201]:
        raise HTTPException(status_code=400, detail=response.text)

    return response.json()

# ==============================
# PAYSTACK PAYOUTS (TRANSFERS)
# ==============================
def create_transfer_recipient(account_number: str, bank_code: str, account_name: str):
    """
    Register a truck owner's bank account with Paystack as a transfer recipient.
    Returns the recipient_code needed to send them money.
    """
    if not PAYSTACK_SECRET_KEY:
        raise HTTPException(status_code=500, detail="Missing PAYSTACK_SECRET_KEY")

    url = "https://api.paystack.co/transferrecipient"
    headers = {
        "Authorization": f"Bearer {PAYSTACK_SECRET_KEY}",
        "Content-Type": "application/json"
    }
    data = {
        "type": "nuban",
        "name": account_name,
        "account_number": account_number,
        "bank_code": bank_code,
        "currency": "ZAR"
    }

    response = requests.post(url, json=data, headers=headers)

    if response.status_code not in [200, 201]:
        return {
            "error": True,
            "status": response.status_code,
            "message": response.text
        }

    return response.json()


def initiate_payout(recipient_code: str, amount: float, reason: str = "Job payout"):
    """
    Send money to a previously registered transfer recipient.
    """
    if not PAYSTACK_SECRET_KEY:
        raise HTTPException(status_code=500, detail="Missing PAYSTACK_SECRET_KEY")

    url = "https://api.paystack.co/transfer"
    headers = {
        "Authorization": f"Bearer {PAYSTACK_SECRET_KEY}",
        "Content-Type": "application/json"
    }
    data = {
        "source": "balance",
        "amount": int(amount * 100),
        "recipient": recipient_code,
        "reason": reason
    }

    response = requests.post(url, json=data, headers=headers)

    if response.status_code not in [200, 201]:
        return {
            "error": True,
            "status": response.status_code,
            "message": response.text
        }

    return response.json()


# ==============================
# PAYSTACK SUBACCOUNTS (CONTRACTOR PAYOUT ROUTING)
# ==============================
def create_paystack_subaccount(business_name: str, bank_code: str, account_number: str, percentage_charge: float = 0):
    """
    Create a Paystack subaccount for a contractor.
    percentage_charge = platform's cut (0 means contractor receives 100% of the payment, minus Paystack's own transaction fee).
    Returns the subaccount_code needed to route payments to this contractor.
    """
    if not PAYSTACK_SECRET_KEY:
        raise HTTPException(status_code=500, detail="Missing PAYSTACK_SECRET_KEY")

    url = "https://api.paystack.co/subaccount"
    headers = {
        "Authorization": f"Bearer {PAYSTACK_SECRET_KEY}",
        "Content-Type": "application/json"
    }
    data = {
        "business_name": business_name,
        "bank_code": bank_code,
        "account_number": account_number,
        "percentage_charge": percentage_charge
    }

    response = requests.post(url, json=data, headers=headers)

    if response.status_code not in [200, 201]:
        return {
            "error": True,
            "status": response.status_code,
            "message": response.text
        }

    return response.json()
