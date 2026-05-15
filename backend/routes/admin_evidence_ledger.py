# backend/routes/admin_evidence_ledger.py

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models.evidence_ledger import EvidenceLedger
from backend.utils.rbac import require_roles

router = APIRouter(
    prefix="/admin/evidence-ledger",
    tags=["Admin"]
)

@router.get("/")
def list_evidence_ledger(
    q: str | None = Query(None),
    db: Session = Depends(get_db),
    _=Depends(require_roles(["ADMIN"])),  # ✅ FIX
):
    query = db.query(EvidenceLedger)

    if q:
        like = f"%{q}%"
        query = query.filter(
            EvidenceLedger.evidence_hash.ilike(like) |
            EvidenceLedger.file_name.ilike(like) |
            EvidenceLedger.evidence_type.ilike(like) |
            EvidenceLedger.detection_result.ilike(like) |
            EvidenceLedger.model_used.ilike(like)
        )

    return query.order_by(
        EvidenceLedger.created_at.desc()
    ).all()
