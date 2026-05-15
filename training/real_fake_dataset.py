import os
from PIL import Image
from torch.utils.data import Dataset

class RealFakeDataset(Dataset):
    def __init__(self, root, transform=None, split="train"):
        """
        root  = gan_dataset/
        split = 'train' or 'val'

        Expected structure:
            gan_dataset/ADM/train/ai/
            gan_dataset/ADM/train/nature/
            gan_dataset/BigGAN/train/ai/
            gan_dataset/BigGAN/train/nature/
            ... and same for val/
        """

        self.samples = []
        self.transform = transform

        # Scan GAN groups
        for gan_name in os.listdir(root):
            gan_path = os.path.join(root, gan_name)

            if not os.path.isdir(gan_path):
                continue

            split_path = os.path.join(gan_path, split)
            if not os.path.isdir(split_path):
                continue

            ai_path = os.path.join(split_path, "ai")
            nature_path = os.path.join(split_path, "nature")

            # -------------------------
            # FAKE = ai
            # -------------------------
            if os.path.isdir(ai_path):
                for f in os.listdir(ai_path):
                    if f.lower().endswith(("jpg", "jpeg", "png", "webp")):
                        self.samples.append((os.path.join(ai_path, f), 1))  # fake = 1

            # -------------------------
            # REAL = nature
            # -------------------------
            if os.path.isdir(nature_path):
                for f in os.listdir(nature_path):
                    if f.lower().endswith(("jpg", "jpeg", "png", "webp")):
                        self.samples.append((os.path.join(nature_path, f), 0))  # real = 0

        if len(self.samples) == 0:
            raise ValueError(f"[RealFakeDataset] No samples found under root={root}, split={split}")

        print(f"[RealFakeDataset] Loaded {len(self.samples)} images (split={split})")

        # Preload first GOOD image to use as fallback
        self.fallback_img = self._load_first_good()

    def _load_first_good(self):
        """Find one good image to use as fallback if corrupt images are found."""
        for path, _ in self.samples:
            try:
                return Image.open(path).convert("RGB")
            except:
                continue
        raise RuntimeError("No valid image found in dataset!")

    def __len__(self):
        return len(self.samples)

    def __getitem__(self, index):
        path, label = self.samples[index]

        try:
            img = Image.open(path).convert("RGB")
        except Exception:
            print(f"[CORRUPT] Skipping: {path}")
            img = self.fallback_img.copy()  # no infinite recursion

        if self.transform:
            img = self.transform(img)

        return img, label
