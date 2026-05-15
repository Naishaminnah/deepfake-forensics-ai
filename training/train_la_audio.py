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
from sklearn.metrics import roc_curve

# =========================
# SEED
# =========================
SEED = 42
random.seed(SEED)
np.random.seed(SEED)
torch.manual_seed(SEED)

DEVICE = "cuda" if torch.cuda.is_available() else "cpu"

# =========================
# DATA PATHS
# =========================
TRAIN_BONA = r"D:\backend\audio_train_set\bonafide"
TRAIN_SPOOF = r"D:\backend\audio_train_set\spoof"

DEV_BONA = r"D:\backend\audio_dev_set\bonafide"
DEV_SPOOF = r"D:\backend\audio_dev_set\spoof"

TEST_BONA = r"D:\backend\audio_test_set\bonafide"
TEST_SPOOF = r"D:\backend\audio_test_set\spoof"

# =========================
# AUDIO CONFIG
# =========================
SR = 16000
N_MELS = 80
MAX_LEN = 400

BATCH_SIZE = 16
EPOCHS = 40
LR = 3e-4

# =========================
# BALANCE DATA
# =========================
def load_balanced(bona, spoof):

    b = glob(os.path.join(bona, "*.flac"))
    s = glob(os.path.join(spoof, "*.flac"))

    m = min(len(b), len(s))

    random.shuffle(b)
    random.shuffle(s)

    b = b[:m]
    s = s[:m]

    files = b + s
    labels = [0]*len(b) + [1]*len(s)

    combo = list(zip(files, labels))
    random.shuffle(combo)

    f,l = zip(*combo)
    return list(f), list(l)

# =========================
# AUGMENT
# =========================
def augment(y, sr):

    if random.random() < 0.3:
        noise = np.random.randn(len(y))
        y = y + 0.003 * noise

    if random.random() < 0.3:
        try:
            y = librosa.effects.pitch_shift(y, sr=sr, n_steps=random.randint(-2,2))
        except:
            pass

    if random.random() < 0.3:
        try:
            rate = random.uniform(0.9,1.1)
            y = librosa.effects.time_stretch(y, rate=rate)
        except:
            pass

    return y

# =========================
# FEATURE
# =========================
def logmel(path, aug=False):

    y, sr = librosa.load(path, sr=SR)

    if len(y) < SR:
        y = np.pad(y, (0, SR-len(y)))

    if aug:
        y = augment(y, sr)

    mel = librosa.feature.melspectrogram(y=y, sr=sr, n_mels=N_MELS)
    mel = librosa.power_to_db(mel)

    if mel.shape[1] < MAX_LEN:
        mel = np.pad(mel, ((0,0),(0,MAX_LEN-mel.shape[1])))
    else:
        mel = mel[:,:MAX_LEN]

    return mel.astype(np.float32)

# =========================
# DATASET
# =========================
class SpoofDataset(Dataset):

    def __init__(self, files, labels, aug=False):
        self.files = files
        self.labels = labels
        self.aug = aug

    def __len__(self):
        return len(self.files)

    def __getitem__(self, idx):

        feat = logmel(self.files[idx], self.aug)
        feat = torch.tensor(feat).unsqueeze(0)

        label = torch.tensor(self.labels[idx]).float()
        return feat, label

# =========================
# MFM LAYER (LCNN CORE)
# =========================
class MFM(nn.Module):
    def __init__(self, in_channels, out_channels, kernel=3, stride=1, padding=1):
        super().__init__()

        self.conv = nn.Conv2d(
            in_channels,
            out_channels*2,
            kernel,
            stride,
            padding
        )

    def forward(self, x):
        x = self.conv(x)
        out = torch.split(x, x.shape[1]//2, 1)
        return torch.max(out[0], out[1])

# =========================
# LCNN MODEL
# =========================
class LCNN(nn.Module):

    def __init__(self):
        super().__init__()

        self.features = nn.Sequential(

            MFM(1, 32),
            nn.MaxPool2d(2),

            MFM(32, 64),
            nn.MaxPool2d(2),

            MFM(64, 128),
            nn.MaxPool2d(2),

            MFM(128, 128),
            nn.AdaptiveAvgPool2d((4,4))
        )

        self.fc = nn.Sequential(
            nn.Linear(128*4*4, 256),
            nn.ReLU(),
            nn.Dropout(0.3),
            nn.Linear(256,1)
        )

    def forward(self, x):
        x = self.features(x)
        x = x.view(x.size(0), -1)
        return self.fc(x).squeeze(1)

# =========================
# EER CALC
# =========================
def compute_eer(labels, scores):

    fpr, tpr, thr = roc_curve(labels, scores)
    fnr = 1 - tpr
    eer = fpr[np.nanargmin(np.abs(fnr - fpr))]
    return eer

# =========================
# EVAL
# =========================
def evaluate(model, loader):

    model.eval()
    scores = []
    labels = []

    with torch.no_grad():
        for x,y in loader:

            x = x.to(DEVICE)
            out = torch.sigmoid(model(x)).cpu().numpy()

            scores.extend(out)
            labels.extend(y.numpy())

    eer = compute_eer(labels, scores)

    preds = [1 if s>0.5 else 0 for s in scores]
    acc = np.mean(np.array(preds)==np.array(labels))

    return acc, eer

# =========================
# TRAIN
# =========================
def main():

    train_f, train_l = load_balanced(TRAIN_BONA, TRAIN_SPOOF)
    dev_f, dev_l = load_balanced(DEV_BONA, DEV_SPOOF)
    test_f, test_l = load_balanced(TEST_BONA, TEST_SPOOF)

    train_loader = DataLoader(
        SpoofDataset(train_f, train_l, aug=True),
        batch_size=BATCH_SIZE,
        shuffle=True
    )

    dev_loader = DataLoader(
        SpoofDataset(dev_f, dev_l),
        batch_size=BATCH_SIZE
    )

    test_loader = DataLoader(
        SpoofDataset(test_f, test_l),
        batch_size=BATCH_SIZE
    )

    model = LCNN().to(DEVICE)

    criterion = nn.BCEWithLogitsLoss()
    optimizer = optim.Adam(model.parameters(), lr=LR)

    best_eer = 1.0

    for epoch in range(EPOCHS):

        model.train()
        total_loss = 0

        for x,y in tqdm(train_loader):

            x = x.to(DEVICE)
            y = y.to(DEVICE)

            optimizer.zero_grad()

            out = model(x)
            loss = criterion(out, y)

            loss.backward()
            optimizer.step()

            total_loss += loss.item()

        acc, eer = evaluate(model, dev_loader)

        print(f"\nEpoch {epoch+1}")
        print(f"Loss: {total_loss:.3f}")
        print(f"Dev ACC: {acc:.4f}")
        print(f"Dev EER: {eer:.4f}")

        if eer < best_eer:
            best_eer = eer
            torch.save(model.state_dict(), "best_lcnn_model.pth")

    print("\nTesting best model...")
    model.load_state_dict(torch.load("best_lcnn_model.pth"))

    acc, eer = evaluate(model, test_loader)

    print(f"Test ACC: {acc:.4f}")
    print(f"Test EER: {eer:.4f}")

# =========================

if __name__ == "__main__":
    main()
