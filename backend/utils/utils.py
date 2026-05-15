import torch
import os
import random
import numpy as np
from typing import Any, Dict, Optional

def set_seed(seed: int = 42) -> None:
    """Set all random seeds for reproducibility."""
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    torch.cuda.manual_seed_all(seed)
    torch.backends.cudnn.deterministic = True
    torch.backends.cudnn.benchmark = False

def save_checkpoint(obj: Any, path: str, **extra: Any) -> None:
    """
    Save model or any object safely to disk.
    
    Args:
        obj: The main object to save (typically a model or state dict).
        path: File path to save checkpoint.
        extra: Optional extra objects to include in checkpoint (dict-like).
    """
    os.makedirs(os.path.dirname(path), exist_ok=True)
    
    if isinstance(obj, torch.nn.Module):
        checkpoint = {"model_state_dict": obj.state_dict()}
    elif isinstance(obj, dict):
        checkpoint = obj
    else:
        checkpoint = {"obj": obj}
    
    checkpoint.update(extra)
    torch.save(checkpoint, path)
    print(f"[INFO] Checkpoint saved at {path}")

def count_parameters(model: torch.nn.Module) -> int:
    """Return the number of trainable parameters in the model."""
    return sum(p.numel() for p in model.parameters() if p.requires_grad)
