# training/audio_utils.py

import torch

def accuracy(pred, labels):
    return (pred.argmax(dim=1) == labels).float().mean().item()

def save_checkpoint(path, model, optimizer, epoch):
    torch.save({
        "epoch": epoch,
        "model_state": model.state_dict(),
        "optim_state": optimizer.state_dict()
    }, path)
