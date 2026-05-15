import os
from dotenv import load_dotenv
from web3 import Web3
from eth_account import Account

# -----------------------
# Load .env from project root
# -----------------------
ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
ENV_PATH = os.path.join(ROOT_DIR, ".env")
load_dotenv(ENV_PATH)

# -----------------------
# Config values
# -----------------------
GANACHE_URL = os.getenv("GANACHE_URL")
CHAIN_ID = int(os.getenv("CHAIN_ID"))
CONTRACT_ADDRESS = Web3.to_checksum_address(os.getenv("CONTRACT_ADDRESS"))

LEGAL_AUTHORITY_PRIVATE_KEY = os.getenv("LEGAL_AUTHORITY_PRIVATE_KEY")
FORENSIC_ANALYST_PRIVATE_KEY = os.getenv("FORENSIC_ANALYST_PRIVATE_KEY")

if not GANACHE_URL:
    raise RuntimeError("❌ GANACHE_URL missing")
if not CONTRACT_ADDRESS:
    raise RuntimeError("❌ CONTRACT_ADDRESS missing")

# -----------------------
# Web3
# -----------------------
w3 = Web3(Web3.HTTPProvider(GANACHE_URL))
if not w3.is_connected():
    raise RuntimeError("❌ Ganache not running")

# -----------------------
# Accounts
# -----------------------
legal_authority = Account.from_key(LEGAL_AUTHORITY_PRIVATE_KEY)
forensic_analyst = Account.from_key(FORENSIC_ANALYST_PRIVATE_KEY)

# ✅ EXPORT ADDRESSES (THIS WAS MISSING)
LEGAL_AUTHORITY_ADDRESS = legal_authority.address
FORENSIC_ANALYST_ADDRESS = forensic_analyst.address

print("[OK] ENV LOADED")
print("CHAIN_ID:", CHAIN_ID)
print("LEGAL AUTHORITY:", LEGAL_AUTHORITY_ADDRESS)
print("FORENSIC ANALYST:", FORENSIC_ANALYST_ADDRESS)
