# backend/routes/stylegan_reconstruct.py

import torch
from fastapi import APIRouter, UploadFile, File, Depends
from fastapi.responses import StreamingResponse
from io import BytesIO
from PIL import Image
from torchvision import transforms

from sqlalchemy.orm import Session
from backend.database import get_db
from backend.utils.current_user import get_current_user
from backend.utils.hash_utils import generate_sha256
from backend.utils.evidence_logger import log_evidence
from backend.models.user import User

from backend.stylegan.stylegan_loader import StyleGAN2Loader
from backend.stylegan.stylegan_latent_projector import StyleGANProjector

router = APIRouter()

DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
STYLEGAN_PKL = "backend/stylegan_weights/stylegan2_ffhq_config_f.pkl"

stylegan_loader = StyleGAN2Loader(STYLEGAN_PKL, device=DEVICE)
projector = StyleGANProjector(stylegan_loader.G, device=DEVICE, steps=400, lr=0.01)


@router.post("/gan/stylegan/reconstruct")
async def reconstruct_face(
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    img_bytes = await file.read()
    img = Image.open(BytesIO(img_bytes)).convert("RGB")

    target = projector.preprocess(img)
    w_opt, out_tensor = projector.project(target)

    # -------- Evidence Ledger (silent) --------
    evidence_hash = generate_sha256(img_bytes)

    user = db.query(User).filter(
        User.username == current_user["username"]
    ).first()

    log_evidence(
        db=db,
        evidence_hash=evidence_hash,
        evidence_type="stylegan_reconstruction",
        file_name=file.filename,
        file_size=len(img_bytes),
        mime_type=file.content_type,
        detection_result="RECONSTRUCTED",
        confidence_score=None,
        model_used="StyleGAN2_Projector",
        uploader_id=user.id if user else None,
    )

    out_img = out_tensor.squeeze(0).clamp(-1, 1).add(1).div(2)
    out_img = transforms.ToPILImage()(out_img)

    buffer = BytesIO()
    out_img.save(buffer, format="PNG")
    buffer.seek(0)

    return StreamingResponse(buffer, media_type="image/png")
