const EvidenceRegistry = artifacts.require("EvidenceRegistry");

contract("EvidenceRegistry", (accounts) => {
  const legalAuthority = accounts[0];
  const forensicAnalyst = accounts[1];
  const attacker = accounts[2];

  let registry;

  const evidenceHash = web3.utils.keccak256("sample-evidence");
  const ipfsCID = "QmTestCID123456";
  const evidenceType = "image";

  before(async () => {
    registry = await EvidenceRegistry.deployed();
  });

  /* ===========================
     DEPLOYMENT TEST
  =========================== */
  it("should assign correct roles on deployment", async () => {
    const la = await registry.legalAuthority();
    const fa = await registry.forensicAnalyst();

    assert.equal(la, legalAuthority, "Legal Authority incorrect");
    assert.equal(fa, forensicAnalyst, "Forensic Analyst incorrect");
  });

  /* ===========================
     REGISTER EVIDENCE
  =========================== */
  it("should allow forensic analyst to register evidence", async () => {
    await registry.registerEvidence(
      evidenceHash,
      ipfsCID,
      evidenceType,
      { from: forensicAnalyst }
    );

    const evidence = await registry.getEvidence(evidenceHash);

    assert.equal(evidence[0], evidenceHash);
    assert.equal(evidence[1], ipfsCID);
    assert.equal(evidence[2], evidenceType);
    assert.equal(evidence[4], false);
  });

  /* ===========================
     DUPLICATE PREVENTION
  =========================== */
  it("should reject duplicate evidence registration", async () => {
    try {
      await registry.registerEvidence(
        evidenceHash,
        ipfsCID,
        evidenceType,
        { from: forensicAnalyst }
      );
      assert.fail("Duplicate evidence allowed");
    } catch (err) {
      assert(
        err.message.includes("Evidence already exists"),
        "Expected duplicate prevention"
      );
    }
  });

  /* ===========================
     VERIFICATION
  =========================== */
  it("should allow legal authority to verify evidence", async () => {
    await registry.verifyEvidence(evidenceHash, {
      from: legalAuthority,
    });

    const evidence = await registry.getEvidence(evidenceHash);
    assert.equal(evidence[4], true, "Evidence not verified");
  });

  /* ===========================
     ACCESS CONTROL
  =========================== */
  it("should block unauthorized verification attempts", async () => {
    const fakeHash = web3.utils.keccak256("fake-evidence");

    try {
      await registry.verifyEvidence(fakeHash, { from: attacker });
      assert.fail("Unauthorized verification allowed");
    } catch (err) {
      assert(
        err.message.includes("Not Legal Authority"),
        "Unauthorized access blocked"
      );
    }
  });

  /* ===========================
     READ PROTECTION
  =========================== */
  it("should reject reading non-existent evidence", async () => {
    try {
      await registry.getEvidence(web3.utils.keccak256("ghost"));
      assert.fail("Non-existent evidence returned");
    } catch (err) {
      assert(
        err.message.includes("Evidence not found"),
        "Missing evidence rejected"
      );
    }
  });
});
