# training/audio_datasets.py

import os
import torch
import torchaudio
from torch.utils.data import Dataset

class ASVspoofDataset(Dataset):
    def __init__(self, protocol_file, audio_dir, preprocess_fn=None):
        self.audio_dir = audio_dir
        self.preprocess_fn = preprocess_fn

        self.entries = []
        with open(protocol_file, "r") as f:
            for line in f:
                parts = line.strip().split()
                file_id = parts[1]
                label = parts[-1]   # "bonafide" or "spoof"
                self.entries.append((file_id, 0 if label == "bonafide" else 1))

    def __len__(self):
        return len(self.entries)

    def __getitem__(self, idx):
        file_id, label = self.entries[idx]
        path = os.path.join(self.audio_dir, file_id + ".flac")

        wav, sr = torchaudio.load(path)

        # convert to mono
        wav = wav.mean(dim=0, keepdim=True)

        if self.preprocess_fn:
            mel = self.preprocess_fn(wav)
            mel = mel.squeeze(0)     # (1, 80, T) -> (80, T)
            return mel.float(), torch.tensor(label)

        return wav.float(), torch.tensor(label)
