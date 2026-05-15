# backend/routes/image_detect.py

from fastapi import APIRouter, UploadFile, File, Depends, HTTPException, Form
import os, shutil
from sqlalchemy.orm import Session

from backend.models.image_detector import predict_image
from backend.database import get_db
from backend.utils.current_user import get_current_user
from backend.utils.hash_utils import generate_sha256
from backend.utils.evidence_logger import log_evidence
from backend.models.user import User


router = APIRouter()
UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)


@router.post("/detect/image")
async def detect_image(
    file: UploadFile = File(...),
    case_id: int | None = Form(None),
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    
    if current_user["role"] == "FORENSIC_ANALYST" and case_id is None:
        raise HTTPException(status_code=400, detail="case_id is required for forensic analysis")

    file_path = os.path.join(UPLOAD_DIR, file.filename)

    with open(file_path, "wb") as f:
        shutil.copyfileobj(file.file, f)

    try:
        result = predict_image(file_path)

        with open(file_path, "rb") as f:
            file_bytes = f.read()

        evidence_hash = generate_sha256(file_bytes)

        user = db.query(User).filter(
            User.username == current_user["username"]
        ).first()

        evidence_record = log_evidence(
            db=db,
            case_id=case_id,
            evidence_hash=evidence_hash,
            evidence_type="image",
            file_name=file.filename,
            file_size=len(file_bytes),
            mime_type=file.content_type,
            detection_result=result.get("label"),
            confidence_score=result.get("confidence"),
            model_used="ImageCNN_v1",
            uploader_id=user.id if user else None,
        )

        if current_user["role"] == "FORENSIC_ANALYST":
            return {
                "filename": file.filename,
                "prediction": result,
                "hash": evidence_hash,
                "ledger_id": evidence_record.id,
                "case_id": case_id,
                "status": "LOGGED_LOCALLY",
            }

        return {
            "filename": file.filename,
            **result
        }

    finally:
        if os.path.exists(file_path):
            os.remove(file_path)
