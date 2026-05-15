import cv2
import os
import numpy as np
from pathlib import Path


def extract_frames_from_video(video_path, output_dir=None, frame_skip=5, resize=(224, 224)):
    """
    Extracts frames from a video at regular intervals.

    Args:
        video_path (str): Path to the input video file.
        output_dir (str, optional): Folder to save extracted frames. Defaults to None (in-memory only).
        frame_skip (int): Extract one frame every `frame_skip` frames.
        resize (tuple): Resize each frame to (width, height).

    Returns:
        List[np.ndarray]: List of extracted frame arrays (RGB).
    """
    frames = []
    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        raise RuntimeError(f"❌ Failed to open video: {video_path}")

    frame_idx = 0
    os.makedirs(output_dir, exist_ok=True) if output_dir else None

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        if frame_idx % frame_skip == 0:
            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            frame = cv2.resize(frame, resize)
            frames.append(frame)

            if output_dir:
                frame_path = Path(output_dir) / f"frame_{frame_idx:05d}.jpg"
                cv2.imwrite(str(frame_path), cv2.cvtColor(frame, cv2.COLOR_RGB2BGR))

        frame_idx += 1

    cap.release()
    return frames
