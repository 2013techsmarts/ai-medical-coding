from sqlalchemy import Boolean, Column, ForeignKey, Integer, String, Text, DateTime
from sqlalchemy.orm import relationship
from .database import Base
import datetime

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    email = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    role = Column(String) # "doctor" or "coder"
    is_active = Column(Boolean, default=True)

    notes = relationship("ClinicalNote", back_populates="doctor")
    approvals = relationship("Approval", back_populates="coder")

class ClinicalNote(Base):
    __tablename__ = "clinical_notes"

    id = Column(Integer, primary_key=True, index=True)
    doctor_id = Column(Integer, ForeignKey("users.id"))
    content = Column(Text)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    status = Column(String, default="pending") # pending, reviewed, approved
    final_codes_id = Column(Integer, ForeignKey("approvals.id"), nullable=True)

    doctor = relationship("User", back_populates="notes")
    coding_results = relationship("CodingResult", back_populates="note")
    final_approval = relationship("Approval", foreign_keys=[final_codes_id])

class CodingResult(Base):
    __tablename__ = "coding_results"

    id = Column(Integer, primary_key=True, index=True)
    note_id = Column(Integer, ForeignKey("clinical_notes.id"))
    ai_suggested_codes = Column(Text) # JSON string of codes
    confidence_score = Column(String)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    note = relationship("ClinicalNote", back_populates="coding_results")
    approvals = relationship("Approval", back_populates="coding_result")

class Approval(Base):
    __tablename__ = "approvals"

    id = Column(Integer, primary_key=True, index=True)
    coding_result_id = Column(Integer, ForeignKey("coding_results.id"))
    coder_id = Column(Integer, ForeignKey("users.id"))
    final_codes = Column(Text) # JSON string of final approved codes
    approved_at = Column(DateTime, default=datetime.datetime.utcnow)

    coding_result = relationship("CodingResult", back_populates="approvals")
    coder = relationship("User", back_populates="approvals")

class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    action = Column(String)
    user_id = Column(Integer, ForeignKey("users.id"))
    entity = Column(String) # e.g., note, coding_result
    entity_id = Column(Integer)
    details = Column(Text) # JSON string of what changed
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)
