# training/audio_features.py

import torch
import torchaudio
import torchaudio.transforms as T
import torch.nn.functional as F
import torch.nn as nn


class FeatureExtractor(nn.Module):
    def __init__(self, sample_rate=16000, augment=False, target_frames=400):
        super().__init__()

        self.sample_rate = sample_rate
        self.augment = augment
        self.target_frames = target_frames

        # Register torchaudio transforms as modules so .to(device) works
        self.melspec = T.MelSpectrogram(
            sample_rate=sample_rate,
            n_fft=1024,
            hop_length=160,
            win_length=400,
            n_mels=80,
            f_min=20,
            f_max=7600
        )

        self.db = T.AmplitudeToDB()

        # Optional SpecAugment
        self.time_mask = T.TimeMasking(time_mask_param=20)
        self.freq_mask = T.FrequencyMasking(freq_mask_param=8)

    def _fix_length(self, mel):
        """
        mel: (1, 80, T)
        Ensures T = target_frames (pad or truncate)
        """
        T_curr = mel.shape[-1]

        if T_curr > self.target_frames:
            mel = mel[:, :, :self.target_frames]

        elif T_curr < self.target_frames:
            pad_amount = self.target_frames - T_curr
            mel = F.pad(mel, (0, pad_amount))

        return mel

    def forward(self, wav):
        """
        wav: (1, N) on CPU or CUDA
        output: (1, 80, target_frames)
        """

        device = wav.device

        # Ensure all transforms run on SAME device
        self.melspec = self.melspec.to(device)
        self.db = self.db.to(device)
        self.time_mask = self.time_mask.to(device)
        self.freq_mask = self.freq_mask.to(device)

        # MelSpectrogram
        mel = self.melspec(wav)
        mel = self.db(mel)

        # Normalize
        mel = (mel - mel.mean()) / (mel.std() + 1e-6)

        # Fix length
        mel = self._fix_length(mel)

        # Augment if enabled
        if self.augment:
            mel = self.time_mask(mel)
            mel = self.freq_mask(mel)

        return mel
