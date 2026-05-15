# backend/models/image_detector.py
"""
EfficientNet-B4 based Image Deepfake Detector (binary: real vs fake)
- Includes training-ready model class
- Supports easy inference with .predict()
- Auto-loads best trained model when imported
"""

from pathlib import Path
import torch
import torch.nn as nn
import torch.nn.functional as F
from torchvision.models import efficientnet_b4, EfficientNet_B4_Weights
from torchvision import transforms
from PIL import Image
from backend.config import DEVICE, MODEL_DIR


class ImageDeepfakeDetector(nn.Module):
    def __init__(self, pretrained=True, num_classes: int = 2):
        super().__init__()
        weights = EfficientNet_B4_Weights.IMAGENET1K_V1 if pretrained else None
        backbone = efficientnet_b4(weights=weights)
        in_features = backbone.classifier[1].in_features

        # Replace classifier with a more regularized head
        backbone.classifier = nn.Sequential(
            nn.Dropout(p=0.4, inplace=True),
            nn.Linear(in_features, 512),
            nn.ReLU(inplace=True),
            nn.Dropout(p=0.3),
            nn.Linear(512, num_classes)
        )

        self.model = backbone
        self.to(DEVICE)

    def forward(self, x):
        return self.model(x)

    def predict(self, image_path: str):
        """
        Inference for a single image path
        Returns (label, probability_of_fake)
        """
        self.eval()
        tf = transforms.Compose([
            transforms.Resize((380, 380)),
            transforms.ToTensor(),
            transforms.Normalize(mean=[0.485,0.456,0.406], std=[0.229,0.224,0.225]),
        ])
        img = Image.open(image_path).convert("RGB")
        t = tf(img).unsqueeze(0).to(DEVICE)
        with torch.no_grad():
            logits = self(t)
            probs = F.softmax(logits, dim=1)
            p_fake = float(probs[0, 1].cpu().item())
            label = "FAKE" if probs.argmax(dim=1).item() == 1 else "REAL"
        return label, p_fake

    def save(self, filename="image_detector_final.pth"):
        MODEL_DIR.mkdir(parents=True, exist_ok=True)
        path = Path(MODEL_DIR) / filename
        torch.save(self.state_dict(), path)
        print(f"[OK] Model saved to {path}")

    def load(self, filename="image_detector_final.pth"):
        path = Path(MODEL_DIR) / filename
        if not path.exists():
            raise FileNotFoundError(f"Model file not found: {path}")
        self.load_state_dict(torch.load(path, map_location=DEVICE))
        self.to(DEVICE)
        self.eval()
        print(f"[OK] Loaded model from {path}")


# --------- GLOBAL AUTO-LOAD SECTION FOR API USE ---------
MODEL_PATH = Path(MODEL_DIR) / "image_detector_final.pth"
model = ImageDeepfakeDetector(pretrained=False)
if MODEL_PATH.exists():
    model.load_state_dict(torch.load(MODEL_PATH, map_location=DEVICE))
    model.eval()
    print(f"[OK] Auto-loaded model from {MODEL_PATH}")
else:
    print("[WARN] Model file not found, please train or adjust path.")


def predict_image(image_path: str):
    label, fake_prob = model.predict(image_path)

    real_prob = 1 - fake_prob

    confidence = real_prob if label == "REAL" else fake_prob

    return {
        "prediction": label,
        "confidence": round(confidence, 3),
        "fake_probability": round(fake_prob, 3),
        "real_probability": round(real_prob, 3),
    }


if __name__ == "__main__":
    # Quick test
    x = torch.randn(1, 3, 380, 380).to(DEVICE)
    y = model(x)
    print("output shape:", y.shape)
