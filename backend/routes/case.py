from fastapi import APIRouter, Depends, Form, HTTPException
from sqlalchemy.orm import Session
import uuid

from backend.database import get_db
from backend.models.user import User
from backend.models.case import Case
from backend.utils.rbac import require_roles


router = APIRouter(prefix="/cases", tags=["Cases"])

@router.post("/create")
def create_case(
    title: str = Form(...),
    description: str = Form(""),
    db: Session = Depends(get_db),
    user=Depends(require_roles(["FORENSIC_ANALYST"]))
):
    db_user = db.query(User).filter(User.username == user["username"]).first()


    if not db_user:
        raise HTTPException(status_code=401, detail="User not found")

    case = Case(
        case_id=f"CASE-{uuid.uuid4().hex[:10].upper()}",
        title=title,
        description=description,
        created_by=db_user.id,  # ✅ FIXED
    )

    db.add(case)
    db.commit()
    db.refresh(case)

    return {
         "id": case.id,
         "case_id": case.case_id,
         "title": case.title,
         "description": case.description,
         "created_at": case.created_at
        }



@router.get("/")
def list_cases(
    db: Session = Depends(get_db),
    _=Depends(require_roles(["FORENSIC_ANALYST", "LEGAL_AUTHORITY"]))
):
    return db.query(Case).order_by(Case.created_at.desc()).all()
