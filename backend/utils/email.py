import os
import socket
import smtplib
from email.mime.text import MIMEText
from typing import Optional


class IPv4SMTP(smtplib.SMTP):
    """
    Render (and some other cloud hosts) fail to route outbound IPv6
    connections, causing 'Network is unreachable' errors when smtplib
    picks an IPv6 address for the SMTP server. This subclass forces the
    underlying socket to use IPv4 only, while leaving hostname-based TLS
    verification (starttls) untouched since self._host stays as the
    original hostname.
    """
    def _get_socket(self, host, port, timeout):
        addr_info = socket.getaddrinfo(host, port, socket.AF_INET, socket.SOCK_STREAM)
        family, socktype, proto, canonname, sockaddr = addr_info[0]
        sock = socket.socket(family, socktype, proto)
        if timeout is not None:
            sock.settimeout(timeout)
        sock.connect(sockaddr)
        return sock

SMTP_SERVER = os.getenv("SMTP_SERVER", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))

SMTP_USER = os.getenv("SMTP_USER")
SMTP_PASS = os.getenv("SMTP_PASS")


# -----------------------------
# VALIDATION (CRITICAL FOR PROD)
# -----------------------------
if not SMTP_USER or not SMTP_PASS:
    print("WARNING: SMTP credentials not set in environment variables")


# -----------------------------
# CORE EMAIL SENDER
# -----------------------------
def send_email(to_email: str, subject: str, body: str) -> bool:
    """
    Sends email via SMTP.
    Returns True if successful, False otherwise.
    """

    if not SMTP_USER or not SMTP_PASS:
        print("SMTP not configured")
        return False

    msg = MIMEText(body, "plain", "utf-8")
    msg["Subject"] = subject
    msg["From"] = SMTP_USER
    msg["To"] = to_email

    try:
        with IPv4SMTP(SMTP_SERVER, SMTP_PORT, timeout=10) as server:
            server.ehlo()
            server.starttls()
            server.ehlo()

            server.login(SMTP_USER, SMTP_PASS)
            server.sendmail(SMTP_USER, [to_email], msg.as_string())

        print(f"[EMAIL SENT] → {to_email}")
        return True

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