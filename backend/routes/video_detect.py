# backend/routes/video_detect.py

import os
import torch
import numpy as np
from fastapi import APIRouter, UploadFile, File, Depends, HTTPException, Form
from sqlalchemy.orm import Session
from pathlib import Path
import tempfile

from backend.utils.video_utils import extract_frames_from_video
from backend.models.frame_model import FrameModel
from backend.models.video_detector import load_temporal_model
from backend.config import DEVICE, MODEL_DIR
from backend.database import get_db
from backend.utils.current_user import get_current_user
from backend.utils.hash_utils import generate_sha256
from backend.utils.evidence_logger import log_evidence
from backend.models.user import User

router = APIRouter()

# ==========================
# Load models (UNCHANGED)
# ==========================
frame_model_path = Path(MODEL_DIR) / "frame_model_best.pth"
frame_model = FrameModel()
frame_ckpt = torch.load(frame_model_path, map_location=DEVICE)

if "model_state_dict" in frame_ckpt:
    frame_model.load_state_dict(frame_ckpt["model_state_dict"], strict=False)
else:
    frame_model.load_state_dict(frame_ckpt, strict=False)

frame_model.to(DEVICE)
frame_model.eval()

TEMPORAL_MODEL_TYPE = "lstm"

temporal_ckpt_path = Path(MODEL_DIR) / "video_temporal_best.pth"

temporal_model = load_temporal_model(
    model_type=TEMPORAL_MODEL_TYPE,
    model_path=temporal_ckpt_path,
    device=DEVICE
)

# ==========================
# Feature extraction helper
# ==========================
def extract_video_features(frames, batch_size=8):
    features = []
    with torch.no_grad():
        for i in range(0, len(frames), batch_size):
            batch = frames[i:i + batch_size]
            batch_tensor = torch.tensor(np.array(batch)).permute(0, 3, 1, 2).float() / 255.0
            batch_tensor = batch_tensor.to(DEVICE)
            batch_features = frame_model.extract_features(batch_tensor)
            features.append(batch_features.cpu())
    return torch.cat(features, dim=0)


@router.post("/detect/video")
async def detect_video(
    file: UploadFile = File(...),
    case_id: int | None = Form(None),
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    
    if current_user["role"] == "FORENSIC_ANALYST" and case_id is None:
        raise HTTPException(status_code=400, detail="case_id is required for forensic analysis")

    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as tmp:
            content = await file.read()
            tmp.write(content)
            tmp_path = tmp.name

        frames = extract_frames_from_video(tmp_path, frame_skip=5, resize=(224, 224))
        if not frames:
            raise HTTPException(status_code=400, detail="No frames extracted")

        features = extract_video_features(frames).unsqueeze(0).to(DEVICE)

        with torch.no_grad():
            preds = temporal_model(features)
            probs = torch.softmax(preds, dim=1).cpu().numpy()[0]

        prediction = {
            "fake_probability": round(float(probs[1]), 4),
            "real_probability": round(float(probs[0]), 4),
            "label": "Fake" if probs[1] > 0.5 else "Real"
        }

        user = db.query(User).filter(
            User.username == current_user["username"]
        ).first()

        evidence_hash = generate_sha256(content)

        evidence_record = log_evidence(
            db=db,
            case_id=case_id,
            evidence_hash=evidence_hash,
            evidence_type="video",
            file_name=file.filename,
            file_size=len(content),
            mime_type=file.content_type,
            detection_result=prediction["label"],
            confidence_score=max(prediction["fake_probability"], prediction["real_probability"]),
            model_used="VideoLSTM_v1",
            uploader_id=user.id if user else None,
        )

        if current_user["role"] in ["FORENSIC_ANALYST", "LEGAL_AUTHORITY"]:
            return {
                "filename": file.filename,
                "prediction": prediction,
                "hash": evidence_hash,
                "ledger_id": evidence_record.id,
                "case_id": case_id,
                "status": "LOGGED_LOCALLY",
            }

        return {
            "filename": file.filename,
            "prediction": prediction,
        }

    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)
