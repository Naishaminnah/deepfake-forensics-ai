# backend/models/evidence_anchor_ledger.py

from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.sql import func
from backend.database import Base

class EvidenceAnchorLedger(Base):
    __tablename__ = "evidence_anchor_ledger"

    id = Column(Integer, primary_key=True, index=True)

    case_id = Column(Integer, ForeignKey("cases.id"), index=True)

    evidence_hash = Column(String(64), index=True, nullable=False)
    ipfs_cid = Column(String(128), nullable=False)
    metadata_hash = Column(String(64), nullable=False)

    evidence_type = Column(String(32))
    file_name = Column(String(255))
    file_size = Column(Integer)
    mime_type = Column(String(64))

    blockchain_tx_hash = Column(String(128))
    registered_by = Column(Integer)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
