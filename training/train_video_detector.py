"""
training/train_video_detector.py

Train a video-level temporal deepfake detector using pre-extracted frame embeddings.

Usage:
    python -m training.train_video_detector

Expect folder layout:
    backend/features/
        video_0001/
            frames.npy       # shape (T, E)
            video_mean.npy   # (E,) optional
            meta.npy         # dict with 'label' and 'num_frames'

Outputs:
    - checkpoints/video_temporal_best.pth
"""

import os
import math
import random
import numpy as np
from pathlib import Path
from tqdm import tqdm

import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import Dataset, DataLoader, random_split

from sklearn.metrics import roc_auc_score, accuracy_score

# adjust import path if needed: uses your backend config
from backend.config import DEVICE, MODEL_DIR

# -------------------------
# Config / Hyperparameters
# -------------------------
class CFG:
    feature_root = r"D:\deepfake_forensics_ai\backend\features"  # where per-video folders exist
    temporal_model = "transformer"            # "lstm" or "transformer"
    seq_len = 32                       # frames per video sequence (sample/pad to this)
    input_dim = 1792                   # embedding dim produced by frame model
    hidden_dim = 512
    lstm_layers = 2
    transformer_heads = 8
    transformer_layers = 3

    batch_size = 1                     # safe for GPU memory (you asked for 1 earlier)
    epochs = 20
    lr = 1e-4
    weight_decay = 1e-4
    device = DEVICE
    num_workers = 4
    checkpoint_dir = "checkpoints"
    patience = 4                       # early stopping patience (on val AUC)
    seed = 42

# set seeds
random.seed(CFG.seed)
np.random.seed(CFG.seed)
torch.manual_seed(CFG.seed)
if torch.cuda.is_available():
    torch.cuda.manual_seed_all(CFG.seed)

# -------------------------
# Dataset
# -------------------------
def sample_seq(features: np.ndarray, seq_len: int):
    """
    Given features shape (T, E), sample or pad to (seq_len, E).
    Strategy:
      - If T >= seq_len: sample seq_len indices uniformly (preserve order).
      - If T < seq_len: pad by repeating last frame.
    """
    T = features.shape[0]
    if T == 0:
        return np.zeros((seq_len, features.shape[1]), dtype=features.dtype)
    if T >= seq_len:
        # select seq_len evenly spaced indices and keep temporal order
        indices = np.linspace(0, T - 1, seq_len, dtype=int)
        return features[indices]
    else:
        # pad by repeating last frame
        pad_count = seq_len - T
        pad = np.repeat(features[-1:, :], pad_count, axis=0)
        return np.concatenate([features, pad], axis=0)

class VideoFeatureDataset(Dataset):
    """
    Loads per-video embeddings saved by extract_frame_features.py
    Each sample returns (features_tensor: (seq_len, E), label: float)
    """
    def __init__(self, feature_root: str, seq_len: int = CFG.seq_len, subset: str = "all"):
        """
        subset: 'all', 'train', 'val' or 'test' - this function does not implement
                splitting by name; splitting is done externally via random_split.
        """
        self.root = Path(feature_root)
        self.seq_len = seq_len
        self.samples = []

        if not self.root.exists():
            raise FileNotFoundError(f"Feature root not found: {self.root}")

        # ✅ Updated logic to support directly numbered folders (00000, 00001, ...)
        for video_folder in self.root.iterdir():
            if not video_folder.is_dir():
                continue
            frames_path = video_folder / "frames.npy"
            meta_path = video_folder / "meta.npy"
            if frames_path.exists() and meta_path.exists():
                try:
                    meta = np.load(meta_path, allow_pickle=True).item()
                    label = float(meta.get("label", 0.0))  # try reading label from meta
                except Exception:
                    label = 0.0  # default label if missing
                self.samples.append({
                    "frames": str(frames_path),
                    "label": label
                })

        if len(self.samples) == 0:
            raise RuntimeError(f"No feature samples found under {feature_root}")

        # shuffle for randomness
        random.shuffle(self.samples)

    def __len__(self):
        return len(self.samples)

    def __getitem__(self, idx):
        entry = self.samples[idx]
        frames = np.load(entry["frames"])     # (T, E)
        frames = sample_seq(frames, self.seq_len)  # (seq_len, E)
        features = torch.tensor(frames, dtype=torch.float32)
        label = torch.tensor(entry["label"], dtype=torch.float32)
        return features, label


# -------------------------
# Models: LSTM and Transformer
# -------------------------
class VideoLSTM(nn.Module):
    def __init__(self,
                 input_dim=CFG.input_dim,
                 hidden_dim=CFG.hidden_dim,
                 num_layers=CFG.lstm_layers,
                 bidirectional=True,
                 dropout=0.3):
        super().__init__()
        self.bidirectional = bidirectional
        self.lstm = nn.LSTM(input_dim, hidden_dim, num_layers=num_layers,
                            batch_first=True, bidirectional=bidirectional, dropout=dropout)
        out_dim = hidden_dim * 2 if bidirectional else hidden_dim
        self.head = nn.Sequential(
            nn.Linear(out_dim, 256),
            nn.LayerNorm(256),
            nn.GELU(),
            nn.Dropout(0.4),
            nn.Linear(256, 1)   # logits
        )

    def forward(self, x):
        # x: (B, T, E)
        B = x.size(0)
        _, (hn, _) = self.lstm(x)  # hn shape: (num_layers * num_directions, B, hidden_dim)
        if self.bidirectional:
            # take last forward and last backward
            last_forward = hn[-2]   # (B, hidden_dim)
            last_backward = hn[-1]  # (B, hidden_dim)
            h = torch.cat([last_forward, last_backward], dim=1)  # (B, 2*hidden_dim)
        else:
            h = hn[-1]
        logits = self.head(h).squeeze(1)  # (B,)
        return logits


class VideoTransformer(nn.Module):
    def __init__(self,
                 input_dim=CFG.input_dim,
                 num_layers=CFG.transformer_layers,
                 nhead=CFG.transformer_heads,
                 dim_feedforward=None,
                 dropout=0.2,
                 max_len=CFG.seq_len):
        super().__init__()
        dim_feedforward = dim_feedforward or (input_dim * 4)
        self.input_proj = nn.Linear(input_dim, input_dim)  # identity proj (keeps shape)
        encoder_layer = nn.TransformerEncoderLayer(d_model=input_dim, nhead=nhead,
                                                   dim_feedforward=dim_feedforward,
                                                   dropout=dropout, activation='gelu', batch_first=True)
        self.transformer = nn.TransformerEncoder(encoder_layer, num_layers=num_layers)
        # learnable cls token
        self.cls_token = nn.Parameter(torch.randn(1, 1, input_dim))
        self.pos_emb = nn.Parameter(torch.randn(1, max_len + 1, input_dim))
        self.head = nn.Sequential(
            nn.LayerNorm(input_dim),
            nn.Linear(input_dim, 256),
            nn.GELU(),
            nn.Dropout(0.3),
            nn.Linear(256, 1)
        )

    def forward(self, x):
        # x: (B, T, E)
        B, T, E = x.shape
        x = self.input_proj(x)  # (B, T, E)
        cls = self.cls_token.expand(B, -1, -1)  # (B,1,E)
        x = torch.cat([cls, x], dim=1)          # (B, T+1, E)
        pos = self.pos_emb[:, : T + 1, :].to(x.device)
        x = x + pos
        x = self.transformer(x)                 # (B, T+1, E)
        cls_out = x[:, 0, :]                    # (B, E)
        logits = self.head(cls_out).squeeze(1)
        return logits


# -------------------------
# Training / Validation Utils
# -------------------------
def evaluate_model(model, loader, device):
    model.eval()
    y_true, y_score = [], []
    with torch.no_grad():
        for feats, labels in loader:
            feats = feats.to(device)
            labels = labels.to(device)
            logits = model(feats)
            probs = torch.sigmoid(logits)
            y_score.extend(probs.cpu().numpy().tolist())
            y_true.extend(labels.cpu().numpy().tolist())
    # metrics
    y_pred = [1 if p >= 0.5 else 0 for p in y_score]
    auc = roc_auc_score(y_true, y_score) if len(set(y_true)) > 1 else 0.5
    acc = accuracy_score(y_true, y_pred)
    return auc, acc


def train(feature_root=CFG.feature_root,
          temporal_model=CFG.temporal_model,
          seq_len=CFG.seq_len,
          input_dim=CFG.input_dim,
          batch_size=CFG.batch_size,
          epochs=CFG.epochs,
          lr=CFG.lr):
    os.makedirs(CFG.checkpoint_dir, exist_ok=True)
    device = CFG.device

    # dataset
    dataset = VideoFeatureDataset(feature_root, seq_len=seq_len)
    n = len(dataset)
    n_val = max( int(0.15 * n),  int(100) )   # at least 100 val if available
    n_train = n - n_val
    train_set, val_set = random_split(dataset, [n_train, n_val])

    train_loader = DataLoader(train_set, batch_size=batch_size, shuffle=True, num_workers=CFG.num_workers, pin_memory=True)
    val_loader = DataLoader(val_set, batch_size=batch_size, shuffle=False, num_workers=CFG.num_workers, pin_memory=True)

    # model
    if temporal_model.lower() == "lstm":
        model = VideoLSTM(input_dim=input_dim, hidden_dim=CFG.hidden_dim, num_layers=CFG.lstm_layers).to(device)
    else:
        model = VideoTransformer(input_dim=input_dim, num_layers=CFG.transformer_layers, nhead=CFG.transformer_heads, max_len=seq_len).to(device)

    criterion = nn.BCEWithLogitsLoss()
    optimizer = optim.AdamW(model.parameters(), lr=lr, weight_decay=CFG.weight_decay)
    scheduler = optim.lr_scheduler.ReduceLROnPlateau(optimizer, mode='max', factor=0.5, patience=2, verbose=True)

    scaler = torch.cuda.amp.GradScaler() if torch.cuda.is_available() else None

    best_val_auc = -1.0
    epochs_no_improve = 0

    for epoch in range(1, epochs + 1):
        model.train()
        running_loss = 0.0

        pbar = tqdm(train_loader, desc=f"Epoch {epoch}/{epochs} [Train]", leave=False)
        for feats, labels in pbar:
            feats = feats.to(device)    # (B, T, E)
            labels = labels.to(device)

            optimizer.zero_grad()
            with torch.autocast("cuda" if torch.cuda.is_available() else "cpu"):
                logits = model(feats)   # (B,)
                loss = criterion(logits, labels)

            if scaler:
                scaler.scale(loss).backward()
                scaler.step(optimizer)
                scaler.update()
            else:
                loss.backward()
                optimizer.step()

            running_loss += loss.item()
            pbar.set_postfix({"loss": f"{running_loss / (pbar.n + 1):.4f}"})

        avg_train_loss = running_loss / max(1, len(train_loader))

        # validate
        val_auc, val_acc = evaluate_model(model, val_loader, device)
        print(f"\nEpoch {epoch}: train_loss={avg_train_loss:.4f}, val_auc={val_auc:.4f}, val_acc={val_acc:.4f}")

        # scheduler step
        scheduler.step(val_auc)

        # save best
        if val_auc > best_val_auc:
            best_val_auc = val_auc
            epochs_no_improve = 0
            save_path = os.path.join(CFG.checkpoint_dir, "video_temporal_best_2.pth")
            torch.save({
                     "model_state_dict": model.state_dict(),
                     "cfg": {k: v for k, v in vars(CFG).items() if not k.startswith('__')}
                       }, save_path)

            print(f"✅ Saved best model (AUC={best_val_auc:.4f}) -> {save_path}")
        else:
            epochs_no_improve += 1

        # early stopping
        if epochs_no_improve >= CFG.patience:
            print(f"Stopping early after {epoch} epochs (no improvement in {CFG.patience} epochs).")
            break

    print(f"\nTraining finished. Best val AUC: {best_val_auc:.4f}")
    return model


# -------------------------
# Entry point
# -------------------------
if __name__ == "__main__":
    os.makedirs(CFG.checkpoint_dir, exist_ok=True)
    train(feature_root=CFG.feature_root,
          temporal_model=CFG.temporal_model,
          seq_len=CFG.seq_len,
          input_dim=CFG.input_dim,
          batch_size=CFG.batch_size,
          epochs=CFG.epochs,
          lr=CFG.lr)
