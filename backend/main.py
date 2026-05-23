import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from backend.database import engine, Base
from backend.routes import auth, feedback, jobs
from backend import admin

# ---------------- APP INSTANCE ----------------
app = FastAPI(title="Trucking Trust Backend")

# ---------------- DATABASE ----------------
# ⚠️ OK for now, later switch to Alembic migrations
Base.metadata.create_all(bind=engine)

# ---------------- UPLOADS (TEMP FIX) ----------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

#UPLOAD_DIR = os.path.join(BASE_DIR, "uploads")

import os

UPLOAD_DIR = os.environ.get("UPLOAD_DIR", "/tmp/uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)



TRUCK_PACKS_DIR = os.path.join(UPLOAD_DIR, "truck_packs")
SLIPS_DIR = os.path.join(UPLOAD_DIR, "slips")

os.makedirs(TRUCK_PACKS_DIR, exist_ok=True)
os.makedirs(SLIPS_DIR, exist_ok=True)

# Mount static files
app.mount("/uploads", StaticFiles(directory=UPLOAD_DIR), name="uploads")

# ---------------- CORS ----------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # ⚠️ tighten later
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------- ROUTERS ----------------
app.include_router(auth.router)
app.include_router(feedback.router)
app.include_router(jobs.router)
app.include_router(admin.router)

# ---------------- STARTUP ----------------
@app.on_event("startup")
async def startup_event():
    print("Backend started")
    print(f"Uploads: {UPLOAD_DIR}")

# ---------------- ROOT ----------------
@app.get("/")
def root():
    return {"message": "Trucking Trust Backend is running"}