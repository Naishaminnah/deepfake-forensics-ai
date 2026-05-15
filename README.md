# DeepFake Forensics AI

A forensic-grade deepfake detection and tamper-proof evidence management platform. This system detects AI-generated fakes across image, video, and audio modalities, and anchors forensic evidence immutably on the Ethereum blockchain via smart contracts — making it suitable for legal and law-enforcement use cases.

Built independently as a final-year BSc Computer Science project.

---

## What This System Does

Modern deepfakes pose a serious threat to the integrity of digital evidence in legal proceedings. This platform addresses that problem end-to-end:

1. **Detects** deepfakes across image, video, and audio using multiple trained neural networks
2. **Identifies** which GAN architecture generated a fake image (GAN fingerprinting)
3. **Reconstructs** the latent space of a fake image to trace its generative origin
4. **Anchors** evidence hashes immutably on Ethereum so tampering is cryptographically detectable
5. **Stores** evidence files on IPFS (via Pinata) for decentralised, tamper-evident storage
6. **Enforces** role-based access — only forensic analysts can register evidence; only legal authorities can verify it

---

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    React Frontend                        │
│         (role-aware UI for analysts & authorities)       │
└───────────────────────┬─────────────────────────────────┘
                        │ HTTP / REST
┌───────────────────────▼─────────────────────────────────┐
│               FastAPI Backend (Python)                   │
│  ┌──────────────┐  ┌──────────────┐  ┌───────────────┐  │
│  │  AI Models   │  │  Auth / RBAC │  │ Evidence Mgmt │  │
│  │  (inference) │  │  JWT + roles │  │  (ledger DB)  │  │
│  └──────────────┘  └──────────────┘  └───────────────┘  │
└──────┬───────────────────────────────────────┬──────────┘
       │                                       │
┌──────▼──────┐                     ┌──────────▼──────────┐
│ PostgreSQL  │                     │  Ethereum (Ganache)  │
│  (ledger)   │                     │  EvidenceRegistry   │
└─────────────┘                     │  Solidity contract  │
                                    └──────────┬──────────┘
                                               │
                                    ┌──────────▼──────────┐
                                    │   IPFS via Pinata    │
                                    │ (decentralised file  │
                                    │      storage)        │
                                    └─────────────────────┘
```

---

## AI Models

All models were trained from scratch on the datasets listed below.

| Modality | Model | Purpose |
|---|---|---|
| Image | EfficientNet-B4 / VGG16 | Frame-level deepfake detection |
| Video | Temporal CNN + LSTM | Sequence-level fake detection across frames |
| Audio | ECAPA-TDNN | Audio deepfake / voice clone detection |
| GAN fingerprinting | Custom CNN classifier | Identifies *which* GAN generated a fake (StyleGAN, BigGAN, etc.) |
| GAN inversion | BigGAN + StyleGAN2 latent projector | Reconstructs the latent vector of a fake to trace its generative origin |

---

## Datasets Used

- **FaceForensics++** — Deepfakes, Face2Face, FaceSwap, FaceShifter, NeuralTextures (c23 compression, video)
- **DeepFakeDetection** — Google/JigSaw dataset
- **Celeb-DF v2** — High-quality celebrity deepfake videos
- Custom GAN-generated image dataset for fingerprinting

---

## Blockchain Evidence Flow

```
Forensic Analyst uploads evidence file
        │
        ▼
SHA-256 hash computed from raw bytes
        │
        ▼
File uploaded to IPFS → returns CID
        │
        ▼
EvidenceRegistry.registerEvidence(hash, CID, type)
  called on Ethereum via Web3.py
        │
        ▼
Smart contract stores: hash, CID, type,
  analyst address, block timestamp
        │
        ▼
TX hash + metadata stored in PostgreSQL ledger
        │
        ▼
Legal Authority calls verifyEvidence(hash)
  → immutably marks evidence as court-verified
```

**Duplicate protection:** The smart contract reverts with `"Evidence already exists"` if the same hash is re-submitted. The backend also checks the local ledger before touching the chain.

---

## Smart Contract

`blockchain/contracts/EvidenceRegistry.sol`

- Written in Solidity, deployed via Truffle to local Ganache
- Two privileged roles: `legalAuthority` and `forensicAnalyst`
- Functions: `registerEvidence`, `verifyEvidence`, `getEvidence`
- Events emitted on registration and verification for auditability
- Access-controlled: only the forensic analyst can register; only the legal authority can verify; both can read

---

## Tech Stack

**AI / ML**
- Python 3.10+, PyTorch, torchvision
- ECAPA-TDNN (audio), EfficientNet-B4 (image/video), StyleGAN2, BigGAN

**Backend**
- FastAPI, SQLAlchemy, PostgreSQL
- Web3.py (Ethereum interaction)
- Pinata SDK (IPFS pinning)
- JWT authentication, role-based access control (RBAC)

**Blockchain**
- Solidity (smart contract)
- Truffle (compile, migrate, test)
- Ganache (local Ethereum testnet)
- IPFS via Pinata

**Frontend**
- React, Axios

---

## Project Structure

```
deepfake_forensics_ai/
├── backend/
│   ├── main.py                  # FastAPI app entry point
│   ├── config.py                # Device, paths, env config
│   ├── database.py              # SQLAlchemy + PostgreSQL setup
│   ├── core/
│   │   └── blockchain_config.py # Web3 + Ganache connection
│   ├── models/                  # AI model definitions + inference
│   │   ├── audio_detector.py    # ECAPA-TDNN inference
│   │   ├── audio_model.py       # ECAPA-TDNN architecture
│   │   ├── ethereum_service.py  # Blockchain register/verify/get
│   │   ├── gan_fingerprinter_infer.py
│   │   ├── biggan_loader.py
│   │   ├── latent_projector.py  # GAN inversion (latent space)
│   │   └── ...
│   ├── routes/                  # FastAPI routers
│   │   ├── image_detect.py
│   │   ├── video_detect.py
│   │   ├── audio_detect.py
│   │   ├── gan_detect.py
│   │   ├── gan_reconstruct.py
│   │   ├── forensic_upload.py   # Upload + blockchain anchor
│   │   ├── court_verification.py
│   │   ├── auth.py
│   │   └── ...
│   └── utils/
│       ├── rbac.py              # Role-based access control
│       ├── current_user.py      # JWT decoding
│       ├── hash_utils.py        # SHA-256 helpers
│       └── evidence_logger.py   # Ledger write utility
├── blockchain/
│   ├── contracts/
│   │   └── EvidenceRegistry.sol # Solidity smart contract
│   ├── migrations/              # Truffle deployment scripts
│   └── test/                    # Solidity unit tests
├── frontend/                    # React app
├── training/                    # Model training scripts
├── data/                        # FaceForensics++ dataset (not tracked)
├── checkpoints/                 # Saved model weights (not tracked)
├── .env.example                 # Environment variable template
├── .gitignore
└── requirements.txt
```

---

## How to Run Locally

### Prerequisites
- Python 3.10+
- Node.js 18+ and npm
- PostgreSQL (running locally)
- Ganache (GUI or CLI)
- Truffle (`npm install -g truffle`)

### 1. Clone and install

```bash
git clone https://github.com/yourusername/deepfake-forensics-ai.git
cd deepfake-forensics-ai
python -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Configure environment

```bash
cp .env.example .env
# Edit .env — fill in DATABASE_URL, Ganache keys, Pinata JWT
```

### 3. Deploy the smart contract

```bash
# Start Ganache on port 7545 first, then:
cd blockchain
truffle migrate --reset
# Copy the deployed contract address into your .env CONTRACT_ADDRESS
```

### 4. Start the backend

```bash
cd ..
uvicorn backend.main:app --reload
# API docs available at http://localhost:8000/docs
```

### 5. Start the frontend

```bash
cd frontend
npm install
npm start
# Opens at http://localhost:3000
```

---

## API Endpoints (selected)

| Method | Endpoint | Description |
|---|---|---|
| POST | `/detect/image` | Detect deepfake in image |
| POST | `/detect/video` | Detect deepfake in video |
| POST | `/detect/audio` | Detect audio deepfake |
| POST | `/detect/gan` | GAN fingerprint identification |
| POST | `/gan/reconstruct` | GAN latent space reconstruction |
| POST | `/forensics/upload-and-register` | Upload + anchor to blockchain |
| GET | `/evidence/anchor/by-hash/{hash}` | Query blockchain evidence record |
| POST | `/auth/login` | JWT login |

Full interactive docs: `http://localhost:8000/docs`

---

## Roles & Access Control

| Role | Can Do |
|---|---|
| `FORENSIC_ANALYST` | Run detection, upload and register evidence on-chain |
| `LEGAL_AUTHORITY` | Verify evidence on-chain, view all case records |
| `ADMIN` | User management, full ledger access |

---

## Key Design Decisions

**Why blockchain for evidence?** SHA-256 hashes stored on-chain are cryptographically immutable. Any post-upload tampering with a file changes its hash and breaks the chain record — detectable by anyone with the original transaction hash.

**Why IPFS?** Centralised file storage can be deleted or modified. IPFS content-addresses files by their hash, making silent modification impossible.

**Why multi-modal detection?** Real-world deepfakes are increasingly combined (fake face + cloned voice + synthetic video). A single-modal detector is easily bypassed by faking the other modality.

**Why GAN inversion?** Detection alone tells you *that* something is fake. Latent-space reconstruction can suggest *how* it was generated, which is useful in court for establishing the sophistication of the forgery.

---

## Limitations & Future Work

- Currently runs on a local Ganache testnet — production deployment would require migration to a public Ethereum testnet (Sepolia) or a permissioned chain
- Model weights are excluded from this repo due to size — see training scripts to reproduce
- Audio detection was trained on a limited dataset and may underperform on certain voice cloning techniques
- A full benchmarking paper with precision/recall/AUC tables across all five FaceForensics++ manipulation types is in preparation

---

## Author

**NAISHA MINNAH**
BSc Computer Science — Calicut University, India, 2025
- GitHub: [@Naishaminnah](https://github.com/Naishaminnah)
- LinkedIn: [linkedin.com/in/yourprofile](https://linkedin.com/in/yourprofile)

---

## License

MIT License — see `LICENSE` for details.
