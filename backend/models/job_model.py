import enum
from sqlalchemy import Column, Integer, String, Enum as SQLEnum, ForeignKey
from sqlalchemy.orm import relationship
from backend.database import Base


class JobStatus(str, enum.Enum):
    pending = "pending"
    completed = "completed"


class WorkOrder(Base):
    __tablename__ = "work_orders"

    id = Column(Integer, primary_key=True, index=True)

    title = Column(String, nullable=False)
    description = Column(String, nullable=True)
    price = Column(Integer, nullable=False)

    status = Column(
        SQLEnum(JobStatus, native_enum=False),
        default=JobStatus.pending,
        nullable=False
    )

    truck_owner_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    # ✅ RELATIONSHIP (correct)
    owner = relationship(
        "User",
        back_populates="work_orders"
    )