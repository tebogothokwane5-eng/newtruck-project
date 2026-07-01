import enum
from sqlalchemy import (
    Column, Integer, String, Float,
    Enum as SQLEnum, ForeignKey,
    Boolean, DateTime, Text
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from backend.database import Base


# ---------------- ENUMS ----------------

class RoleEnum(str, enum.Enum):
    truck_owner = "truck_owner"
    main_contractor = "main_contractor"
    admin = "admin"


class JobStatus(str, enum.Enum):
    pending = "pending"
    accepted = "accepted"
    rejected = "rejected"
    completed = "completed"


class ApplicationStatus(str, enum.Enum):
    pending = "pending"
    approved = "approved"
    rejected = "rejected"


# ---------------- USER ----------------

import enum
from sqlalchemy import (
    Column, Integer, String, Enum as SQLEnum,
    Boolean, Text
)
from sqlalchemy.orm import relationship
from backend.database import Base


# ---------------- ENUM ----------------

class RoleEnum(str, enum.Enum):
    truck_owner = "truck_owner"
    main_contractor = "main_contractor"
    admin = "admin"


# ---------------- USER ----------------

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)

    username = Column(String(50), unique=True, index=True, nullable=False)
    email = Column(String(120), unique=True, index=True, nullable=False)

    phone_no = Column(String(20))
    id_no = Column(String(50))

    password = Column(String(255), nullable=False)

    role = Column(SQLEnum(RoleEnum, native_enum=False), nullable=False)

    document = Column(Text)
    is_active = Column(Boolean, default=False)

    # ---------------- RELATIONSHIPS ----------------

    # Jobs created by contractor
    jobs_created = relationship(
        "Job",
        back_populates="contractor",
        foreign_keys="Job.contractor_id",
        cascade="all, delete-orphan"
    )

    # Applications submitted by truck owner
    applications = relationship(
        "JobApplication",
        back_populates="truck_owner",
        foreign_keys="JobApplication.truck_owner_id",
        cascade="all, delete-orphan"
    )

    # Feedback GIVEN (contractor → truck owner)
    feedback_given = relationship(
        "Feedback",
        back_populates="contractor",
        foreign_keys="Feedback.contractor_id",
        cascade="all, delete-orphan"
    )

    # Feedback RECEIVED (truck owner side)
    feedback_received = relationship(
        "Feedback",
        back_populates="truck_owner",
        foreign_keys="Feedback.truck_owner_id",
        cascade="all, delete-orphan"
    )

    # ✅ WorkOrders owned by this user (truck owner)
    work_orders = relationship(
        "WorkOrder",
        back_populates="owner",
        foreign_keys="WorkOrder.truck_owner_id",
        cascade="all, delete-orphan"
    )

# ---------------- JOB ----------------

class Job(Base):
    __tablename__ = "jobs"

    id = Column(Integer, primary_key=True, index=True)

    title = Column(String(150), nullable=False)
    description = Column(Text, nullable=False)

    target_limit = Column(Integer, default=0)
    applicant_count = Column(Integer, default=0)

    status = Column(
        SQLEnum(JobStatus, native_enum=False),
        default=JobStatus.pending,
        nullable=False,
        index=True
    )

    contractor_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), index=True)
    assigned_truck_owner_id = Column(Integer, ForeignKey("users.id"))

    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)

    order_number = Column(String(100))
    address = Column(String(255))
    latitude = Column(Float)
    longitude = Column(Float)

    # ---------------- RELATIONSHIPS ----------------

    contractor = relationship(
        "User",
        back_populates="jobs_created",
        foreign_keys=[contractor_id]
    )

    applications = relationship(
        "JobApplication",
        back_populates="job"
    )

    assigned_truck_owner = relationship(
        "User",
        foreign_keys=[assigned_truck_owner_id],
        viewonly=True
    )


# ---------------- JOB APPLICATION ----------------

class JobApplication(Base):
    __tablename__ = "job_applications"

    id = Column(Integer, primary_key=True, index=True)

    job_id = Column(Integer, ForeignKey("jobs.id", ondelete="CASCADE"), index=True)
    truck_owner_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), index=True)

    truck_pack = Column(String(255))

    status = Column(
        SQLEnum(ApplicationStatus, native_enum=False),
        default=ApplicationStatus.pending,
        index=True,
        nullable=False
    )

    order_number = Column(String(100))
    location = Column(String(255))

    # ---------------- RELATIONSHIPS ----------------

    job = relationship("Job", back_populates="applications")

    truck_owner = relationship(
        "User",
        back_populates="applications",
        foreign_keys=[truck_owner_id]
    )

    delivery_history = relationship(
        "DeliverySlip",
        back_populates="application"
    )


# ---------------- DELIVERY SLIP ----------------

class DeliverySlip(Base):
    __tablename__ = "delivery_slips"

    id = Column(Integer, primary_key=True, index=True)

    application_id = Column(
        Integer,
        ForeignKey("job_applications.id", ondelete="CASCADE"),
        index=True,
        nullable=False
    )

    file_path = Column(String(255), nullable=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    application = relationship(
        "JobApplication",
        back_populates="delivery_history"
    )


# ---------------- FEEDBACK ----------------

class Feedback(Base):
    __tablename__ = "feedback"

    id = Column(Integer, primary_key=True)

    job_id = Column(Integer, ForeignKey("jobs.id", ondelete="CASCADE"), index=True)

    truck_owner_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), index=True)
    contractor_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), index=True)

    rating = Column(Integer, nullable=False)
    comment = Column(String(500))

    # ---------------- RELATIONSHIPS ----------------

    truck_owner = relationship(
        "User",
        back_populates="feedback_received",
        foreign_keys=[truck_owner_id]
    )

    contractor = relationship(
        "User",
        back_populates="feedback_given",
        foreign_keys=[contractor_id]
    )