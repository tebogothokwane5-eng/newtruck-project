from sqlalchemy import Column, Integer, Float, String, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from backend.database import Base


class Payment(Base):
    __tablename__ = "payments"

    id = Column(Integer, primary_key=True, index=True)

    job_id = Column(Integer, ForeignKey("work_orders.id"), nullable=False)
    contractor_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    truck_owner_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    amount = Column(Float, nullable=False)
    status = Column(String, default="pending")
    reference = Column(String, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # optional relationships (recommended)
    job = relationship("WorkOrder")
    contractor = relationship("User", foreign_keys=[contractor_id])
    truck_owner = relationship("User", foreign_keys=[truck_owner_id])