import os
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader
from tqdm import tqdm

from training.real_fake_dataset import RealFakeDataset
from backend.models.gan_fingerprinter import GANFingerprinter
from training.gan_transforms import train_transform, test_transform

DATA_ROOT = "D:/deepfake_forensics_ai/gan_dataset"
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"


def train(batch=32):
    print("\n======================")
    print("🚀 Starting Real vs Fake Training")
    print("======================")
    print(f"DEVICE: {DEVICE}")
    print(f"DATA ROOT: {DATA_ROOT}")
    print("Loading datasets...")
    print("----------------------")

    # ----------------------------
    # LOAD DATASETS
    # ----------------------------
    train_ds = RealFakeDataset(DATA_ROOT, train_transform, split="train")
    val_ds   = RealFakeDataset(DATA_ROOT, test_transform, split="val")

    print(f"[INFO] Train samples: {len(train_ds)}")
    print(f"[INFO] Val samples:   {len(val_ds)}")
    print("Creating DataLoaders (this may take a moment)...")

    train_dl = DataLoader(train_ds, batch_size=batch, shuffle=True, num_workers=0)
    val_dl   = DataLoader(val_ds, batch_size=batch, num_workers=0)

    print("✔ DataLoaders created.")
    print("Initializing model...\n")

    # ----------------------------
    # MODEL + OPTIMIZER + SCHEDULER
    # ----------------------------
    model = GANFingerprinter(num_classes=2).to(DEVICE)

    opt = optim.AdamW(
        model.parameters(),
        lr=1e-4,
        weight_decay=1e-4     # ✅ L2 Regularization
    )

    scheduler = optim.lr_scheduler.CosineAnnealingLR(
        opt,
        T_max=30,             # total epochs
        eta_min=1e-6          # minimum LR
    )

    loss_fn = nn.CrossEntropyLoss()
    scaler = torch.cuda.amp.GradScaler()    # ✅ Mixed Precision

    print("Model initialized. Beginning training...\n")

    best = 0
    for epoch in range(30):
        print(f"\n========== Epoch {epoch+1}/30 ==========")

        model.train()
        correct = total = 0

        train_iter = tqdm(train_dl, desc=f"Training", ncols=90)

        for imgs, labels in train_iter:
            imgs, labels = imgs.to(DEVICE), labels.to(DEVICE)

            opt.zero_grad()

            # ----------------------------
            # AMP TRAINING STEP
            # ----------------------------
            with torch.cuda.amp.autocast():
                out = model(imgs)
                loss = loss_fn(out, labels)

            scaler.scale(loss).backward()
            scaler.step(opt)
            scaler.update()

            correct += (out.argmax(1) == labels).sum().item()
            total += labels.size(0)

            train_iter.set_postfix({
                "loss": f"{loss.item():.4f}",
                "acc": f"{correct/total:.3f}"
            })

        train_acc = correct / total

        # Step LR scheduler
        scheduler.step()

        # ----------------------------
        # VALIDATION LOOP
        # ----------------------------
        model.eval()
        v_correct = v_total = 0
        val_iter = tqdm(val_dl, desc=f"Validating", ncols=90)

        with torch.no_grad():
            for imgs, labels in val_iter:
                imgs, labels = imgs.to(DEVICE), labels.to(DEVICE)
                out = model(imgs)
                v_correct += (out.argmax(1) == labels).sum().item()
                v_total += labels.size(0)

                val_iter.set_postfix({
                    "acc": f"{v_correct/v_total:.3f}"
                })

        val_acc = v_correct / v_total

        print(f"\nEpoch {epoch+1} Summary:")
        print(f"   Train Acc: {train_acc:.4f}")
        print(f"   Val Acc:   {val_acc:.4f}")

        if val_acc > best:
            best = val_acc
            torch.save(model.state_dict(), "real_fake_detector.pth")
            print("✔ Saved new BEST model!\n")
        else:
            print("No improvement.\n")


if __name__ == "__main__":
    import multiprocessing
    multiprocessing.freeze_support()
    train()
