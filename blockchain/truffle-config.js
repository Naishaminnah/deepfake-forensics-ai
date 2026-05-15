/**
 * @title Truffle Configuration
 * @notice Configured for Ganache local network and Solidity 0.8.20
 */

const path = require("path");

module.exports = {
  // Where Truffle should store compiled contract artifacts
  contracts_build_directory: path.join(__dirname, "build/contracts"),

  networks: {
    development: {
      host: "127.0.0.1",      // Ganache default host
      port: 7545,             // Ganache default port
      network_id: "*",        // Match any network id
      gas: 8000000,           // Gas limit
      gasPrice: 20000000000,  // 20 gwei
    },
  },

  // Compiler settings
  compilers: {
    solc: {
      version: "0.8.19",        // Solidity version
      settings: {
        optimizer: {
          enabled: true,
          runs: 200,
        },
      },
    },
  },

  // Mocha testing framework settings (optional)
  mocha: {
    timeout: 100000,
  },
};
