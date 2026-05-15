# training/audio_losses.py

import torch
import torch.nn as nn
import torch.nn.functional as F

class AAMSoftmax(nn.Module):
    def __init__(self, emb_dim=192, n_classes=2, margin=0.3, scale=30):
        super().__init__()
        self.margin = margin
        self.scale = scale
        self.W = nn.Parameter(torch.randn(n_classes, emb_dim))

    def forward(self, emb, labels):
        emb = F.normalize(emb, dim=1)
        W = F.normalize(self.W, dim=1)

        logits = F.linear(emb, W)
        theta = torch.acos(torch.clamp(logits, -1 + 1e-7, 1 - 1e-7))
        target_logits = torch.cos(theta + self.margin)

        # -------- SAFE NON-INPLACE VERSION --------
        one_hot = torch.zeros_like(logits)
        one_hot.scatter_(1, labels.view(-1, 1), 1.0)

        # logits = final_logits (NO inplace)
        final_logits = logits * (1 - one_hot) + target_logits * one_hot
        # ------------------------------------------

        return final_logits * self.scale
