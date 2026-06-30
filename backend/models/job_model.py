# backend/models/job_model.py
import enum
from sqlalchemy import Column, Integer, String, Enum, ForeignKey
from sqlalchemy.orm import relationship
from backend.database import Base


class JobStatus(enum.Enum):
    pending = "pending"
    completed = "completed"


class ApplicationStatus(enum.Enum):
    applied = "applied"
    accepted = "accepted"


class WorkOrder(Base):
    __tablename__ = "work_orders"

    id = Column(Integer, primary_key=True, index=True)

    title = Column(String, nullable=False)
    description = Column(String, nullable=True)

    price = Column(Integer, nullable=False)

    status = Column(Enum(JobStatus), default=JobStatus.pending)

    truck_owner_id = Column(Integer, ForeignKey("users.id"))

    # optional relationship
    owner = relationship("User", back_populates="jobs_created")