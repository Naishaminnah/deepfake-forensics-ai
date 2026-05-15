import os
import random
import numpy as np
from glob import glob
from tqdm import tqdm

import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import Dataset, DataLoader

import librosa

# ======================================================
# REPRODUCIBILITY
# ======================================================

SEED = 42
random.seed(SEED)
np.random.seed(SEED)
torch.manual_seed(SEED)
torch.cuda.manual_seed_all(SEED)

# ======================================================
# CONFIG
# ======================================================

TRAIN_BONA = r"D:\backend\audio_train_set\bonafide"
TRAIN_SPOOF = r"D:\backend\audio_train_set\spoof"

DEV_BONA = r"D:\backend\audio_dev_set\bonafide"
DEV_SPOOF = r"D:\backend\audio_dev_set\spoof"

TEST_BONA = r"D:\backend\audio_test_set\bonafide"
TEST_SPOOF = r"D:\backend\audio_test_set\spoof"

SAMPLE_RATE = 16000
N_MELS = 128
MAX_LEN = 400
BATCH_SIZE = 16
EPOCHS = 30
LR = 1e-4

DEVICE = "cuda" if torch.cuda.is_available() else "cpu"

# ======================================================
# BALANCED FILE LOADING
# ======================================================

def get_balanced_files(bona_path, spoof_path):

    bona = glob(os.path.join(bona_path, "*.flac"))
    spoof = glob(os.path.join(spoof_path, "*.flac"))

    min_len = min(len(bona), len(spoof))

    random.shuffle(bona)
    random.shuffle(spoof)

    bona = bona[:min_len]
    spoof = spoof[:min_len]

    files = bona + spoof
    labels = [0]*len(bona) + [1]*len(spoof)

    combined = list(zip(files, labels))
    random.shuffle(combined)

    files, labels = zip(*combined)
    return list(files), list(labels)

# ======================================================
# AUGMENTATION
# ======================================================

def augment_audio(y, sr):

    # Noise
    if random.random() < 0.3:
        noise = np.random.randn(len(y))
        y = y + 0.005 * noise

    # Pitch shift
    if random.random() < 0.3:
        try:
            steps = random.randint(-2, 2)
            y = librosa.effects.pitch_shift(y, sr=sr, n_steps=steps)
        except:
            pass

    # Time stretch (fixed API)
    if random.random() < 0.3:
        try:
            rate = random.uniform(0.9, 1.1)
            y = librosa.effects.time_stretch(y, rate=rate)
        except:
            pass

    return y

# ======================================================
# FEATURE EXTRACTION
# ======================================================

def extract_logmel(path, augment=False):

    y, sr = librosa.load(path, sr=SAMPLE_RATE)

    # Prevent short audio crash
    if len(y) < SAMPLE_RATE:
        y = np.pad(y, (0, SAMPLE_RATE - len(y)))

    if augment:
        y = augment_audio(y, sr)

    mel = librosa.feature.melspectrogram(
        y=y,
        sr=sr,
        n_mels=N_MELS
    )

    logmel = librosa.power_to_db(mel)

    # Pad / trim
    if logmel.shape[1] < MAX_LEN:
        pad = MAX_LEN - logmel.shape[1]
        logmel = np.pad(logmel, ((0, 0), (0, pad)))
    else:
        logmel = logmel[:, :MAX_LEN]

    return logmel.astype(np.float32)

# ======================================================
# DATASET
# ======================================================

class AudioDataset(Dataset):

    def __init__(self, files, labels, augment=False):
        self.files = files
        self.labels = labels
        self.augment = augment

    def __len__(self):
        return len(self.files)

    def __getitem__(self, idx):

        feat = extract_logmel(self.files[idx], self.augment)
        feat = torch.tensor(feat).unsqueeze(0)

        label = torch.tensor(self.labels[idx]).long()

        return feat, label

# ======================================================
# MODEL (CNN + ATTENTION)
# ======================================================

class AudioDetector(nn.Module):

    def __init__(self):
        super().__init__()

        self.conv = nn.Sequential(

            nn.Conv2d(1, 32, 3, padding=1),
            nn.BatchNorm2d(32),
            nn.ReLU(),
            nn.MaxPool2d(2),

            nn.Conv2d(32, 64, 3, padding=1),
            nn.BatchNorm2d(64),
            nn.ReLU(),
            nn.MaxPool2d(2),

            nn.Conv2d(64, 128, 3, padding=1),
            nn.BatchNorm2d(128),
            nn.ReLU(),
            nn.AdaptiveAvgPool2d((8, 8))
        )

        self.attn = nn.MultiheadAttention(128, 4, batch_first=True)

        self.fc = nn.Sequential(
            nn.Linear(128*8*8, 256),
            nn.ReLU(),
            nn.Dropout(0.3),
            nn.Linear(256, 2)
        )

    def forward(self, x):

        x = self.conv(x)

        b, c, h, w = x.shape
        x = x.view(b, c, h*w).permute(0, 2, 1)

        x, _ = self.attn(x, x, x)

        x = x.reshape(b, -1)
        return self.fc(x)

# ======================================================
# EVALUATION
# ======================================================

def evaluate(model, loader):

    model.eval()
    correct = 0
    total = 0

    with torch.no_grad():
        for x, y in loader:

            x, y = x.to(DEVICE), y.to(DEVICE)

            out = model(x)
            preds = torch.argmax(out, 1)

            correct += (preds == y).sum().item()
            total += y.size(0)

    return correct / total

# ======================================================
# TRAINING
# ======================================================

def main():

    print("Preparing datasets...")

    train_files, train_labels = get_balanced_files(TRAIN_BONA, TRAIN_SPOOF)
    dev_files, dev_labels = get_balanced_files(DEV_BONA, DEV_SPOOF)
    test_files, test_labels = get_balanced_files(TEST_BONA, TEST_SPOOF)

    train_loader = DataLoader(
        AudioDataset(train_files, train_labels, augment=True),
        batch_size=BATCH_SIZE,
        shuffle=True,
        num_workers=2,
        pin_memory=True
    )

    dev_loader = DataLoader(
        AudioDataset(dev_files, dev_labels),
        batch_size=BATCH_SIZE
    )

    test_loader = DataLoader(
        AudioDataset(test_files, test_labels),
        batch_size=BATCH_SIZE
    )

    model = AudioDetector().to(DEVICE)

    criterion = nn.CrossEntropyLoss()
    optimizer = optim.Adam(model.parameters(), lr=LR)

    best_dev = 0

    print(f"Training on {DEVICE}...")

    for epoch in range(EPOCHS):

        model.train()
        running_loss = 0

        for x, y in tqdm(train_loader):

            x, y = x.to(DEVICE), y.to(DEVICE)

            optimizer.zero_grad()

            out = model(x)
            loss = criterion(out, y)

            loss.backward()
            optimizer.step()

            running_loss += loss.item()

        dev_acc = evaluate(model, dev_loader)

        print(f"\nEpoch {epoch+1}/{EPOCHS}")
        print(f"Loss: {running_loss:.3f}")
        print(f"Dev Accuracy: {dev_acc:.4f}")

        if dev_acc > best_dev:
            best_dev = dev_acc
            torch.save(model.state_dict(), "best_audio_model.pth")
            print("Saved new best model.")

    # ================= FINAL TEST =================

    print("\nEvaluating best model on TEST set...")

    model.load_state_dict(torch.load("best_audio_model.pth"))
    test_acc = evaluate(model, test_loader)

    print(f"Final Test Accuracy: {test_acc:.4f}")

# ======================================================

if __name__ == "__main__":
    main()
