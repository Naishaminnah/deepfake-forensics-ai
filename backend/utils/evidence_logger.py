# backend/utils/evidence_logger.py

from sqlalchemy.orm import Session
from backend.models.evidence_ledger import EvidenceLedger

def log_evidence(
    db: Session,
    case_id: int,
    evidence_hash: str,
    evidence_type: str,
    file_name: str,
    file_size: int,
    mime_type: str,
    detection_result: str,
    confidence_score: float,
    model_used: str,
    uploader_id: int,
):
    record = EvidenceLedger(
        case_id=case_id,
        evidence_hash=evidence_hash,
        evidence_type=evidence_type,
        file_name=file_name,
        file_size=file_size,
        mime_type=mime_type,
        detection_result=detection_result,
        confidence_score=confidence_score,
        model_used=model_used,
        uploader_id=uploader_id,
    )

    db.add(record)
    db.commit()
    db.refresh(record)

    return record
