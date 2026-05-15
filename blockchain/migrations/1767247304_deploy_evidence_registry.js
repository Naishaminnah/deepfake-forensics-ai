const EvidenceRegistry = artifacts.require("EvidenceRegistry");

module.exports = async function (deployer, network, accounts) {
  // Use first two Ganache accounts for roles
  const legalAuthority = accounts[0];
  const forensicAnalyst = accounts[1];

  console.log("Deploying EvidenceRegistry with:");
  console.log("Legal Authority:", legalAuthority);
  console.log("Forensic Analyst:", forensicAnalyst);

  await deployer.deploy(
    EvidenceRegistry,
    legalAuthority,
    forensicAnalyst,
    { gas: 8000000 } // optional high gas
  );

  const instance = await EvidenceRegistry.deployed();
  console.log("EvidenceRegistry deployed at:", instance.address);
};
