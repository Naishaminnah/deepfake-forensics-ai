# backend/models/audio_model.py

import torch
import torch.nn as nn
import torch.nn.functional as F


class SEBlock(nn.Module):
    def __init__(self, channels, reduction=16):
        super().__init__()
        self.fc1 = nn.Linear(channels, channels // reduction)
        self.fc2 = nn.Linear(channels // reduction, channels)

    def forward(self, x):
        s = torch.mean(x, dim=2)
        s = F.relu(self.fc1(s))
        s = torch.sigmoid(self.fc2(s))
        return x * s.unsqueeze(2)


class TDNNBlock(nn.Module):
    def __init__(self, in_channels, out_channels, dilation):
        super().__init__()
        self.conv = nn.Conv1d(
            in_channels, out_channels, kernel_size=3,
            dilation=dilation, padding=dilation
        )
        self.bn = nn.BatchNorm1d(out_channels)

    def forward(self, x):
        return F.relu(self.bn(self.conv(x)))


class ECAPA_TDNN(nn.Module):
    """
    Pure ECAPA embedding network.
    NO classifier.
    NO AAMSoftmax inside.
    Produces only embeddings.
    """
    def __init__(self, channels=512, emb_size=192):
        super().__init__()

        self.layer1 = TDNNBlock(80, channels, dilation=1)
        self.layer2 = TDNNBlock(channels, channels, dilation=2)
        self.layer3 = TDNNBlock(channels, channels, dilation=3)

        self.se1 = SEBlock(channels)
        self.se2 = SEBlock(channels)
        self.se3 = SEBlock(channels)

        self.conv_proj = nn.Conv1d(channels * 3, channels, kernel_size=1)

        self.stats_pool = lambda x: torch.cat(
            [torch.mean(x, dim=2), torch.std(x, dim=2)], dim=1
        )

        self.fc = nn.Linear(channels * 2, emb_size)

    def forward(self, mel):
        """
        Input: mel (B, 80, T)
        Output: embeddings (B, 192)
        """
        if mel.dim() == 4:
            mel = mel.squeeze(1)  # (B, 1, 80, T) → (B, 80, T)

        x1 = self.se1(self.layer1(mel))
        x2 = self.se2(self.layer2(x1))
        x3 = self.se3(self.layer3(x2))

        x = torch.cat([x1, x2, x3], dim=1)
        x = self.conv_proj(x)

        stats = self.stats_pool(x)
        emb = F.relu(self.fc(stats))

        return emb
