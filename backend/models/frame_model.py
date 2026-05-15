import torch
import torch.nn as nn
from torchvision import models

class FrameDeepfakeModel(nn.Module):
    """
    Frame-level DeepFake detector using a pretrained EfficientNet-B4 backbone.
    Trains to classify each frame as real or fake.
    """

    def __init__(self, num_classes=1, pretrained=True):
        super(FrameDeepfakeModel, self).__init__()

        # Load pretrained EfficientNet-B4
        backbone = models.efficientnet_b4(weights="IMAGENET1K_V1" if pretrained else None)
        self.feature_extractor = backbone.features
        in_features = backbone.classifier[1].in_features  # 1792

        # Replace classification head
        self.classifier = nn.Sequential(
            nn.AdaptiveAvgPool2d(1),
            nn.Flatten(),
            nn.Linear(in_features, 512),
            nn.BatchNorm1d(512),
            nn.GELU(),
            nn.Dropout(0.4),
            nn.Linear(512, num_classes)
        )

        # Use sigmoid for binary, softmax for multi-class
        self.activation = nn.Sigmoid() if num_classes == 1 else nn.Softmax(dim=1)

        self._init_weights()

    def _init_weights(self):
        for m in self.classifier:
            if isinstance(m, nn.Linear):
                nn.init.xavier_uniform_(m.weight)
                nn.init.zeros_(m.bias)

    def forward(self, x):
        """
        Args:
            x: (B, 3, 224, 224)
        Returns:
            prob: (B,) predicted probability of being fake (if binary)
        """
        x = self.feature_extractor(x)
        x = self.classifier(x)
        x = self.activation(x)
        return x.squeeze(1) if x.ndim == 2 and x.shape[1] == 1 else x

    def extract_features(self, x):
        """
        Return intermediate embeddings (used later for video-level aggregation)
        """
        with torch.no_grad():
            feats = self.feature_extractor(x)
            feats = nn.functional.adaptive_avg_pool2d(feats, 1).flatten(1)
        return feats

    # ---------- Save / Load ----------
    def save(self, path):
        torch.save({"model_state_dict": self.state_dict()}, path)

    @staticmethod
    def load(path, map_location="cpu"):
        checkpoint = torch.load(path, map_location=map_location)
        model = FrameDeepfakeModel(num_classes=1, pretrained=False)
        model.load_state_dict(checkpoint["model_state_dict"], strict=False)
        return model
FrameModel = FrameDeepfakeModel
