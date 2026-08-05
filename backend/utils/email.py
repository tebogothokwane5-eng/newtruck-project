import os
import requests
from typing import Optional

RESEND_API_KEY = os.getenv("RESEND_API_KEY")
RESEND_FROM_EMAIL = os.getenv("RESEND_FROM_EMAIL", "onboarding@resend.dev")
RESEND_API_URL = "https://api.resend.com/emails"


# -----------------------------
# VALIDATION (CRITICAL FOR PROD)
# -----------------------------
if not RESEND_API_KEY:
    print("WARNING: RESEND_API_KEY not set in environment variables")


# -----------------------------
# CORE EMAIL SENDER
# -----------------------------
def send_email(to_email: str, subject: str, body: str) -> bool:
    """
    Sends email via the Resend HTTP API (not raw SMTP - Render blocks
    outbound SMTP ports on free-tier instances, so SMTP silently times out).
    Returns True if successful, False otherwise.
    """

    if not RESEND_API_KEY:
        print("Resend not configured")
        return False

    try:
        response = requests.post(
            RESEND_API_URL,
            headers={
                "Authorization": f"Bearer {RESEND_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "from": RESEND_FROM_EMAIL,
                "to": to_email,
                "subject": subject,
                "text": body,
            },
            timeout=10,
        )

        if response.status_code in (200, 201):
            print(f"[EMAIL SENT] → {to_email}")
            return True

        print(f"[EMAIL ERROR] {response.status_code}: {response.text}")
        return False

    except Exception as e:
        print(f"[EMAIL ERROR] {e}")
        return False


# -----------------------------
# NOTIFICATIONS
# -----------------------------
def notify_contractor_on_application(truck_owner, job, db) -> None:
    """
    Notify contractor when a truck owner applies.
    """

    from backend.models.user import User

    contractor = db.query(User).filter(User.id == job.contractor_id).first()

    if not contractor or not contractor.email:
        return

    subject = "New Truck Application"
    body = (
        f"Hello,\n\n"
        f"{truck_owner.username} applied for your job:\n"
        f"Title: {job.title}\n\n"
        f"Regards,\nTrucking System"
    )

    send_email(contractor.email, subject, body)


def notify_truck_owner_on_accept(truck_owner, job) -> None:
    """
    Notify truck owner when job is accepted.
    """

    if not truck_owner or not truck_owner.email:
        return

    subject = "Job Accepted"
    body = (
        f"Hello {truck_owner.username},\n\n"
        f"Your application for:\n"
        f"'{job.title}' has been accepted.\n\n"
        f"Regards,\nTrucking System"
    )

    send_email(truck_owner.email, subject, body)