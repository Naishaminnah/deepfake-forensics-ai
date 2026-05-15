import pickle
import torch
import dnnlib
import legacy

class StyleGAN2OfficialLoader:
    def __init__(self, pkl_path, device="cuda"):
        self.device = device
        self.G = self.load_generator(pkl_path)

    def load_generator(self, pkl_path):
        print(f"Loading StyleGAN2 model from: {pkl_path}")

        with open(pkl_path, "rb") as f:
            data = pickle.load(f)

        # Some pickles contain nested dicts including G_ema
        if "G_ema" in data:
            G = data["G_ema"]
        else:
            G = data

        G = G.to(self.device)
        G.eval()
        return G
