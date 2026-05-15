from fastapi import APIRouter, Depends, HTTPException, Request, Form
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
import re

from backend.database import get_db
from backend.models.user import User
from backend.utils.auth_utils import (
    hash_password,
    verify_password,
    create_access_token
)
from backend.utils.rbac import require_roles
from backend.utils.audit_logger import log_action
from backend.utils.current_user import get_current_user

router = APIRouter(prefix="/auth", tags=["Authentication"])


# ============================
# PUBLIC SIGNUP (USER only)
# ============================
@router.post("/signup")
def signup(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db)
):
    username = username.strip()

    if not username.strip():
        raise HTTPException(status_code=400, detail="Username cannot be empty")

    if len(username) < 3:
        raise HTTPException(
            status_code=400,
            detail="Username must be at least 3 characters long"
        )
    USERNAME_REGEX = r"^[A-Za-z0-9_]+$"

    if not re.match(USERNAME_REGEX, username.strip()):
      raise HTTPException(
        status_code=400,
        detail="Username may contain only letters, numbers, and underscores"
    )
    if db.query(User).filter(User.username == username.strip()).first():
      raise HTTPException(400, "Username already taken")

    if password.strip() != password:
        raise HTTPException(
            status_code=400,
            detail="Password cannot start or end with spaces"
        )

    if len(password) < 8:
        raise HTTPException(
            status_code=400,
            detail="Password must be at least 8 characters long"
        )

    

    user = User(
        username=username,
        hashed_password=hash_password(password),
        role="USER",
        is_active=True
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    log_action(
        db=db,
        user_id=user.id,
        username=user.username,
        role=user.role,
        action="SIGNUP",
        resource="auth/signup",
        ip_address=request.client.host
    )

    return {"message": "Account created successfully. Please login."}


# ============================
# LOGIN (JWT)
# ============================
@router.post("/login")
def login(
    request: Request,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    username = form_data.username.strip()
    password = form_data.password

    user = db.query(User).filter(User.username == username).first()

    # 🔐 Do NOT leak which field failed
    if not user or not verify_password(password, user.hashed_password):
      log_action(
        db=db,
        user_id=user.id if user else None,
        username=username,
        role="UNKNOWN",
        action="FAILED_LOGIN",
        resource="auth/login",
        ip_address=request.client.host
    )
      raise HTTPException(
        status_code=401,
        detail="Invalid username or password"
    )

    
    if not user.is_active:
        raise HTTPException(
            status_code=403,
            detail="User account disabled"
        )

    log_action(
        db=db,
        user_id=user.id,
        username=user.username,
        role=user.role,
        action="LOGIN",
        resource="auth/login",
        ip_address=request.client.host
    )

    token = create_access_token({
        "sub": user.username,
        "role": user.role
    })

    return {
        "access_token": token,
        "token_type": "bearer",
        "role": user.role
    }


# ============================
# ADMIN: CREATE FORENSIC / LEGAL USERS
# ============================
@router.post("/create-user")
def create_user(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    role: str = Form(...),
    db: Session = Depends(get_db),
    admin=Depends(require_roles(["ADMIN"]))
):
    username = username.strip()
    

    if not re.match(r"^[A-Za-z0-9_]+$", username.strip()):
      raise HTTPException(
        status_code=400,
        detail="Username may contain only letters, numbers, and underscores"
    )


    if role not in ["FORENSIC_ANALYST", "LEGAL_AUTHORITY"]:
        raise HTTPException(
            status_code=400,
            detail="Only FORENSIC_ANALYST or LEGAL_AUTHORITY can be created"
        )

    if not username.strip():
        raise HTTPException(status_code=400, detail="Username cannot be empty")

    if len(username.strip()) < 3:
        raise HTTPException(
            status_code=400,
            detail="Username must be at least 3 characters long"
        )
    if db.query(User).filter(User.username == username.strip()).first():
        raise HTTPException(status_code=400, detail="Username  already taken")
    
    if password.strip() != password:
        raise HTTPException(
            status_code=400,
            detail="Password cannot start or end with spaces"
        )

    if len(password) < 8:
        raise HTTPException(
            status_code=400,
            detail="Password must be at least 8 characters long"
        )

    

    user = User(
        username=username,
        hashed_password=hash_password(password),
        role=role,
        is_active=True
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    log_action(
        db=db,
        user_id=user.id,
        username=user.username,
        role=user.role,
        action="CREATE_USER",
        resource=f"auth/create-user ({role})",
        ip_address=request.client.host
    )

    return {
        "message": f"{role} account created successfully",
        "username": username
    }
@router.get("/me")
def get_me(user=Depends(get_current_user)):
    return user