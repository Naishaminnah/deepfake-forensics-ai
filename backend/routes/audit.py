from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models.audit_log import AuditLog
from backend.utils.rbac import require_roles

router = APIRouter(prefix="/audit", tags=["Audit Logs"])


@router.get("/")
def get_audit_logs(
    db: Session = Depends(get_db),
    _=Depends(require_roles(["ADMIN", "FORENSIC_ANALYST", "LEGAL_AUTHORITY"]))
):
    """
    Retrieve forensic audit logs.
    Accessible only to ADMIN, FORENSIC_ANALYST, LEGAL_AUTHORITY
    """
    return (
        db.query(AuditLog)
        .order_by(AuditLog.timestamp.desc())
        .all()
    )
