import os
import cv2
import random
import torch
from torch.utils.data import Dataset
from torchvision import transforms
from PIL import Image

class FrameDataset(Dataset):
    """
    Dataset for extracting frames from FaceForensics++ (C23) and Celeb-DF v2 videos.
    Automatically assigns labels and uses the provided test list for proper splits.
    """

    def __init__(self, ffpp_root=None, celebdf_root=None, test_list_path=None,
                 split='train', frame_interval=10, transform=None):
        """
        Args:
            ffpp_root (str): Root path to FaceForensics++ dataset.
            celebdf_root (str): Root path to Celeb-DF v2 dataset.
            test_list_path (str): Path to list_of_testing_videos.txt (for Celeb-DF).
            split (str): 'train', 'val', or 'test'.
            frame_interval (int): Extract every Nth frame.
            transform: torchvision transforms for preprocessing.
        """
        self.ffpp_root = ffpp_root
        self.celebdf_root = celebdf_root
        self.test_list = set()
        self.split = split
        self.frame_interval = frame_interval
        self.transform = transform

        # Load CelebDF test list if provided
        if test_list_path and os.path.exists(test_list_path):
            with open(test_list_path, "r") as f:
                self.test_list = set(line.strip() for line in f.readlines())

        # Gather all samples
        self.samples = self._gather_samples()
        print(f"[INFO] Found {len(self.samples)} videos for {split} split")

    def _gather_samples(self):
        samples = []

        # =============== FACEFORENSICS++ =================
        if self.ffpp_root and os.path.exists(self.ffpp_root):
            # Real videos
            real_dir = os.path.join(self.ffpp_root, "original_sequences", "youtube", "c23", "videos")
            if os.path.exists(real_dir):
                for f in os.listdir(real_dir):
                    if f.endswith((".mp4", ".avi", ".mov")):
                        samples.append((os.path.join(real_dir, f), 0))

            # Fake videos (from all manipulation methods)
            manip_root = os.path.join(self.ffpp_root, "manipulated_sequences")
            if os.path.exists(manip_root):
                for method in os.listdir(manip_root):
                    video_dir = os.path.join(manip_root, method, "c23", "videos")
                    if not os.path.exists(video_dir):
                        continue
                    for f in os.listdir(video_dir):
                        if f.endswith((".mp4", ".avi", ".mov")):
                            samples.append((os.path.join(video_dir, f), 1))

        # =============== CELEB-DF V2 =================
        if self.celebdf_root and os.path.exists(self.celebdf_root):
            for subfolder, label in [("real", 0), ("fake", 1)]:
                folder_path = os.path.join(self.celebdf_root, subfolder)
                if not os.path.exists(folder_path):
                    continue
                for f in os.listdir(folder_path):
                    if not f.endswith((".mp4", ".avi", ".mov")):
                        continue
                    # Apply test split rules
                    if self.split == "test" and f not in self.test_list:
                        continue
                    if self.split != "test" and f in self.test_list:
                        continue
                    samples.append((os.path.join(folder_path, f), label))

        random.shuffle(samples)
        return samples

    def __len__(self):
        return len(self.samples)

    def __getitem__(self, idx):
        video_path, label = self.samples[idx]
        frames = self._extract_frames(video_path)

        if not frames:
            # fallback: black image tensor
            img = Image.new("RGB", (224, 224))
        else:
            img = random.choice(frames)

        if self.transform:
            img = self.transform(img)

        return img, torch.tensor(label, dtype=torch.long)

    def _extract_frames(self, video_path):
        """
        Extract frames every `frame_interval` frames.
        """
        frames = []
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            return frames

        frame_idx = 0
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            if frame_idx % self.frame_interval == 0:
                frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                frames.append(Image.fromarray(frame))
            frame_idx += 1

        cap.release()
        return frames


def get_transforms(split="train"):
    if split == "train":
        return transforms.Compose([
            transforms.Resize((224, 224)),
            transforms.RandomHorizontalFlip(),
            transforms.ColorJitter(brightness=0.2, contrast=0.2, saturation=0.2),
            transforms.ToTensor(),
            transforms.Normalize(mean=[0.485, 0.456, 0.406],
                                 std=[0.229, 0.224, 0.225]),
        ])
    else:
        return transforms.Compose([
            transforms.Resize((224, 224)),
            transforms.ToTensor(),
            transforms.Normalize(mean=[0.485, 0.456, 0.406],
                                 std=[0.229, 0.224, 0.225]),
        ])
