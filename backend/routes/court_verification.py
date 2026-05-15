from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
from hashlib import sha256
import requests

from backend.models.ethereum_service import get_evidence_from_chain
from backend.utils.rbac import require_roles

router = APIRouter(prefix="/forensics", tags=["Court Verification"])

PINATA_GATEWAY = "https://gateway.pinata.cloud/ipfs"

# ✅ Allowed evidence types (court-accepted)
ALLOWED_EVIDENCE_TYPES = {"image", "video", "audio"}


@router.post("/verify")
async def verify_evidence_for_court(
    file: UploadFile = File(...),
    _=Depends(require_roles(["LEGAL_AUTHORITY"]))
):
    """
    Court-grade verification using blockchain + IPFS CID validation.
    READ ONLY.
    """

    # 🔒 Enforce supported evidence formats
    if not file.content_type:
        raise HTTPException(
            status_code=400,
            detail="Unable to determine file type"
        )

    major_type = file.content_type.split("/")[0]

    if major_type not in ALLOWED_EVIDENCE_TYPES:
        raise HTTPException(
            status_code=400,
            detail="Only image, video, and audio evidence are supported"
        )

    # 1️⃣ Read uploaded file
    uploaded_bytes = await file.read()
    uploaded_hash = sha256(uploaded_bytes).hexdigest()

    # 2️⃣ Fetch blockchain record (FIXED)
    evidence = get_evidence_from_chain(uploaded_hash)

    # ✅ FIX: Not found is a VALID forensic verdict
    if evidence is None:
        return {
            "verdict": "NOT_A_MATCH",
            "on_chain": False,
            "uploaded_hash": uploaded_hash,
            "confidence": "HIGH",
            "reason": "Evidence hash not found on blockchain",
        }

    # 3️⃣ Fetch original file from IPFS
    ipfs_url = f"{PINATA_GATEWAY}/{evidence.ipfs_cid}"

    resp = requests.get(ipfs_url, timeout=20)
    if resp.status_code != 200:
        raise HTTPException(
            status_code=502,
            detail="Failed to retrieve evidence from IPFS gateway"
        )

    ipfs_bytes = resp.content
    ipfs_hash = sha256(ipfs_bytes).hexdigest()

    # 4️⃣ Triple verification
    match = (
        uploaded_hash == evidence.evidence_hash
        and ipfs_hash == evidence.evidence_hash
    )

    return {
        "verdict": "MATCH" if match else "MISMATCH",
        "uploaded_hash": uploaded_hash,
        "blockchain_hash": evidence.evidence_hash,
        "ipfs_hash": ipfs_hash,
        "ipfs_cid": evidence.ipfs_cid,
        "registered_by": evidence.registered_by,
        "timestamp": evidence.timestamp,
        "tx_hash": evidence.tx_hash,
    }
