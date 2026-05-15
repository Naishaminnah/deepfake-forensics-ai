# backend/routes/audio_detect.py

import os
from fastapi import APIRouter, UploadFile, File, HTTPException, Depends, Form
from fastapi.responses import JSONResponse
import tempfile
from sqlalchemy.orm import Session

from backend.models.audio_detector import AudioDeepfakeDetector
from backend.database import get_db
from backend.utils.current_user import get_current_user
from backend.utils.hash_utils import generate_sha256
from backend.utils.evidence_logger import log_evidence
from backend.models.user import User

router = APIRouter()

MODEL_PATH = "best_audio_model.pth"
detector = AudioDeepfakeDetector(MODEL_PATH, device="cuda")


@router.post("/detect/audio")
async def detect_audio(
    file: UploadFile = File(...),
    case_id: int | None = Form(None),
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if current_user["role"] == "FORENSIC_ANALYST" and case_id is None:
        raise HTTPException(status_code=400, detail="case_id is required for forensic analysis")

    if not file.filename.lower().endswith((".wav", ".flac", ".mp3")):
        raise HTTPException(status_code=400, detail="Invalid audio format")

    with tempfile.NamedTemporaryFile(delete=False, suffix=file.filename[-4:]) as tmp:
        file_bytes = await file.read()
        tmp.write(file_bytes)
        tmp_path = tmp.name

    try:
        result = detector.predict(tmp_path)
        evidence_hash = generate_sha256(file_bytes)

        user = db.query(User).filter(
            User.username == current_user["username"]
        ).first()

        evidence_record = log_evidence(
            db=db,
            case_id=case_id,
            evidence_hash=evidence_hash,
            evidence_type="audio",
            file_name=file.filename,
            file_size=len(file_bytes),
            mime_type=file.content_type,
            detection_result=result.get("label"),
            confidence_score=max(
                    result.get("real_confidence", 0),
                    result.get("fake_confidence", 0)
            ),

            model_used="AudioCNN_v1",
            uploader_id=user.id if user else None,
        )

        if current_user["role"] == "FORENSIC_ANALYST":
            return JSONResponse({
                "prediction": result,
                "hash": evidence_hash,
                "ledger_id": evidence_record.id,
                "case_id": case_id,
                "status": "LOGGED_LOCALLY",
            })

        return JSONResponse(result)

    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)
