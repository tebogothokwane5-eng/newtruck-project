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

@app.get("/")
def root():
    return {"status": "running"}