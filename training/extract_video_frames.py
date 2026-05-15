import os
import cv2
from tqdm import tqdm

def extract_frames_from_video(video_path, output_dir, frame_skip=5):
    """
    Extract frames from a single video file every `frame_skip` frames.
    """
    os.makedirs(output_dir, exist_ok=True)
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        print(f"[WARN] Could not open {video_path}")
        return

    frame_idx = 0
    saved_idx = 0

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        if frame_idx % frame_skip == 0:
            frame_filename = os.path.join(output_dir, f"frame_{saved_idx:05d}.jpg")
            cv2.imwrite(frame_filename, frame)
            saved_idx += 1

        frame_idx += 1

    cap.release()


def process_dataset(dataset_root, output_root, frame_skip=5):
    """
    Process all videos in real/ and fake/ folders of dataset_root.
    """
    for label in ['real', 'fake']:
        input_dir = os.path.join(dataset_root, label)
        output_label_dir = os.path.join(output_root, label)
        os.makedirs(output_label_dir, exist_ok=True)

        if not os.path.exists(input_dir):
            print(f"[WARN] Missing folder: {input_dir}")
            continue

        videos = [v for v in os.listdir(input_dir) if v.endswith(('.mp4', '.avi', '.mov'))]
        for video_name in tqdm(videos, desc=f"Extracting frames ({label})"):
            video_path = os.path.join(input_dir, video_name)
            video_base = os.path.splitext(video_name)[0]
            output_dir = os.path.join(output_label_dir, video_base)

            if not os.path.exists(output_dir) or len(os.listdir(output_dir)) == 0:
                extract_frames_from_video(video_path, output_dir, frame_skip)
            else:
                print(f"[SKIP] Frames already exist for {video_name}")


if __name__ == "__main__":
    dataset_root = r"D:\deepfake_forensics_ai\datasets\celeb_df_v2"
    output_root = dataset_root  # same folder, creates subfolders inside
    frame_skip = 5  # extract 1 frame every 5

    print(f"[INFO] Extracting frames from videos in: {dataset_root}")
    process_dataset(dataset_root, output_root, frame_skip)
    print("\n✅ Frame extraction complete!")
