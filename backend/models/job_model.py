# backend/models/job_model.py
import enum
from sqlalchemy import Column, Integer, String, Enum, ForeignKey
from backend.database import Base
from sqlalchemy.orm import relationship 

class JobStatus(enum.Enum):
    pending = "pending"
    completed = "completed"

class ApplicationStatus(enum.Enum):
    applied = "applied"
    accepted = "accepted"

    
    
    
    

