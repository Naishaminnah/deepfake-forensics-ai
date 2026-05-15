import torch
from PIL import Image
from training.gan_transforms import test_transform
from backend.models.gan_fingerprinter import GANFingerprinter

class GANDetector:
    def __init__(self, device=None):
        self.device = device or ("cuda" if torch.cuda.is_available() else "cpu")

        # Load real vs fake model
        self.rf_model = GANFingerprinter(num_classes=2).to(self.device)
        self.rf_model.load_state_dict(torch.load("real_fake_detector.pth", map_location=self.device))
        self.rf_model.eval()

        # Load GAN type model
        self.gan_classes = ["ADM", "BigGAN", "Glide", "VQDM"]
        self.gan_model = GANFingerprinter(num_classes=len(self.gan_classes)).to(self.device)
        self.gan_model.load_state_dict(torch.load("gan_type_classifier.pth", map_location=self.device))
        self.gan_model.eval()

    def predict(self, img_path):
        try:
            img = Image.open(img_path).convert("RGB")
        except Exception as e:
            return {"error": f"Cannot open image: {e}"}

        x = test_transform(img).unsqueeze(0).to(self.device)

        # -------- Stage 1: real vs fake --------
        with torch.no_grad():
            rf_logits = self.rf_model(x)
            rf_pred = rf_logits.argmax(1).item()
            rf_conf = torch.softmax(rf_logits, dim=1)[0][rf_pred].item()

        if rf_pred == 0:  # Real
            return {"type": "REAL", "gan_type": None, "confidence": float(rf_conf)}

        # -------- Stage 2: GAN type --------
        with torch.no_grad():
            gt_logits = self.gan_model(x)
            gt_pred = gt_logits.argmax(1).item()
            gt_conf = torch.softmax(gt_logits, dim=1)[0][gt_pred].item()

        return {
            "type": "FAKE",
            "gan_type": self.gan_classes[gt_pred],
            "confidence": float(gt_conf),
        }
