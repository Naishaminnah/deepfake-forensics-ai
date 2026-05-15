# backend/routes/gan_detect.py

from fastapi import APIRouter, UploadFile, File, Depends, Form, HTTPException
from fastapi.responses import JSONResponse
import tempfile
import os

from sqlalchemy.orm import Session
from backend.database import get_db
from backend.utils.current_user import get_current_user
from backend.utils.hash_utils import generate_sha256
from backend.utils.evidence_logger import log_evidence
from backend.models.user import User
from backend.models.gan_fingerprinter_infer import GANDetector

router = APIRouter()
detector = GANDetector()


@router.post("/detect/gan")
async def detect_gan_type(
    file: UploadFile = File(...),
    case_id: int | None = Form(None),
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    
    
    if current_user["role"] == "FORENSIC_ANALYST" and case_id is None:
        raise HTTPException(status_code=400, detail="case_id is required for forensic analysis")

    file_bytes = await file.read()
    tmp_path = None

    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as tmp:
            tmp.write(file_bytes)
            tmp_path = tmp.name

        result = detector.predict(tmp_path)
        evidence_hash = generate_sha256(file_bytes)

        user = db.query(User).filter(
            User.username == current_user["username"]
        ).first()

        log_evidence(
            db=db,
            case_id=case_id,
            evidence_hash=evidence_hash,
            evidence_type="gan_fingerprint",
            file_name=file.filename,
            file_size=len(file_bytes),
            mime_type=file.content_type,
            detection_result=result.get("gan_type"),
            confidence_score=result.get("confidence"),
            model_used="GANFingerprinter_v1",
            uploader_id=user.id if user else None,
        )

        if user and user.role == "FORENSIC_ANALYST":
            return JSONResponse({
                **result,
                "evidence_hash": evidence_hash,
                "case_id": case_id,
                "ledger_status": "LOGGED_LOCALLY"
            })

        return JSONResponse(result)

    finally:
        if tmp_path and os.path.exists(tmp_path):
            os.remove(tmp_path)
