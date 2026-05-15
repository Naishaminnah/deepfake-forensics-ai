# training/train_image_detector.py
"""
Advanced training script for image deepfake detection using EfficientNet-B4.
- Expects extracted frames under data/frames/{real,fake}/
- Performs an internal train/val split (stratified by class)
- Uses balanced WeightedRandomSampler
- Uses mixed precision (AMP) for speed and memory
- Computes AUC, F1, Precision, Recall on validation
- Saves best model by val AUC
"""

import os
import random
from pathlib import Path
import argparse
import numpy as np
from sklearn.metrics import roc_auc_score, f1_score, precision_score, recall_score, accuracy_score
from collections import Counter

import torch
import torch.nn as nn
from torch.utils.data import Dataset, DataLoader, WeightedRandomSampler
from torchvision import transforms
from PIL import Image
from tqdm import tqdm

from backend.models.image_detector import ImageDeepfakeDetector
from backend.config import DEVICE, DATA_DIR, MODEL_DIR

# ---------------------------
# Dataset that reads frames/real & frames/fake
# ---------------------------
class FramesDataset(Dataset):
    def __init__(self, root: Path, files: list, transform=None):
        self.root = Path(root)
        self.files = files
        self.transform = transform

    def __len__(self):
        return len(self.files)

    def __getitem__(self, idx):
        p, label = self.files[idx]
        img = Image.open(p).convert("RGB")
        if self.transform:
            img = self.transform(img)
        return img, label

# ---------------------------
# Helpers
# ---------------------------
def list_frame_files(frames_root: Path):
    real = sorted((frames_root / "real").glob("**/*.jpg"))
    fake = sorted((frames_root / "fake").glob("**/*.jpg"))
    real_pairs = [(p, 0) for p in real]
    fake_pairs = [(p, 1) for p in fake]
    return real_pairs + fake_pairs

def train_val_split(pairs, val_ratio=0.2, seed=42):
    random.seed(seed)
    # stratified split by label
    pairs = list(pairs)
    by_label = {0: [], 1: []}
    for p, l in pairs:
        by_label[l].append((p,l))
    train, val = [], []
    for l, items in by_label.items():
        n_val = max(1, int(len(items) * val_ratio))
        random.shuffle(items)
        val.extend(items[:n_val])
        train.extend(items[n_val:])
    random.shuffle(train)
    random.shuffle(val)
    return train, val

# ---------------------------
# Transforms
# ---------------------------
train_transform = transforms.Compose([
    transforms.Resize((380, 380)),           # EfficientNet-B4 default
    transforms.RandomHorizontalFlip(p=0.5),
    transforms.RandomRotation(8),
    transforms.ColorJitter(0.2,0.2,0.2,0.05),
    transforms.RandomResizedCrop(380, scale=(0.85,1.0), ratio=(0.9,1.1)),
    transforms.ToTensor(),
    transforms.Normalize(mean=[0.485,0.456,0.406], std=[0.229,0.224,0.225]),
])

val_transform = transforms.Compose([
    transforms.Resize((380,380)),
    transforms.ToTensor(),
    transforms.Normalize(mean=[0.485,0.456,0.406], std=[0.229,0.224,0.225]),
])

# ---------------------------
# Training loop
# ---------------------------
def train(args):
    frames_root = Path(args.data_dir)  # expected: data/frames
    # Use pre-split folders instead of random split
    train_pairs = list_frame_files(Path(args.data_dir) / "train")
    val_pairs   = list_frame_files(Path(args.data_dir) / "val")

    print(f"Train frames: {len(train_pairs)}, Val frames: {len(val_pairs)}")

    # dataset + sampler
    train_ds = FramesDataset(frames_root, train_pairs, transform=train_transform)
    val_ds = FramesDataset(frames_root, val_pairs, transform=val_transform)

    # compute class weights for WeightedRandomSampler
    counts = Counter([label for _, label in train_pairs])
    class_counts = [counts.get(0,0), counts.get(1,0)]
    print("Train class counts:", class_counts)
    weights_per_class = [0.0, 0.0]
    if class_counts[0] > 0 and class_counts[1] > 0:
        weights_per_class = [1.0 / class_counts[i] for i in range(2)]
    samples_weight = [weights_per_class[label] for _, label in train_pairs]
    sampler = WeightedRandomSampler(weights=samples_weight, num_samples=len(samples_weight), replacement=True)

    train_loader = DataLoader(train_ds, batch_size=args.batch_size, sampler=sampler, num_workers=args.workers, pin_memory=True)
    val_loader = DataLoader(val_ds, batch_size=args.batch_size, shuffle=False, num_workers=args.workers, pin_memory=True)

    # model, criterion, optimizer, scheduler
    model = ImageDeepfakeDetector(pretrained=True).to(DEVICE)
    criterion = nn.CrossEntropyLoss(label_smoothing=args.label_smoothing)
    optimizer = torch.optim.AdamW(model.parameters(), lr=args.lr, weight_decay=args.weight_decay)
    scheduler = torch.optim.lr_scheduler.ReduceLROnPlateau(optimizer, mode='min', factor=0.5, patience=3)

    scaler = torch.cuda.amp.GradScaler(enabled=(args.amp and DEVICE.startswith("cuda")))

    best_auc = 0.0
    best_epoch = -1

    for epoch in range(1, args.epochs + 1):
        model.train()
        running_loss = 0.0
        preds_all = []
        labels_all = []
        pbar = tqdm(train_loader, desc=f"Train Epoch {epoch}/{args.epochs}", leave=False)
        for imgs, labels in pbar:
            imgs = imgs.to(DEVICE, non_blocking=True)
            labels = labels.to(DEVICE, non_blocking=True)

            optimizer.zero_grad()
            with torch.cuda.amp.autocast(enabled=(args.amp and DEVICE.startswith("cuda"))):
                logits = model(imgs)
                loss = criterion(logits, labels)

            scaler.scale(loss).backward()
            scaler.step(optimizer)
            scaler.update()

            running_loss += loss.item() * imgs.size(0)
            probs = torch.softmax(logits, dim=1)[:,1].detach().cpu().numpy()
            preds_all.extend(probs.tolist())
            labels_all.extend(labels.detach().cpu().numpy().tolist())
            pbar.set_postfix({"loss": f"{loss.item():.4f}"})

        train_loss = running_loss / len(train_ds)
        train_auc = roc_auc_score(labels_all, preds_all) if len(set(labels_all)) > 1 else 0.5

        # validation
        model.eval()
        val_probs = []
        val_labels = []
        val_loss = 0.0
        with torch.no_grad():
            for imgs, labels in tqdm(val_loader, desc="Validation", leave=False):
                imgs = imgs.to(DEVICE, non_blocking=True)
                labels = labels.to(DEVICE, non_blocking=True)
                logits = model(imgs)
                loss = criterion(logits, labels)
                val_loss += loss.item() * imgs.size(0)
                probs = torch.softmax(logits, dim=1)[:,1].cpu().numpy()
                val_probs.extend(probs.tolist())
                val_labels.extend(labels.cpu().numpy().tolist())

        val_loss = val_loss / len(val_ds)
        val_auc = roc_auc_score(val_labels, val_probs) if len(set(val_labels)) > 1 else 0.5
        # threshold metrics
        val_preds_bin = [1 if p > 0.5 else 0 for p in val_probs]
        val_acc = accuracy_score(val_labels, val_preds_bin)
        val_f1 = f1_score(val_labels, val_preds_bin, zero_division=0)
        val_prec = precision_score(val_labels, val_preds_bin, zero_division=0)
        val_rec = recall_score(val_labels, val_preds_bin, zero_division=0)

        print(f"Epoch {epoch} | Train Loss {train_loss:.4f} AUC {train_auc:.4f} | Val Loss {val_loss:.4f} AUC {val_auc:.4f} Acc {val_acc:.4f} F1 {val_f1:.4f}")

        # scheduler step
        scheduler.step(val_loss)

        # save best by AUC
        if val_auc > best_auc:
            best_auc = val_auc
            best_epoch = epoch
            MODEL_DIR.mkdir(parents=True, exist_ok=True)
            save_name = f"image_detector_best_epoch{epoch}_auc{best_auc:.4f}.pth"
            torch.save(model.state_dict(), MODEL_DIR / save_name)
            print(f"✅ Saved best model: {save_name}")

    print(f"Training finished. Best epoch {best_epoch} with AUC {best_auc:.4f}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--data_dir", type=str, default=str(Path(DATA_DIR) / "frames"), help="frames root (must contain real/ and fake/)")
    parser.add_argument("--batch_size", type=int, default=8)
    parser.add_argument("--epochs", type=int, default=12)
    parser.add_argument("--lr", type=float, default=3e-4)
    parser.add_argument("--weight_decay", type=float, default=1e-4)
    parser.add_argument("--label_smoothing", type=float, default=0.05)
    parser.add_argument("--val_ratio", type=float, default=0.15)
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--amp", action="store_true", help="use mixed precision")
    args = parser.parse_args()
    train(args)
