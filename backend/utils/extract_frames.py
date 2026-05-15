# extract_frames.py (robust version)

import os
import cv2
from pathlib import Path
from tqdm import tqdm
import argparse

VIDEO_EXTENSIONS = [".mp4", ".avi", ".mov"]

def find_videos_recursively(folder):
    """Return a list of all video files in folder and subfolders."""
    folder = Path(folder)
    video_files = []
    for ext in VIDEO_EXTENSIONS:
        video_files.extend(folder.rglob(f"*{ext}"))
    return video_files

def extract_frames_from_videos(video_paths, output_dir, frames_per_video=10):
    """Extract evenly spaced frames from list of videos."""
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    if len(video_paths) == 0:
        print(f"⚠️ No videos found in the given folder.")
        return

    for video_path in tqdm(video_paths, desc=f"Extracting frames"):
        cap = cv2.VideoCapture(str(video_path))
        if not cap.isOpened():
            print(f"❌ Failed to open {video_path}")
            continue

        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        if total_frames == 0:
            continue

        frame_indices = list(range(0, total_frames, max(total_frames // frames_per_video, 1)))[:frames_per_video]

        video_output_dir = output_dir / video_path.stem
        video_output_dir.mkdir(parents=True, exist_ok=True)

        for idx in frame_indices:
            cap.set(cv2.CAP_PROP_POS_FRAMES, idx)
            success, frame = cap.read()
            if not success:
                continue
            frame_name = f"{video_path.stem}_frame_{idx:04d}.jpg"
            cv2.imwrite(str(video_output_dir / frame_name), frame)

        cap.release()

def extract_all_sequences(base_dir, output_root, frames_per_video=10):
    """Extract frames from all real and fake videos recursively."""
    base_dir = Path(base_dir)
    output_root = Path(output_root)
    output_root.mkdir(parents=True, exist_ok=True)

    # ---------------- Real videos ----------------
    real_videos_root = base_dir / "original_sequences"
    real_videos = find_videos_recursively(real_videos_root)
    print(f"\n📁 Found {len(real_videos)} real videos under {real_videos_root}")
    extract_frames_from_videos(real_videos, output_root / "real", frames_per_video)

    # ---------------- Fake videos ----------------
    fake_videos_root = base_dir / "manipulated_sequences"
    fake_videos = find_videos_recursively(fake_videos_root)
    print(f"\n📁 Found {len(fake_videos)} fake videos under {fake_videos_root}")
    extract_frames_from_videos(fake_videos, output_root / "fake", frames_per_video)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Extract frames from FaceForensics++ dataset recursively.")
    parser.add_argument("--data_dir", type=str, required=True, help="Root folder of FaceForensics++ dataset")
    parser.add_argument("--output_dir", type=str, required=True, help="Folder to save extracted frames")
    parser.add_argument("--frames_per_video", type=int, default=10, help="Number of frames per video")
    args = parser.parse_args()

    extract_all_sequences(args.data_dir, args.output_dir, args.frames_per_video)
    print("\n✅ Frame extraction completed!")
