# backend/routes/gan_reconstruct.py

from fastapi import APIRouter, UploadFile, File, Depends, Form, HTTPException
from fastapi.responses import StreamingResponse
from io import BytesIO
from PIL import Image
import torch

from sqlalchemy.orm import Session
from backend.database import get_db
from backend.utils.current_user import get_current_user
from backend.utils.hash_utils import generate_sha256
from backend.utils.evidence_logger import log_evidence
from backend.models.user import User

from backend.models.biggan_loader import load_gan
from backend.models.latent_projector import LatentProjector
from backend.models.reconstruction_utils import preprocess_image

router = APIRouter()
DEVICE = 'cuda' if torch.cuda.is_available() else 'cpu'

G = load_gan(device=DEVICE)
projector = LatentProjector(G, device=DEVICE, steps=500, lr=0.03)


@router.post("/gan/reconstruct")
async def reconstruct_image(
    file: UploadFile = File(...),
    case_id: int | None = Form(None),
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):  
    
    
    
    if current_user["role"] == "FORENSIC_ANALYST" and case_id is None:
        raise HTTPException(status_code=400, detail="case_id is required for forensic analysis")

    img_bytes = await file.read()
    img = Image.open(BytesIO(img_bytes)).convert("RGB")
    img_tensor = preprocess_image(img).to(DEVICE)

    _, recon_img = projector.project(img_tensor)

    evidence_hash = generate_sha256(img_bytes)

    user = db.query(User).filter(
        User.username == current_user["username"]
    ).first()

    log_evidence(
        db=db,
        case_id=case_id,
        evidence_hash=evidence_hash,
        evidence_type="gan_reconstruction",
        file_name=file.filename,
        file_size=len(img_bytes),
        mime_type=file.content_type,
        detection_result="RECONSTRUCTED",
        confidence_score=None,
        model_used="BigGAN_LatentProjector",
        uploader_id=user.id if user else None,
    )

    out = BytesIO()
    recon_img.save(out, format="PNG")
    out.seek(0)

    return StreamingResponse(out, media_type="image/png")
