# training/train_audio_detector.py

import os
import torch
import numpy as np
from torch.utils.data import DataLoader
from torch.cuda.amp import GradScaler, autocast
from sklearn.metrics import roc_curve, auc, confusion_matrix
from tqdm import tqdm

from backend.models.audio_model import ECAPA_TDNN
from training.audio_datasets import ASVspoofDataset
from training.audio_features import FeatureExtractor
from training.audio_losses import AAMSoftmax
from training.audio_utils import save_checkpoint


def compute_eer(labels, scores):
    fpr, tpr, thresholds = roc_curve(labels, scores, pos_label=1)
    fnr = 1 - tpr
    eer = fpr[np.nanargmin(np.abs(fnr - fpr))]
    return eer * 100.0


def compute_minDCF(labels, scores, p_target=0.01, c_miss=1, c_fa=1):
    fpr, tpr, thresholds = roc_curve(labels, scores, pos_label=1)
    fnr = 1 - tpr
    c_det = p_target * c_miss * fnr + (1 - p_target) * c_fa * fpr
    return np.min(c_det)


def train():
    DEVICE = "cuda" if torch.cuda.is_available() else "cpu"

    base = "audio_data/ASVspoof2019/LA/"

    protocol_train = base + "ASVspoof2019_LA_cm_protocols/ASVspoof2019.LA.cm.train.trn.txt"
    protocol_dev   = base + "ASVspoof2019_LA_cm_protocols/ASVspoof2019.LA.cm.dev.trl.txt"

    train_flac = base + "ASVspoof2019_LA_train/flac/"
    dev_flac   = base + "ASVspoof2019_LA_dev/flac/"

    # Feature extractor
    feature_extractor = FeatureExtractor()

    # Datasets
    train_ds = ASVspoofDataset(protocol_train, train_flac, preprocess_fn=feature_extractor)
    dev_ds   = ASVspoofDataset(protocol_dev, dev_flac, preprocess_fn=feature_extractor)

    # Loaders
    train_loader = DataLoader(train_ds, batch_size=16, shuffle=True, num_workers=4)
    dev_loader   = DataLoader(dev_ds, batch_size=16, shuffle=False, num_workers=4)

    # Model + loss
    model = ECAPA_TDNN().to(DEVICE)
    classifier = AAMSoftmax().to(DEVICE)

    optimizer = torch.optim.Adam(model.parameters(), lr=1e-3)
    scaler = GradScaler()

    # Make sure save directory exists
    os.makedirs("backend/models", exist_ok=True)

    EPOCHS = 40
    best_acc = 0.0
    best_model_path = "backend/models/audio_detector_best_40_epoch.pt"

    for epoch in range(1, EPOCHS + 1):

        # ====================================
        #              TRAINING
        # ====================================
        model.train()
        classifier.train()
        total_loss = 0

        print(f"\nEpoch {epoch}/{EPOCHS} — Training")
        for mel, labels in tqdm(train_loader, desc="Training", ncols=100):
            mel, labels = mel.to(DEVICE), labels.to(DEVICE)

            optimizer.zero_grad()

            with autocast():
                emb = model(mel)
                logits = classifier(emb, labels)
                loss = torch.nn.CrossEntropyLoss()(logits, labels)

            scaler.scale(loss).backward()
            scaler.step(optimizer)
            scaler.update()

            total_loss += loss.item()

        # ====================================
        #             VALIDATION
        # ====================================
        model.eval()
        classifier.eval()

        all_scores = []
        all_labels = []
        correct = 0
        total = 0

        print(f"Epoch {epoch}/{EPOCHS} — Validation")
        with torch.no_grad():
            for mel, labels in tqdm(dev_loader, desc="Validating", ncols=100):
                mel, labels = mel.to(DEVICE), labels.to(DEVICE)

                emb = model(mel)
                logits = classifier(emb, labels)

                soft = torch.softmax(logits, dim=1)
                fake_scores = soft[:, 1].cpu().numpy()

                all_scores.extend(fake_scores)
                all_labels.extend(labels.cpu().numpy())

                predicted = logits.argmax(1)
                correct += (predicted == labels).sum().item()
                total += labels.size(0)

        val_acc = correct / total

        # Metrics
        eer = compute_eer(all_labels, all_scores)
        mindcf = compute_minDCF(all_labels, all_scores)
        fpr, tpr, _ = roc_curve(all_labels, all_scores)
        roc_auc = auc(fpr, tpr)
        cm = confusion_matrix(all_labels, np.round(all_scores))

        print("\n====================")
        print(f"Epoch {epoch}/{EPOCHS}")
        print(f"Loss: {total_loss:.4f}")
        print(f"Validation Accuracy: {val_acc:.4f}")
        print(f"EER: {eer:.2f}%")
        print(f"minDCF: {mindcf:.4f}")
        print(f"ROC-AUC: {roc_auc:.4f}")
        print(f"Confusion Matrix:\n{cm}")
        print("====================\n")

        # Save epoch checkpoint
        torch.save({
    "epoch": epoch,
    "model_state": model.state_dict(),
    "classifier_state": classifier.state_dict(),
    "optim_state": optimizer.state_dict()
}, f"audio_detector_epoch{epoch}.pt")


        # Save BEST model
        if val_acc > best_acc:
            best_acc = val_acc
            torch.save(model.state_dict(), best_model_path)
            print(f"🔥 BEST MODEL UPDATED — Saved to {best_model_path}")


if __name__ == "__main__":
    train()
