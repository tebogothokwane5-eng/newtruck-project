import enum
from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy import Enum as SQLEnum
from backend.database import Base


# ---------------- ENUM ----------------
class WorkOrderStatus(str, enum.Enum):
    pending = "pending"
    completed = "completed"


# ---------------- MODEL ----------------
class WorkOrder(Base):
    __tablename__ = "work_orders"

    id = Column(Integer, primary_key=True, index=True)

    title = Column(String, nullable=False)
    description = Column(String, nullable=True)
    price = Column(Integer, nullable=False)

    status = Column(
        SQLEnum(WorkOrderStatus, native_enum=False),
        default=WorkOrderStatus.pending,
        nullable=False
    )

    truck_owner_id = Column(
        Integer,
        ForeignKey("users.id"),
        nullable=False
    )

    truck_owner = relationship(
        "User",
        back_populates="work_orders"
    )
    payments = relationship("Payment", back_populates="job")