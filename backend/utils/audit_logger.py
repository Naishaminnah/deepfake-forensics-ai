from sqlalchemy.orm import Session
from backend.models.audit_log import AuditLog

def log_action(
    db: Session,
    user_id: int,
    username: str,
    role: str,
    action: str,
    resource: str = None,
    ip_address: str = None
):
    log = AuditLog(
        user_id=user_id,
        username=username,
        role=role,
        action=action,
        resource=resource,
        ip_address=ip_address
    )
    db.add(log)
    db.commit()
