from pydantic import BaseModel, Field, ConfigDict
from typing import Optional
from datetime import datetime

from backend.models.user import RoleEnum, JobStatus, ApplicationStatus


# ---------------- USERS ----------------

class UserCreate(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    password: str = Field(..., min_length=6)
    phone_no: str
    id_no: str
    email: str
    role: RoleEnum
    document: Optional[str] = None


class UserLogin(BaseModel):
    username: str
    password: str


class BankDetailsUpdate(BaseModel):
    bank_code: str
    bank_account_number: str
    bank_account_name: str


class PaypalEmailUpdate(BaseModel):
    paypal_email: str


class UserOut(BaseModel):
    id: int
    username: str
    role: RoleEnum
    document: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


# ---------------- JOBS ----------------

class JobCreate(BaseModel):
    title: str = Field(..., min_length=3, max_length=150)
    description: str
    target_limit: int = Field(..., gt=0)
    price: float = Field(default=0, ge=0)


class JobOut(BaseModel):
    id: int
    title: str
    description: str
    status: JobStatus

    contractor_id: int
    target_limit: int
    applicant_count: int

    assigned_truck_owner_id: Optional[int] = None

    created_at: Optional[datetime] = None

    application_id: Optional[int] = None
    order_number: Optional[str] = None
    location: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


# ---------------- JOB APPLICATIONS ----------------

class JobApplicationCreate(BaseModel):
    job_id: int


class JobApplicationOut(BaseModel):
    id: int
    job_id: int
    truck_owner_id: int
    status: ApplicationStatus

    model_config = ConfigDict(from_attributes=True)


# ---------------- SLIPS ----------------

class SlipUpload(BaseModel):
    job_id: int


# ---------------- FEEDBACK ----------------

class FeedbackCreate(BaseModel):
    job_id: int
    rating: int = Field(..., ge=1, le=5)
    comment: Optional[str] = None


class FeedbackOut(BaseModel):
    id: int
    job_id: int
    truck_owner_id: int
    contractor_id: int

    rating: int
    comment: Optional[str]

    model_config = ConfigDict(from_attributes=True)


# ---------------- JOB STATUS ----------------

class JobStatusUpdate(BaseModel):
    status: JobStatus

# ---------------- ASSIGN ORDER ----------------

class AssignOrderPayload(BaseModel):
    order_number: str
    location: str

# -------------------------
# PASSWORD RESET
# -------------------------
class ForgotPasswordRequest(BaseModel):
    email: str


class ResetPasswordRequest(BaseModel):
    email: str
    code: str
    new_password: str
