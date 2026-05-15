from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime, timedelta

from backend.database import get_db
from backend.models.user import User
from backend.models.audit_log import AuditLog
from backend.utils.rbac import require_roles

router = APIRouter(prefix="/admin", tags=["Admin"])
@router.get("/summary")
def admin_summary(
    db: Session = Depends(get_db),
    _=Depends(require_roles(["ADMIN"]))
):
    # --------------------
    # USER METRICS
    # --------------------
    total_users = db.query(func.count(User.id)).scalar()

    users_by_role = (
        db.query(User.role, func.count(User.id))
        .group_by(User.role)
        .all()
    )

    users_by_role_dict = {role: count for role, count in users_by_role}

    # --------------------
    # AUDIT METRICS
    # --------------------
    total_events = db.query(func.count(AuditLog.id)).scalar()

    actions = (
        db.query(AuditLog.action, func.count(AuditLog.id))
        .group_by(AuditLog.action)
        .all()
    )

    actions_dict = {action: count for action, count in actions}

    last_24h_count = (
        db.query(func.count(AuditLog.id))
        .filter(AuditLog.timestamp >= datetime.utcnow() - timedelta(hours=24))
        .scalar()
    )

    # --------------------
    # SYSTEM STATUS
    # --------------------
    system_status = "OPERATIONAL"

    return {
        "users": {
            "total": total_users,
            "by_role": users_by_role_dict
        },
        "audit": {
            "total_events": total_events,
            "actions": actions_dict,
            "last_24h": last_24h_count
        },
        "system": {
            "status": system_status
        }
    }
