from datetime import datetime
from pathlib import Path
import json

from web3 import Web3
from web3.exceptions import ContractLogicError, Web3RPCError

from backend.core.blockchain_config import (
    GANACHE_URL,
    CONTRACT_ADDRESS,
    FORENSIC_ANALYST_ADDRESS,
)

from backend.models.blockchain_evidence import BlockchainEvidence

# -----------------------
# Web3 Setup
# -----------------------
w3 = Web3(Web3.HTTPProvider(GANACHE_URL))
if not w3.is_connected():
    raise RuntimeError("❌ Ganache is not running")

w3.eth.default_account = Web3.to_checksum_address(FORENSIC_ANALYST_ADDRESS)

# -----------------------
# Load Contract ABI
# -----------------------
ARTIFACT_PATH = (
    Path(__file__).resolve().parents[1]
    / "blockchain"
    / "EvidenceRegistry.json"
)

with open(ARTIFACT_PATH) as f:
    ABI = json.load(f)["abi"]

contract = w3.eth.contract(
    address=Web3.to_checksum_address(CONTRACT_ADDRESS),
    abi=ABI,
)

# -----------------------
# Helpers
# -----------------------
def _hash_evidence(evidence_hash: str) -> bytes:
    return Web3.keccak(text=evidence_hash)

# -----------------------
# Register Evidence
# -----------------------
def register_evidence_on_chain(
    evidence_hash: str,
    ipfs_cid: str,
    evidence_type: str,
) -> BlockchainEvidence:

    tx = contract.functions.registerEvidence(
        _hash_evidence(evidence_hash),
        ipfs_cid,
        evidence_type,
    ).transact({"gas": 300000})

    receipt = w3.eth.wait_for_transaction_receipt(tx)

    return BlockchainEvidence(
        evidence_hash=evidence_hash,
        ipfs_cid=ipfs_cid,
        evidence_type=evidence_type,
        registered_by=str(w3.eth.default_account),  # ✅ always string
        tx_hash=receipt.transactionHash.hex(),
        timestamp=int(datetime.utcnow().timestamp()),
    )

# -----------------------
# Fetch Evidence (SAFE)
# -----------------------
def get_evidence_from_chain(
    evidence_hash: str,
) -> BlockchainEvidence | None:
    """
    Returns:
        - BlockchainEvidence → if found on chain
        - None → if NOT found (valid forensic outcome)
    """
    try:
        e = contract.functions.getEvidence(
            _hash_evidence(evidence_hash)
        ).call()

        # Solidity return order:
        # (bytes32, string, string, address, uint256)

        return BlockchainEvidence(
            evidence_hash=evidence_hash,
            ipfs_cid=e[1],
            evidence_type=e[2],
            registered_by=str(e[3]),   # ✅ address → string
            tx_hash="READ_ONLY",
            timestamp=int(e[4]),
        )

    except (ContractLogicError, Web3RPCError):
        # ✅ NOT an error — evidence simply does not exist
        return None
