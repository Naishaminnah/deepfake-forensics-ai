# training/features.py
import os
import numpy as np
import librosa
import soundfile as sf
from scipy.fftpack import dct
from tqdm import tqdm
import pandas as pd

# ==============================
# CONFIG
# ==============================
SAMPLE_RATE = 16000
N_LFCC = 20
N_LIN_FILTERS = 40
N_MELS = 40
N_FFT = 512
HOP_LENGTH = 160
N_CQT = 84

# ==============================
# FEATURE FUNCTIONS
# ==============================
def compute_lfcc(signal, sr=SAMPLE_RATE, n_fft=N_FFT, hop_length=HOP_LENGTH, n_lfcc=N_LFCC, n_filters=N_LIN_FILTERS):
    """Compute LFCC features using librosa + DCT"""
    S = np.abs(librosa.stft(signal, n_fft=n_fft, hop_length=hop_length))**2
    # Linear filter bank
    lin_filters = librosa.filters.linear(n_filters, S.shape[0])
    lin_spec = np.dot(lin_filters, S)
    # Log
    lin_spec = np.log(np.maximum(lin_spec, 1e-10))
    # DCT
    lfcc = dct(lin_spec, type=2, axis=0, norm='ortho')[:n_lfcc]
    return lfcc.T  # time x n_lfcc

def compute_logmel(signal, sr=SAMPLE_RATE, n_mels=N_MELS, n_fft=N_FFT, hop_length=HOP_LENGTH):
    mel = librosa.feature.melspectrogram(signal, sr=sr, n_fft=n_fft, hop_length=hop_length, n_mels=n_mels)
    logmel = np.log(np.maximum(mel, 1e-10))
    delta = librosa.feature.delta(logmel)
    delta2 = librosa.feature.delta(logmel, order=2)
    return np.stack([logmel, delta, delta2], axis=0)  # 3 x n_mels x t

def compute_cqt(signal, sr=SAMPLE_RATE, n_bins=N_CQT, hop_length=HOP_LENGTH):
    cqt = np.abs(librosa.cqt(signal, sr=sr, hop_length=hop_length, n_bins=n_bins))
    return np.log(np.maximum(cqt, 1e-10))[np.newaxis, :, :]  # 1 x n_bins x t

# ==============================
# MAIN FEATURE EXTRACTION
# ==============================
def extract_features(file_path):
    try:
        y, sr = sf.read(file_path)
        if sr != SAMPLE_RATE:
            y = librosa.resample(y, orig_sr=sr, target_sr=SAMPLE_RATE)
        # Features
        lfcc = compute_lfcc(y)
        logmel = compute_logmel(y)
        cqt = compute_cqt(y)
        # Stack all features (channels x time x feature_dim)
        # Ensure matching time dimension by trimming/padding
        min_frames = min(lfcc.shape[0], logmel.shape[2], cqt.shape[2])
        lfcc = lfcc[:min_frames, :]
        logmel = logmel[:, :, :min_frames]
        cqt = cqt[:, :, :min_frames]
        features = np.concatenate([lfcc.transpose(1,0)[np.newaxis,:,:], logmel, cqt], axis=0)
        return features.astype(np.float32)
    except Exception as e:
        print(f"[ERROR] {file_path} -> {e}")
        return None

# ==============================
# LOAD LABELS
# ==============================
def load_labels(protocol_path, subset='train'):
    """
    protocol_path: path to LA_cm_protocols/ASVspoof2019.LA.cm.train.trn.txt
    """
    df = pd.read_csv(protocol_path, sep=' ', header=None, names=['file', 'spoof_type', 'label'])
    labels_dict = {row['file']: 1 if row['label']=='spoof' else 0 for _, row in df.iterrows()}
    return labels_dict

# ==============================
# RUN EXTRACTION
# ==============================
def process_dataset(dataset_dir, protocol_file, out_file):
    """
    dataset_dir: folder with audio files
    protocol_file: train/dev/val protocol
    out_file: path to save features npz
    """
    labels_dict = load_labels(protocol_file)
    X, y = [], []

    audio_files = [os.path.join(dataset_dir, f) for f in os.listdir(dataset_dir) if f.endswith('.flac')]
    for f in tqdm(audio_files, desc=os.path.basename(dataset_dir)):
        feats = extract_features(f)
        if feats is not None:
            X.append(feats)
            fname = os.path.basename(f)
            y.append(labels_dict.get(fname, 0))  # default 0 if not found

    X = np.array(X, dtype=np.float32)
    y = np.array(y, dtype=np.int64)
    np.savez_compressed(out_file, X=X, y=y)
    print(f"Saved features → {out_file}")

# ==============================
# EXAMPLE USAGE
# ==============================
if __name__ == "__main__":
    BASE_DIR = r"D:\deepfake_forensics_ai\audio_data\ASVspoof2019\LA\ASVspoof2019_LA_train\flac"
    PROTOCOL = r"D:\deepfake_forensics_ai\audio_data\ASVspoof2019\LA\ASVspoof2019_LA_cm_protocols\ASVspoof2019.LA.cm.train.trn.txt"
    OUT_FILE = r"D:\deepfake_forensics_ai\audio_data\ASVspoof2019\features_ensemble\train_features.npz"

    os.makedirs(os.path.dirname(OUT_FILE), exist_ok=True)
    process_dataset(BASE_DIR, PROTOCOL, OUT_FILE)
