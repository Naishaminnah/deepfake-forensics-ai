from fastapi import APIRouter, UploadFile, File, HTTPException, Depends, Form
from hashlib import sha256
import json
import requests
import os

from sqlalchemy.orm import Session
from web3.exceptions import Web3RPCError

from backend.database import get_db
from backend.models.evidence_anchor_ledger import EvidenceAnchorLedger
from backend.models.ethereum_service import (
    register_evidence_on_chain,
    get_evidence_from_chain,
)
from backend.utils.rbac import require_roles
from backend.utils.current_user import get_current_user
from backend.models.user import User


router = APIRouter(prefix="/forensics", tags=["Forensic Upload"])

PINATA_PIN_URL = "https://api.pinata.cloud/pinning/pinFileToIPFS"


# -----------------------------------------------------------
# Upload Bytes To Pinata
# -----------------------------------------------------------
def upload_bytes_to_pinata(data: bytes, filename: str) -> str:
    headers = {
        "pinata_api_key": os.getenv("PINATA_API_KEY"),
        "pinata_secret_api_key": os.getenv("PINATA_API_SECRET"),
    }

    files = {"file": (filename, data)}

    response = requests.post(
        PINATA_PIN_URL,
        headers=headers,
        files=files,
        timeout=30,
    )

    if response.status_code != 200:
        raise RuntimeError(response.text)

    return response.json()["IpfsHash"]


# -----------------------------------------------------------
# Upload + Register Evidence
# -----------------------------------------------------------
@router.post("/upload-and-register")
async def upload_and_register_evidence(
    file: UploadFile = File(...),
    case_id: int = Form(...),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
    _=Depends(require_roles(["FORENSIC_ANALYST"]))
):

    data = await file.read()

    if not file.content_type:
        raise HTTPException(400, "Unknown file type")

    evidence_type = file.content_type.split("/")[0]

    if evidence_type not in {"image", "video", "audio"}:
        raise HTTPException(400, "Unsupported evidence type")

    user = db.query(User).filter(
        User.username == current_user["username"]
    ).first()

    if not user:
        raise HTTPException(404, "User not found")

    # -----------------------------------------------------------
    # HASH EVIDENCE
    # -----------------------------------------------------------
    evidence_hash = sha256(data).hexdigest()

    # -----------------------------------------------------------
    # ⭐ STEP 0 — BLOCK SAME CASE DUPLICATES
    # -----------------------------------------------------------
    case_duplicate = (
        db.query(EvidenceAnchorLedger)
        .filter(
            EvidenceAnchorLedger.case_id == case_id,
            EvidenceAnchorLedger.evidence_hash == evidence_hash,
        )
        .first()
    )

    if case_duplicate:
        raise HTTPException(
            status_code=409,
            detail="This evidence is already registered for this case."
        )

    # -----------------------------------------------------------
    # ⭐ STEP 1 — CHECK BLOCKCHAIN FIRST
    # -----------------------------------------------------------
    chain_existing = get_evidence_from_chain(evidence_hash)

    if chain_existing:

        # Check local ledger
        existing_anchor = (
            db.query(EvidenceAnchorLedger)
            .filter(EvidenceAnchorLedger.evidence_hash == evidence_hash)
            .first()
        )

        # Recover ledger if missing
        if not existing_anchor:
            existing_anchor = EvidenceAnchorLedger(
                case_id=case_id,
                evidence_hash=chain_existing.evidence_hash,
                ipfs_cid=chain_existing.ipfs_cid,
                metadata_hash="CHAIN_RECOVERED",
                evidence_type=chain_existing.evidence_type,
                file_name=file.filename,
                file_size=len(data),
                mime_type=file.content_type,
                blockchain_tx_hash=chain_existing.tx_hash,
                registered_by=chain_existing.registered_by,
            )

            db.add(existing_anchor)
            db.commit()
            db.refresh(existing_anchor)

        else:
            new_anchor = EvidenceAnchorLedger(
                case_id=case_id,
                evidence_hash=existing_anchor.evidence_hash,
                ipfs_cid=existing_anchor.ipfs_cid,
                metadata_hash=existing_anchor.metadata_hash,
                evidence_type=existing_anchor.evidence_type,
                file_name=file.filename,
                file_size=len(data),
                mime_type=file.content_type,
                blockchain_tx_hash=existing_anchor.blockchain_tx_hash,
                registered_by=existing_anchor.registered_by,
            )

            db.add(new_anchor)
            db.commit()

        return {
            "status": "EVIDENCE_REUSED",
            "case_id": case_id,
            "evidence_hash": chain_existing.evidence_hash,
            "ipfs_cid": chain_existing.ipfs_cid,
            "evidence_type": chain_existing.evidence_type,
            "registered_by": chain_existing.registered_by,
            "tx_hash": chain_existing.tx_hash,
            "timestamp": chain_existing.timestamp,
        }

    # -----------------------------------------------------------
    # ⭐ STEP 2 — NEW BLOCKCHAIN ANCHOR
    # -----------------------------------------------------------
    ipfs_cid = upload_bytes_to_pinata(
        data=data,
        filename=file.filename or "evidence"
    )

    metadata = {
        "filename": file.filename,
        "content_type": file.content_type,
        "size_bytes": len(data),
        "evidence_type": evidence_type,
    }

    metadata_hash = sha256(
        json.dumps(metadata, sort_keys=True).encode()
    ).hexdigest()

    try:
        chain_record = register_evidence_on_chain(
            evidence_hash=evidence_hash,
            ipfs_cid=ipfs_cid,
            evidence_type=evidence_type,
        )

    except Web3RPCError as e:

        if "Evidence already exists" in str(e):

            chain_existing = get_evidence_from_chain(evidence_hash)

            if not chain_existing:
                raise HTTPException(500, "Blockchain duplicate but record missing")

            return {
                "status": "EVIDENCE_REUSED",
                "case_id": case_id,
                "evidence_hash": chain_existing.evidence_hash,
                "ipfs_cid": chain_existing.ipfs_cid,
                "evidence_type": chain_existing.evidence_type,
                "registered_by": chain_existing.registered_by,
                "tx_hash": chain_existing.tx_hash,
                "timestamp": chain_existing.timestamp,
            }

        raise

    # -----------------------------------------------------------
    # STORE IN LEDGER
    # -----------------------------------------------------------
    anchor = EvidenceAnchorLedger(
        case_id=case_id,
        evidence_hash=evidence_hash,
        ipfs_cid=ipfs_cid,
        metadata_hash=metadata_hash,
        evidence_type=evidence_type,
        file_name=file.filename,
        file_size=len(data),
        mime_type=file.content_type,
        blockchain_tx_hash=chain_record.tx_hash,
        registered_by=user.id,
    )

    db.add(anchor)
    db.commit()
    db.refresh(anchor)

    return {
        "status": "EVIDENCE_NEWLY_ANCHORED",
        "case_id": case_id,
        "evidence_hash": evidence_hash,
        "ipfs_cid": ipfs_cid,
        "metadata_hash": metadata_hash,
        "evidence_type": chain_record.evidence_type,
        "registered_by": chain_record.registered_by,
        "tx_hash": chain_record.tx_hash,
        "timestamp": chain_record.timestamp,
    }
