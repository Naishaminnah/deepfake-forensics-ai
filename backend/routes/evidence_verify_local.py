from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from backend.database import get_db
from backend.models.evidence_ledger import EvidenceLedger
from backend.utils.rbac import require_roles
from backend.utils.current_user import get_current_user

router = APIRouter(prefix="/evidence", tags=["Evidence Ledger"])

@router.get("/ledger/by-case/{case_id}")
def get_case_ledger(
    case_id: int,
    db: Session = Depends(get_db),
    user=Depends(get_current_user)
):
    if user["role"] not in ["LEGAL_AUTHORITY", "ADMIN"]:
        raise HTTPException(status_code=403, detail="Forbidden")

    records = (
        db.query(EvidenceLedger)
        .filter(EvidenceLedger.case_id == case_id)
        .all()
    )

    if not records:
        return {
            "status": "NOT_FOUND",
            "case_id": case_id
        }

    return {
        "status": "FOUND",
        "case_id": case_id,
        "records": [
            {
                "evidence_hash": r.evidence_hash,
                "file_name": r.file_name,
                "evidence_type": r.evidence_type,
                "analysis_type": r.analysis_type,
                "detection_result": r.detection_result,
                "confidence_score": r.confidence_score,
                "model_used": r.model_used,
                "created_at": r.created_at
            }
            for r in records
        ]
    }