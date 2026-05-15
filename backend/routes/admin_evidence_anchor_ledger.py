# backend/routes/admin_evidence_anchor_ledger.py

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models.evidence_anchor_ledger import EvidenceAnchorLedger
from backend.utils.rbac import require_roles

router = APIRouter(
    prefix="/admin/evidence-anchor-ledger",
    tags=["Admin"]
)

@router.get("/")
def list_anchor_ledger(
    q: str | None = Query(None),
    db: Session = Depends(get_db),
    _=Depends(require_roles(["ADMIN"])),  # ✅ FIX
):
    query = db.query(EvidenceAnchorLedger)

    if q:
        like = f"%{q}%"
        query = query.filter(
            EvidenceAnchorLedger.evidence_hash.ilike(like) |
            EvidenceAnchorLedger.ipfs_cid.ilike(like) |
            EvidenceAnchorLedger.blockchain_tx_hash.ilike(like) |
            EvidenceAnchorLedger.file_name.ilike(like)
        )

    return query.order_by(
        EvidenceAnchorLedger.created_at.desc()
    ).all()
