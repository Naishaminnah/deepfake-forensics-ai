from pydantic import BaseModel, Field


class BlockchainEvidence(BaseModel):
    """
    Canonical blockchain-backed forensic evidence record.
    """

    evidence_hash: str = Field(..., description="SHA-256 hash of original media")
    ipfs_cid: str = Field(..., description="IPFS CID")
    evidence_type: str = Field(..., description="image | video | audio")
    registered_by: str = Field(..., description="Ethereum address")
    tx_hash: str = Field(..., description="Transaction hash or READ_ONLY")
    timestamp: int = Field(..., description="Block timestamp (UTC)")
