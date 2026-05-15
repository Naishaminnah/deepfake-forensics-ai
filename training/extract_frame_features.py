import os
import torch
import numpy as np
from tqdm import tqdm
from torchvision import transforms
from torch.utils.data import Dataset
from PIL import Image

from backend.models.frame_model import FrameDeepfakeModel as FrameModel  # trained frame-level CNN
from backend.config import DEVICE


class FrameFeatureDataset(Dataset):
    """Loads video frame paths for real/fake classes."""
    def __init__(self, dataset_root, transform=None):
        self.transform = transform
        self.samples = []

        for label_name in ['real', 'fake']:
            class_dir = os.path.join(dataset_root, label_name)
            if not os.path.exists(class_dir):
                continue

            for video_name in os.listdir(class_dir):
                video_path = os.path.join(class_dir, video_name)
                if not os.path.isdir(video_path):
                    continue

                frames = sorted([
                    os.path.join(video_path, f)
                    for f in os.listdir(video_path)
                    if f.lower().endswith(('.jpg', '.png'))
                ])

                if len(frames) > 0:
                    self.samples.append({
                        "video": video_name,
                        "frames": frames,
                        "label": 0 if label_name == 'real' else 1
                    })

    def __len__(self):
        return len(self.samples)

    def __getitem__(self, idx):
        return self.samples[idx]


def extract_embeddings(model, dataset_root, output_root):
    """Extract per-frame and per-video embeddings."""
    os.makedirs(output_root, exist_ok=True)

    transform = transforms.Compose([
        transforms.Resize((224, 224)),
        transforms.ToTensor(),
        transforms.Normalize([0.485, 0.456, 0.406],
                             [0.229, 0.224, 0.225])
    ])

    dataset = FrameFeatureDataset(dataset_root, transform=transform)
    model.eval()

    device_type = 'cuda' if DEVICE.type == 'cuda' else 'cpu'

    with torch.no_grad(), torch.amp.autocast(device_type=device_type):
        for item in tqdm(dataset, desc="Extracting frame embeddings"):
            video_name = item["video"]
            frames = item["frames"]
            label = item["label"]

            all_feats = []

            for fpath in frames:
                img = Image.open(fpath).convert("RGB")
                img_tensor = transform(img).unsqueeze(0).to(DEVICE)
                feat = model.extract_features(img_tensor).cpu().numpy().squeeze()
                all_feats.append(feat)

            all_feats = np.stack(all_feats, axis=0)

            # --- Save frame embeddings per video ---
            video_folder = os.path.join(output_root, video_name)
            os.makedirs(video_folder, exist_ok=True)
            np.save(os.path.join(video_folder, "frames.npy"), all_feats)

            # --- Save mean embedding (for temporal model training) ---
            mean_feat = np.mean(all_feats, axis=0)
            np.save(os.path.join(video_folder, "video_mean.npy"), mean_feat)

            # --- Save metadata ---
            meta = {
                "label": label,
                "num_frames": len(frames)
            }
            np.save(os.path.join(video_folder, "meta.npy"), meta)

    print(f"\n✅ Frame & video-level embeddings saved in: {output_root}")


def main():
    dataset_root = r"D:\deepfake_forensics_ai\datasets\celeb_df_v2"
    checkpoint_path = r"D:\deepfake_forensics_ai\checkpoints\frame_model_best.pth"
    output_root = r"D:\deepfake_forensics_ai\backend\features"

    print(f"[CONFIG] DEVICE: {DEVICE}")
    print(f"[INFO] Loading model from {checkpoint_path}")

    model = FrameModel(pretrained=False).to(DEVICE)

    ckpt = torch.load(checkpoint_path, map_location=DEVICE)
    if "model_state_dict" in ckpt:
        ckpt = ckpt["model_state_dict"]
    model.load_state_dict(ckpt, strict=False)

    print("[INFO] Frame model loaded successfully.")
    extract_embeddings(model, dataset_root, output_root)
    print("[✅] Feature extraction complete!")


if __name__ == "__main__":
    main()
