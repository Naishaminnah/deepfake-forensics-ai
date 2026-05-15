import os
from pathlib import Path
from dotenv import load_dotenv
import torch

# load .env if available
load_dotenv()

# project root (one level above this file)
ROOT = Path(__file__).resolve().parents[1]

# directories (read from env or use defaults)
DATA_DIR = Path(os.getenv("DATA_DIR", ROOT / "data"))
MODEL_DIR = Path(os.getenv("MODEL_DIR", ROOT / "backend/models"))

# device selection (auto)
DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")

# ensure model dir exists
MODEL_DIR.mkdir(parents=True, exist_ok=True)

print(f"[CONFIG] DEVICE: {DEVICE}")
print(f"[CONFIG] DATA_DIR: {DATA_DIR}")
print(f"[CONFIG] MODEL_DIR: {MODEL_DIR}")
