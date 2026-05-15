import os
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader
from tqdm import tqdm

from training.gan_dataset import GANTypeDataset
from backend.models.gan_fingerprinter import GANFingerprinter
from training.gan_transforms import train_transform, test_transform

DATA_DIR = "D:/deepfake_forensics_ai/gan_dataset_sample"  # updated path
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"

def train(batch=32, max_epochs=40, early_stop_patience=5):
    # Initialize datasets
    train_ds = GANTypeDataset(DATA_DIR, train_transform, split="train")
    val_ds   = GANTypeDataset(DATA_DIR, test_transform,  split="val")

    # Show loaded samples count
    print(f"[INFO] Training samples loaded: {len(train_ds)}")
    print(f"[INFO] Validation samples loaded: {len(val_ds)}")
    print(f"[INFO] Classes: {train_ds.class_to_idx}")

    train_dl = DataLoader(train_ds, batch_size=batch, shuffle=True, num_workers=4)
    val_dl   = DataLoader(val_ds, batch_size=batch, num_workers=2)

    num_classes = len(train_ds.class_to_idx)
    model = GANFingerprinter(num_classes=num_classes).to(DEVICE)

    opt = optim.AdamW(model.parameters(), lr=1e-4, weight_decay=1e-4)
    scheduler = optim.lr_scheduler.CosineAnnealingLR(opt, T_max=max_epochs, eta_min=1e-6)
    loss_fn = nn.CrossEntropyLoss()

    best_acc = 0
    patience_counter = 0

    for epoch in range(max_epochs):
        model.train()
        correct = total = 0
        train_iter = tqdm(train_dl, desc=f"Epoch {epoch+1}/{max_epochs} [Train]", ncols=100)
        
        for imgs, labels in train_iter:
            # Skip corrupted images
            if imgs is None or labels is None:
                continue

            imgs, labels = imgs.to(DEVICE), labels.to(DEVICE)
            opt.zero_grad()
            out = model(imgs)
            loss = loss_fn(out, labels)
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)
            opt.step()

            correct += (out.argmax(1) == labels).sum().item()
            total += labels.size(0)
            train_iter.set_postfix({"loss": f"{loss.item():.4f}", "acc": f"{correct/total:.3f}"})

        train_acc = correct / total if total > 0 else 0.0

        # Validation
        model.eval()
        v_correct = v_total = 0
        val_iter = tqdm(val_dl, desc=f"Epoch {epoch+1}/{max_epochs} [Val]  ", ncols=100)
        with torch.no_grad():
            for imgs, labels in val_iter:
                if imgs is None or labels is None:
                    continue
                imgs, labels = imgs.to(DEVICE), labels.to(DEVICE)
                out = model(imgs)
                v_correct += (out.argmax(1) == labels).sum().item()
                v_total += labels.size(0)
                val_iter.set_postfix({"acc": f"{v_correct/v_total:.3f}"})

        val_acc = v_correct / v_total if v_total > 0 else 0.0
        print(f"\nEpoch {epoch+1} Summary: Train Acc={train_acc:.4f} | Val Acc={val_acc:.4f}")

        # Save best model
        if val_acc > best_acc:
            best_acc = val_acc
            torch.save(model.state_dict(), "gan_type_classifier.pth")
            print("✔ Saved BEST model!\n")
            patience_counter = 0
        else:
            patience_counter += 1
            print(f"No improvement ({patience_counter}/{early_stop_patience})\n")

        if patience_counter >= early_stop_patience:
            print(f"⚠ Early stopping triggered at epoch {epoch+1}")
            break

        scheduler.step()

if __name__ == "__main__":
    train()
