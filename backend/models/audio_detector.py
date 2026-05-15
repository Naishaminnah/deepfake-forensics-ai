# backend/models/audio_detector.py

import torch
import torch.nn.functional as F

from backend.models.audio_model import ECAPA_TDNN
from backend.models.audio_preprocess import AudioPreprocessor


class AudioDeepfakeDetector:
    def __init__(self, model_path, device="cuda"):
        self.device = device

        # -----------------------
        # Load base ECAPA model
        # -----------------------
        self.model = ECAPA_TDNN().to(device)
        checkpoint = torch.load(model_path, map_location=device)

        if "model_state" in checkpoint:
            self.model.load_state_dict(checkpoint["model_state"])
        else:
            print("[WARN] model_state not found in checkpoint.")
        self.model.eval()

        # -----------------------
        # Load NORMAL classifier (not AAMSoftmax)
        # -----------------------
        self.classifier = torch.nn.Linear(192, 2).to(device)

        if "classifier_state" in checkpoint:
            missing, unexpected = self.classifier.load_state_dict(
                checkpoint["classifier_state"], strict=False
            )
            print("[INFO] Loaded classifier (missing ignored):",
                  missing, unexpected)
        else:
            print("[WARN] classifier_state missing. Using random classifier.")

        self.classifier.eval()

        self.pre = AudioPreprocessor()

    @torch.no_grad()
    def predict(self, file_path):
        # Preprocessing
        wav = self.pre.load_audio(file_path).to(self.device)
        mel = self.pre.extract_melspec(wav).to(self.device)
        mel = mel.unsqueeze(0)  # (1, 80, T)

        # Multi-crop trick
        crops = [mel, mel[:, :, :-5], mel[:, :, 5:]]
        scores = []

        for crop in crops:
            emb = self.model(crop)           # -> 192-d embedding
            logits = self.classifier(emb)    # -> (1, 2)
            soft = F.softmax(logits, dim=1)[0]
            scores.append(soft.cpu().numpy())

        avg_prob = sum(scores) / len(scores)

        real, fake = avg_prob
        label = "REAL" if real > fake else "FAKE"

        return {
            "label": label,
            "real_confidence": round(float(real) * 100, 2),
            "fake_confidence": round(float(fake) * 100, 2),
        }
