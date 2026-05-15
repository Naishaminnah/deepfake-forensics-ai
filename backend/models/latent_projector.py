import torch
from torch import nn, optim
from backend.models.reconstruction_utils import postprocess_image
from torchvision.models import vgg16
from backend.models.biggan_loader import default_class_vector

class LatentProjector:
    def __init__(self, G, device='cuda', steps=300, lr=0.05, use_perceptual=True):
        self.G = G
        self.device = device
        self.steps = steps
        self.lr = lr
        self.use_perceptual = use_perceptual

        if use_perceptual:
            self.perceptual_model = vgg16(weights='IMAGENET1K_V1').features.to(device).eval()
            for p in self.perceptual_model.parameters():
                p.requires_grad = False
            self.perceptual_loss_fn = nn.MSELoss()
        else:
            self.perceptual_loss_fn = None

    def project(self, target_tensor, class_vector=None, truncation=0.4):
        """
        Optimize latent vector to reconstruct target image.
        target_tensor: torch.Tensor [1,3,H,W], scaled [0,1]
        class_vector: optional BigGAN class vector [1,1000]
        """
        if class_vector is None:
            class_vector = default_class_vector(self.device)

        # Initialize latent vector
        z = torch.randn(1,128, device=self.device, requires_grad=True)
        optimizer = optim.Adam([z], lr=self.lr)
        loss_fn = nn.MSELoss()

        for step in range(self.steps):
            optimizer.zero_grad()
            recon = self.G(z, class_vector, truncation)
            recon = (recon + 1)/2  # [-1,1] → [0,1]
            loss = loss_fn(recon, target_tensor)
            if self.use_perceptual:
                target_features = self.perceptual_model(target_tensor)
                recon_features = self.perceptual_model(recon)
                loss += self.perceptual_loss_fn(recon_features, target_features)
            loss.backward()
            optimizer.step()
            if step % 50 == 0:
                print(f"Step [{step}/{self.steps}] Loss: {loss.item():.6f}")

        reconstructed_img = postprocess_image(recon)
        return z.detach(), reconstructed_img
