import os
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader
from torchvision import transforms
from sklearn.metrics import roc_auc_score, accuracy_score
from tqdm import tqdm

from backend.models.frame_dataset import FrameDataset
from backend.models.frame_model import FrameDeepfakeModel

# -----------------------------
# Device
# -----------------------------
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"

# -----------------------------
# Configuration
# -----------------------------
class CFG:
    ffpp_root = "D:/deepfake_forensics_ai/data"               # FaceForensics++ C23 root
    celebdf_root = "D:/deepfake_forensics_ai/datasets/celeb_df_v2"  # Celeb-DF v2 root
    test_list_path = os.path.join(celebdf_root, "list_of_testing_videos.txt")
    batch_size = 16
    num_workers = 8
    lr = 1e-4
    epochs = 10
    output_dir = "checkpoints"
    num_classes = 1
    frame_interval = 10  # extract every Nth frame
    img_size = 380      # EfficientNet-B4 input size

# -----------------------------
# Data Transforms
# -----------------------------
def get_transforms(split="train"):
    if split == "train":
        return transforms.Compose([
            transforms.Resize((CFG.img_size, CFG.img_size)),
            transforms.RandomHorizontalFlip(),
            transforms.ColorJitter(brightness=0.2, contrast=0.2, saturation=0.2),
            transforms.ToTensor(),
            transforms.Normalize(mean=[0.485, 0.456, 0.406],
                                 std=[0.229, 0.224, 0.225]),
        ])
    else:
        return transforms.Compose([
            transforms.Resize((CFG.img_size, CFG.img_size)),
            transforms.ToTensor(),
            transforms.Normalize(mean=[0.485, 0.456, 0.406],
                                 std=[0.229, 0.224, 0.225]),
        ])

# -----------------------------
# Training / Validation Functions
# -----------------------------
def train_one_epoch(model, loader, optimizer, scaler, criterion):
    model.train()
    total_loss = 0
    all_preds, all_labels = [], []

    for imgs, labels in tqdm(loader, desc="Training", leave=False):
        imgs, labels = imgs.to(DEVICE), labels.float().to(DEVICE)
        optimizer.zero_grad()

        # AMP-safe autocast for current PyTorch
        with torch.amp.autocast(device_type="cuda"):
            preds = model(imgs)
            if preds.dim() > 1:
                preds = preds.squeeze(1)
            loss = criterion(preds, labels)

        scaler.scale(loss).backward()
        scaler.step(optimizer)
        scaler.update()

        total_loss += loss.item()
        all_preds += torch.sigmoid(preds).detach().cpu().tolist()
        all_labels += labels.detach().cpu().tolist()

    acc = accuracy_score([int(p > 0.5) for p in all_preds], all_labels)
    auc = roc_auc_score(all_labels, all_preds)
    return total_loss / len(loader), acc, auc


def validate(model, loader, criterion):
    model.eval()
    total_loss = 0
    all_preds, all_labels = [], []

    with torch.no_grad():
        for imgs, labels in tqdm(loader, desc="Validating", leave=False):
            imgs, labels = imgs.to(DEVICE), labels.float().to(DEVICE)
            with torch.amp.autocast(device_type="cuda"):
                preds = model(imgs)
                if preds.dim() > 1:
                    preds = preds.squeeze(1)
                loss = criterion(preds, labels)

            total_loss += loss.item()
            all_preds += torch.sigmoid(preds).detach().cpu().tolist()
            all_labels += labels.detach().cpu().tolist()

    acc = accuracy_score([int(p > 0.5) for p in all_preds], all_labels)
    auc = roc_auc_score(all_labels, all_preds)
    return total_loss / len(loader), acc, auc

# -----------------------------
# Main Training Loop
# -----------------------------
def main():
    os.makedirs(CFG.output_dir, exist_ok=True)

    # --- Dataset ---
    train_dataset = FrameDataset(
        ffpp_root=CFG.ffpp_root,
        celebdf_root=CFG.celebdf_root,
        test_list_path=CFG.test_list_path,
        split="train",
        frame_interval=CFG.frame_interval,
        transform=get_transforms("train")
    )

    val_dataset = FrameDataset(
        ffpp_root=CFG.ffpp_root,
        celebdf_root=CFG.celebdf_root,
        test_list_path=CFG.test_list_path,
        split="val",
        frame_interval=CFG.frame_interval,
        transform=get_transforms("val")
    )

    train_loader = DataLoader(train_dataset, batch_size=CFG.batch_size, shuffle=True,
                              num_workers=CFG.num_workers, pin_memory=True)
    val_loader = DataLoader(val_dataset, batch_size=CFG.batch_size, shuffle=False,
                            num_workers=CFG.num_workers, pin_memory=True)

    # --- Model ---
    model = FrameDeepfakeModel(pretrained=True).to(DEVICE)
    criterion = nn.BCEWithLogitsLoss()  # fixed for AMP-safe training
    optimizer = optim.AdamW(model.parameters(), lr=CFG.lr)
    scaler = torch.cuda.amp.GradScaler()  # warning-safe and works fine

    best_auc = 0
    for epoch in range(1, CFG.epochs + 1):
        print(f"\nEpoch {epoch}/{CFG.epochs}")
        train_loss, train_acc, train_auc = train_one_epoch(model, train_loader, optimizer, scaler, criterion)
        val_loss, val_acc, val_auc = validate(model, val_loader, criterion)

        print(f"Train Loss: {train_loss:.4f}, Acc: {train_acc:.4f}, AUC: {train_auc:.4f}")
        print(f"Val Loss:   {val_loss:.4f}, Acc: {val_acc:.4f}, AUC: {val_auc:.4f}")

        # Save best model
        if val_auc > best_auc:
            best_auc = val_auc
            torch.save(model.state_dict(), os.path.join(CFG.output_dir, "frame_model_best.pth"))
            print(f"✅ Saved new best model (AUC={best_auc:.4f})")

    print("\nTraining complete. Best AUC:", best_auc)


if __name__ == "__main__":
    main()
