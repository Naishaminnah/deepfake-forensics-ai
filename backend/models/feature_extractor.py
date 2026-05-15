# backend/models/feature_extractor.py
import torch
import torch.nn as nn
from torchvision import models, transforms
from PIL import Image
from backend.config import DEVICE

class FrameFeatureExtractor(nn.Module):
    """
    EfficientNet-B4 feature extractor for video frames.
    - By default, all encoder parameters are frozen.
    - Use .unfreeze_top_layers(num_layers) or .unfreeze_by_name(patterns) to enable fine-tuning.
    - Forward supports autograd (no @torch.no_grad()) so gradients can flow if some params are trainable.
    """
    def __init__(self, checkpoint_path="backend/models/image_detector_final.pth", device=DEVICE):
        super().__init__()
        self.device = device

        # Build backbone (EfficientNet-B4)
        # Note: weights=None because we'll load your checkpoint
        efficientnet = models.efficientnet_b4(weights=None)
        # Replace classifier with identity to get penultimate features
        # EfficientNet-B4 classifier is typically something like Sequential( ... , Linear(in_features=1792))
        efficientnet.classifier = nn.Identity()

        # Load checkpoint robustly
        if checkpoint_path is not None:
            ck = torch.load(checkpoint_path, map_location=str(device))
            state = ck.get("model_state_dict", ck)
            # load with strict=False to avoid mismatch issues
            efficientnet.load_state_dict(state, strict=False)

        # Freeze all by default
        for p in efficientnet.parameters():
            p.requires_grad = False

        self.encoder = efficientnet.to(self.device)
        self.encoder.eval()  # default mode is eval; set to train() in training when fine-tuning

        # Standard transforms (should match image detector preprocessing)
        self.transform = transforms.Compose([
            transforms.Resize((380, 380)),
            transforms.ToTensor(),
            transforms.Normalize(mean=[0.485, 0.456, 0.406],
                                 std=[0.229, 0.224, 0.225])
        ])

    def freeze_all(self):
        for p in self.encoder.parameters():
            p.requires_grad = False

    def unfreeze_all(self):
        for p in self.encoder.parameters():
            p.requires_grad = True

    def unfreeze_top_layers(self, num_blocks: int = 1):
        """
        Unfreeze the last `num_blocks` blocks of EfficientNet features.
        EfficientNet feature blocks are typically named 'features.X' where X indexes blocks.
        """
        # find feature layers names sorted
        names = [name for name, _ in self.encoder.named_parameters()]
        # heuristic: unfreeze last num_blocks * approximate param groups
        # We'll look for "features." occurrences and unfreeze params that contain the highest indices
        feature_param_names = [n for n in names if n.startswith("features.")]
        if not feature_param_names:
            # fallback: unfreeze last N parameters
            last_params = names[-(num_blocks * 10):]
            for n, p in self.encoder.named_parameters():
                if n in last_params:
                    p.requires_grad = True
            return

        # extract block indices
        blocks = {}
        for n in feature_param_names:
            # e.g., "features.6.conv.0.weight"
            parts = n.split(".")
            try:
                idx = int(parts[1])
            except Exception:
                continue
            blocks.setdefault(idx, []).append(n)

        block_idxs = sorted(blocks.keys())
        to_unfreeze = block_idxs[-num_blocks:] if num_blocks <= len(block_idxs) else block_idxs
        for idx in to_unfreeze:
            for n, p in self.encoder.named_parameters():
                if n.startswith(f"features.{idx}."):
                    p.requires_grad = True

    def unfreeze_by_name(self, patterns):
        """
        Unfreeze any encoder param where the name contains one of the provided patterns.
        patterns: list of substrings to match (e.g. ["features.6", "features.7"])
        """
        for n, p in self.encoder.named_parameters():
            if any(pat in n for pat in patterns):
                p.requires_grad = True

    def to_train_mode_if_needed(self):
        """
        call encoder.train() if any parameters are trainable
        """
        any_trainable = any(p.requires_grad for p in self.encoder.parameters())
        if any_trainable:
            self.encoder.train()
        else:
            self.encoder.eval()

    def forward(self, frames: torch.Tensor, batch_size: int = 32):
        """
        frames: (T,3,H,W) or (B,T,3,H,W)
        returns: (T, feat_dim) or (B, T, feat_dim)
        NOTE: this forward DOES allow gradients to flow into encoder if some params have requires_grad=True.
        """
        # Accept PIL images via helper extract_from_pil if needed
        single_video = False
        if frames.dim() == 4:
            single_video = True
            T_frames, C, H, W = frames.shape
            frames_flat = frames.to(self.device)
        elif frames.dim() == 5:
            B, T_frames, C, H, W = frames.shape
            frames_flat = frames.view(B * T_frames, C, H, W).to(self.device)
        else:
            raise ValueError("frames must be (T,3,H,W) or (B,T,3,H,W)")

        embeddings = []
        # Use amp autocast for faster inference / training on CUDA
        autocast_ctx = torch.amp.autocast if torch.cuda.is_available() else torch.cpu.amp.autocast  # fallback
        with torch.amp.autocast(device_type='cuda'):

            for i in range(0, frames_flat.size(0), batch_size):
                batch = frames_flat[i:i+batch_size].float()
                feats = self.encoder(batch)    # (b, feat_dim)
                embeddings.append(feats.detach().cpu() if not any(p.requires_grad for p in self.encoder.parameters()) else feats.cpu())

        embeddings = torch.cat(embeddings, dim=0)

        if single_video:
            return embeddings  # (T, feat_dim)
        else:
            embeddings = embeddings.view(B, T_frames, -1)
            return embeddings  # (B, T, feat_dim)

    def extract_from_pil(self, pil_images):
        """
        Extract features from list of PIL images. Returns (B, feat_dim)
        pil_images: list of PIL.Image
        """
        tensors = torch.stack([self.transform(img) for img in pil_images]).to(self.device)
        return self.forward(tensors)

    def save(self, filename="frame_feature_extractor.pth"):
        torch.save(self.state_dict(), filename)
        print(f"✅ Feature extractor saved to {filename}")

    def load(self, checkpoint_path):
        state_dict = torch.load(checkpoint_path, map_location=self.device)
        self.load_state_dict(state_dict)
        self.to(self.device)
        self.eval()
        print(f"✅ Feature extractor loaded from {checkpoint_path}")
