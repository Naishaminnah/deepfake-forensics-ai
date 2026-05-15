# backend/routes/evidence_verify_anchor.py

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from backend.database import get_db
from backend.models.evidence_anchor_ledger import EvidenceAnchorLedger
from backend.utils.rbac import require_roles

router = APIRouter(prefix="/evidence/anchor", tags=["Evidence Anchor Ledger"])

@router.get("/by-hash/{evidence_hash}")
def get_anchor_record(
    evidence_hash: str,
    db: Session = Depends(get_db),
    _=Depends(require_roles(["LEGAL_AUTHORITY", "ADMIN"]))
):
    records = (
    db.query(EvidenceAnchorLedger)
    .filter(EvidenceAnchorLedger.evidence_hash == evidence_hash)
    .all()
)


    if not records:
       return {
          "status": "NOT_FOUND",
          "evidence_hash": evidence_hash
    }

    return {
       "status": "FOUND",
       "evidence_hash": evidence_hash,
       "cases": [
   {
      "case_id": r.case_id,
      "evidence_hash": r.evidence_hash,   # ⭐ ADD THIS
      "ipfs_cid": r.ipfs_cid,
      "metadata_hash": r.metadata_hash,
      "file_name": r.file_name,
      "file_size": r.file_size,
      "mime_type": r.mime_type,
      "evidence_type": r.evidence_type,
      "blockchain_tx_hash": r.blockchain_tx_hash,
      "registered_by": r.registered_by,
      "created_at": r.created_at
   }
   for r in records
]

}
