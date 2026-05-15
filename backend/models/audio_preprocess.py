# backend/models/audio_preprocess.py

import torchaudio
import torch
from training.audio_features import FeatureExtractor


class AudioPreprocessor:
    def __init__(self):
        # Do NOT freeze to CPU — allow dynamic device switching
        self.fe = FeatureExtractor(augment=False)

    def load_audio(self, path):
        wav, sr = torchaudio.load(path)

        # Convert stereo -> mono
        if wav.size(0) > 1:
            wav = wav.mean(dim=0, keepdim=True)

        return wav  # keep on CPU for now

    def extract_melspec(self, wav):
        """
        FIX: Move FeatureExtractor internal buffers (STFT window, mel filters)
        to the SAME DEVICE as the input waveform.
        """

        device = wav.device

        # dynamically move STFT windows + mel filters
        self.fe = self.fe.to(device)

        # now safe to run
        mel = self.fe(wav)       # (1, 80, T) on correct device
        mel = mel.squeeze(0)     # → (80, T)

        return mel
