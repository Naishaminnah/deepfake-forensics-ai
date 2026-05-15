# backend/models/evidence_ledger.py

from sqlalchemy import Column, Integer, String, DateTime, Float , ForeignKey
from sqlalchemy.sql import func
from backend.database import Base

class EvidenceLedger(Base):
    __tablename__ = "evidence_ledger"

    id = Column(Integer, primary_key=True, index=True)

    case_id = Column(Integer, ForeignKey("cases.id"), index=True)

    evidence_hash = Column(String(64), index=True, nullable=False)
    evidence_type = Column(String(32), nullable=False)

    file_name = Column(String(255))
    file_size = Column(Integer)
    mime_type = Column(String(64))
    
    analysis_type = Column(String(64))
    detection_result = Column(String(32))
    confidence_score = Column(Float)

    model_used = Column(String(64))
    uploader_id = Column(Integer)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
