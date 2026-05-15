import os
import torch
import torch.nn as nn


# ============================================
# 1️⃣ LSTM Temporal Model
# ============================================
class LSTMTemporal(nn.Module):
    def __init__(self, input_dim=1792, hidden_dim=512, num_layers=2, dropout=0.3):
        super(LSTMTemporal, self).__init__()
        self.lstm = nn.LSTM(
            input_dim,
            hidden_dim,
            num_layers=num_layers,
            batch_first=True,
            bidirectional=True,
            dropout=dropout,
        )
        self.fc = nn.Linear(hidden_dim * 2, 2)  # [real, fake]
        self.softmax = nn.Softmax(dim=1)

    def forward(self, x):
        # x: (B, T, E)
        lstm_out, _ = self.lstm(x)
        pooled = torch.mean(lstm_out, dim=1)
        out = self.fc(pooled)
        return self.softmax(out)


# ============================================
# 2️⃣ Transformer Temporal Model
# ============================================
class TransformerTemporal(nn.Module):
    def __init__(self, embed_dim=1792, num_heads=8, num_layers=4, dropout=0.1):
        super(TransformerTemporal, self).__init__()
        encoder_layer = nn.TransformerEncoderLayer(
            d_model=embed_dim,
            nhead=num_heads,
            dim_feedforward=7168,
            dropout=dropout,
            activation="gelu",
            batch_first=True,
        )
        self.transformer = nn.TransformerEncoder(encoder_layer, num_layers=num_layers)
        self.fc = nn.Linear(embed_dim, 2)
        self.softmax = nn.Softmax(dim=1)

    def forward(self, x):
        # x: (B, T, E)
        x = self.transformer(x)
        pooled = torch.mean(x, dim=1)
        out = self.fc(pooled)
        return self.softmax(out)


# ============================================
# 3️⃣ Loader Utility for Temporal Models
# ============================================
def load_temporal_model(model_type="lstm", model_path=None, device="cpu"):
    """
    Load a temporal model (LSTM or Transformer) safely.

    Args:
        model_type (str): "lstm" or "transformer"
        model_path (str): Path to .pth checkpoint
        device (torch.device): Device to load model onto
    """
    print(f"[INFO] Loading {model_type.upper()} temporal model from {model_path}")

    # --- Instantiate the correct architecture
    if model_type.lower() == "lstm":
        model = LSTMTemporal(input_dim=1792, hidden_dim=512, num_layers=2, dropout=0.3).to(device)
    elif model_type.lower() == "transformer":
        model = TransformerTemporal(embed_dim=1792, num_heads=8, num_layers=4, dropout=0.1).to(device)
    else:
        raise ValueError(f"❌ Unknown model type: {model_type}")

    # --- Load checkpoint safely
    if model_path and os.path.exists(model_path):
        ckpt = torch.load(model_path, map_location=device)

        # Try to read model type if saved inside the checkpoint
        if isinstance(ckpt, dict) and "model_type" in ckpt:
            ckpt_model_type = ckpt["model_type"]
            if ckpt_model_type.lower() != model_type.lower():
                print(f"[WARN] Checkpoint was trained as {ckpt_model_type}, overriding to that type.")
                if ckpt_model_type.lower() == "transformer":
                    model = TransformerTemporal(embed_dim=1792).to(device)
                else:
                    model = LSTMTemporal(input_dim=1792).to(device)

        state_dict = ckpt["model_state_dict"] if "model_state_dict" in ckpt else ckpt
        missing, unexpected = model.load_state_dict(state_dict, strict=False)
        if missing or unexpected:
            print(f"[WARN] Ignored mismatched keys: missing={missing}, unexpected={unexpected}")
        print(f"[OK] {model_type.upper()} model loaded successfully.")
    else:
        print(f"[WARN] No checkpoint found at {model_path}. Using random weights.")

    model.eval()
    return model
