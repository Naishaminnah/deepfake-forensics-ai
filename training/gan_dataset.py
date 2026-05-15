import os
from PIL import Image, UnidentifiedImageError
from torch.utils.data import Dataset

class GANTypeDataset(Dataset):
    def __init__(self, root, transform=None, split="train"):
        """
        root: gan_dataset_sample folder
        split: 'train' or 'val'
        """
        self.samples = []
        self.transform = transform

        # Get GAN classes from split folder
        split_path = os.path.join(root, split)
        gan_classes = [d for d in os.listdir(split_path) if os.path.isdir(os.path.join(split_path, d))]
        gan_classes = sorted(gan_classes)
        self.class_to_idx = {cls: i for i, cls in enumerate(gan_classes)}

        for gan_folder in gan_classes:
            gan_path = os.path.join(split_path, gan_folder)

            # Prefer 'ai_small' if exists, else 'ai'
            ai_path = os.path.join(gan_path, "ai_small")
            if not os.path.isdir(ai_path):
                ai_path = os.path.join(gan_path, "ai")

            if not os.path.isdir(ai_path):
                continue

            for file in os.listdir(ai_path):
                if file.lower().endswith(("jpg", "png", "jpeg")):
                    file_path = os.path.join(ai_path, file)
                    try:
                        # Try opening the image to verify
                        with Image.open(file_path) as im:
                            im.verify()  # Will raise exception if corrupted
                        self.samples.append((file_path, self.class_to_idx[gan_folder]))
                    except (UnidentifiedImageError, OSError, ValueError):
                        print(f"[WARNING] Skipping corrupted image: {file_path}")

        if len(self.samples) == 0:
            raise ValueError(f"[GANTypeDataset] No samples found in {root} for split '{split}'")

        print(f"[INFO] {split.capitalize()} samples loaded: {len(self.samples)}")
        print(f"[INFO] Classes: {self.class_to_idx}")

    def __len__(self):
        return len(self.samples)

    def __getitem__(self, idx):
        path, label = self.samples[idx]
        try:
            img = Image.open(path).convert("RGB")
            if self.transform:
                img = self.transform(img)
            return img, label
        except (UnidentifiedImageError, OSError, ValueError):
            # This should rarely happen since we verified at init
            print(f"[WARNING] Skipping corrupted image at runtime: {path}")
            return self.__getitem__((idx + 1) % len(self.samples))
