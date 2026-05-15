// SPDX-License-Identifier: MIT
pragma solidity ^0.8.19;

contract EvidenceRegistry {

    address public legalAuthority;
    address public forensicAnalyst;

    modifier onlyLegalAuthority() {
        require(msg.sender == legalAuthority, "Not Legal Authority");
        _;
    }

    modifier onlyForensicAnalyst() {
        require(msg.sender == forensicAnalyst, "Not Forensic Analyst");
        _;
    }

    modifier onlyAuthorizedReader() {
        require(
            msg.sender == forensicAnalyst || msg.sender == legalAuthority,
            "Unauthorized reader"
        );
        _;
    }

    struct Evidence {
        bytes32 evidenceHash;
        string ipfsCID;
        string evidenceType;
        address registeredBy;
        uint256 timestamp;
    }

    mapping(bytes32 => Evidence) private evidenceLedger;

    event EvidenceRegistered(
        bytes32 indexed evidenceHash,
        string ipfsCID,
        string evidenceType,
        address indexed registeredBy,
        uint256 timestamp
    );

    constructor(address _legalAuthority, address _forensicAnalyst) {
        legalAuthority = _legalAuthority;
        forensicAnalyst = _forensicAnalyst;
    }

    function registerEvidence(
        bytes32 _evidenceHash,
        string calldata _ipfsCID,
        string calldata _evidenceType
    )
        external
        onlyForensicAnalyst
    {
        require(
            evidenceLedger[_evidenceHash].timestamp == 0,
            "Evidence already exists"
        );

        evidenceLedger[_evidenceHash] = Evidence(
            _evidenceHash,
            _ipfsCID,
            _evidenceType,
            msg.sender,
            block.timestamp
        );

        emit EvidenceRegistered(
            _evidenceHash,
            _ipfsCID,
            _evidenceType,
            msg.sender,
            block.timestamp
        );
    }

    function getEvidence(bytes32 _evidenceHash)
        external
        view
        onlyAuthorizedReader
        returns (
            bytes32,
            string memory,
            string memory,
            address,
            uint256
        )
    {
        Evidence memory e = evidenceLedger[_evidenceHash];
        require(e.timestamp != 0, "Evidence not found");

        return (
            e.evidenceHash,
            e.ipfsCID,
            e.evidenceType,
            e.registeredBy,
            e.timestamp
        );
    }
}
