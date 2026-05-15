import os
from dotenv import load_dotenv

# Load .env once
load_dotenv()

# Pinata JWT
PINATA_JWT = os.getenv("PINATA_JWT")

if not PINATA_JWT:
    raise RuntimeError("PINATA_JWT environment variable not set. Please update .env with your Pinata JWT.")
