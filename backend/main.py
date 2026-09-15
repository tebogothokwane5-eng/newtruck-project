import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from backend.routes import auth, feedback, jobs, payments
from backend import admin
from backend.database import engine, Base

app = FastAPI(title="Trucking Trust Backend")

# ---------------- SAFE STARTUP ----------------
@app.on_event("startup")
def startup():
    print("Backend started successfully")

    try:
        Base.metadata.create_all(bind=engine)
    except Exception as e:
        print("DB init error:", e)

# ---------------- UPLOADS ----------------
UPLOAD_DIR = os.environ.get("UPLOAD_DIR", "/tmp/uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)

app.mount("/uploads", StaticFiles(directory=UPLOAD_DIR), name="uploads")

# ---------------- CORS ----------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------- ROUTES ----------------
app.include_router(auth.router)
app.include_router(feedback.router)
app.include_router(jobs.router)
app.include_router(admin.router)
app.include_router(payments.router)

from fastapi.responses import HTMLResponse

PRIVACY_POLICY_HTML = """
<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<title>Truckify - Privacy Policy</title>
<style>
body { font-family: Arial, sans-serif; max-width: 800px; margin: 40px auto; padding: 0 20px; line-height: 1.6; color: #222; }
h1, h2 { color: #0d47a1; }
</style>
</head>
<body>
<h1>Truckify Privacy Policy</h1>
<p><strong>Last updated:</strong> September 2026</p>

<p>Truckify ("we", "our", "the app") connects truck owners with contractors for job/load matching. This policy explains what personal data we collect, why, and how we protect it.</p>

<h2>Information We Collect</h2>
<ul>
<li>Account information: username, email address, phone number</li>
<li>Identity verification: ID number and uploaded identification documents</li>
<li>Banking information: bank account details, PayPal email, Paystack subaccount information (for processing payments)</li>
<li>Job-related data: job postings, applications, delivery slips, truck pack details, order numbers</li>
<li>Location data: job/delivery addresses and coordinates</li>
<li>Device information: push notification tokens (FCM) for delivering job and application updates</li>
<li>User-generated content: comments, likes, and feedback on jobs</li>
</ul>

<h2>How We Use Your Information</h2>
<ul>
<li>To create and verify your account</li>
<li>To connect truck owners with contractors and facilitate job matching</li>
<li>To process payments securely via Paystack or PayPal</li>
<li>To send you push notifications about job updates and application status</li>
<li>To verify identity and prevent fraud</li>
</ul>

<h2>Data Sharing</h2>
<p>We share necessary information with:</p>
<ul>
<li>Paystack and PayPal, to process payments</li>
<li>Other users, limited to what is needed to complete a job (e.g. a contractor sees a truck owner's username and application details)</li>
</ul>
<p>We do not sell your personal data to third parties.</p>

<h2>Data Retention</h2>
<p>We retain your data for as long as your account is active, or as needed to comply with legal obligations.</p>

<h2>Your Rights</h2>
<p>You have the right to access, correct, or request deletion of your personal data. See our <a href="/data-rights">Data Subject Rights</a> page for details on how to exercise these rights.</p>

<h2>Security</h2>
<p>We use industry-standard measures, including encrypted password storage and secure payment processing, to protect your information.</p>

<h2>Contact Us</h2>
<p>For any privacy-related questions or requests, contact us at tebogothokwane5@gmail.com.</p>

</body>
</html>
"""

DATA_RIGHTS_HTML = """
<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<title>Truckify - Data Subject Rights</title>
<style>
body { font-family: Arial, sans-serif; max-width: 800px; margin: 40px auto; padding: 0 20px; line-height: 1.6; color: #222; }
h1, h2 { color: #0d47a1; }
</style>
</head>
<body>
<h1>Truckify - Your Data Rights</h1>
<p><strong>Last updated:</strong> September 2026</p>

<p>As a Truckify user, you have the following rights regarding your personal data:</p>

<h2>Right to Access</h2>
<p>You can request a copy of the personal data we hold about you by contacting us through the app.</p>

<h2>Right to Correction</h2>
<p>You can update your account information (username, email, phone number, bank details) directly within the app at any time.</p>

<h2>Right to Deletion</h2>
<p>You can request that we delete your account and associated personal data. Contact us through the app's support channel to submit a deletion request. We will process valid requests within a reasonable timeframe, subject to any legal retention requirements (e.g. financial records related to completed payments).</p>

<h2>Right to Withdraw Consent</h2>
<p>Where we rely on your consent to process data (such as push notifications), you may withdraw this consent at any time through your device or app settings.</p>

<h2>How to Exercise Your Rights</h2>
<p>To exercise any of these rights, please email us at tebogothokwane5@gmail.com with your username and a description of your request.</p>

</body>
</html>
"""


@app.get("/privacy-policy", response_class=HTMLResponse)
def privacy_policy():
    return PRIVACY_POLICY_HTML


@app.get("/data-rights", response_class=HTMLResponse)
def data_rights():
    return DATA_RIGHTS_HTML


@app.get("/")
def root():
    return {"status": "running"}