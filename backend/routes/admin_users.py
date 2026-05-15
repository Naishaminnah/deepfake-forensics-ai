from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models.user import User
from backend.utils.rbac import require_roles
from backend.utils.current_user import get_current_user
from backend.utils.audit_logger import log_action

router = APIRouter(prefix="/admin/users", tags=["Admin Users"])


@router.get("/")
def list_users(
    db: Session = Depends(get_db),
    _=Depends(require_roles(["ADMIN"]))
):
    users = db.query(User).all()
    return [
        {
            "id": u.id,
            "username": u.username,
            "role": u.role,
            "is_active": u.is_active,
        }
        for u in users
    ]


@router.put("/{user_id}/status")
def toggle_user_status(
    user_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
    _=Depends(require_roles(["ADMIN"]))
):
    user = db.query(User).filter(User.id == user_id).first()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # 🚫 Prevent admin from disabling self
    if user.username == current_user["username"]:
        log_action(
            db=db,
            user_id=user.id,
            username=current_user["username"],
            role=current_user["role"],
            action="SELF_DISABLE_ATTEMPT_BLOCKED",
            resource=f"admin/users/{user_id}/status",
            ip_address=request.client.host
        )
        raise HTTPException(
            status_code=403,
            detail="Admin cannot disable their own account"
        )

    # Toggle status
    user.is_active = not user.is_active
    db.commit()

    # ✅ Audit log
    log_action(
        db=db,
        user_id=user.id,
        username=current_user["username"],
        role=current_user["role"],
        action="USER_DISABLED" if not user.is_active else "USER_ENABLED",
        resource=f"admin/users/{user_id}/status",
        ip_address=request.client.host
    )

    return {
        "message": "User status updated",
        "is_active": user.is_active
    }
