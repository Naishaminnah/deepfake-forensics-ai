import torch
from pytorch_pretrained_biggan import BigGAN

DEVICE = 'cuda' if torch.cuda.is_available() else 'cpu'

def load_gan(model_name='biggan-deep-256', device=DEVICE):
    """
    Loads pre-trained BigGAN model.
    """
    G = BigGAN.from_pretrained(model_name)
    G.to(device).eval()
    return G

def default_class_vector(device=DEVICE):
    """
    Returns a default one-hot class vector (e.g., golden retriever).
    """
    vec = torch.zeros((1, 1000), device=device)
    vec[0, 207] = 1.0  # Example: 207 = golden retriever
    return vec

def generate_image(G, latent_vector, class_vector=None, device=DEVICE, truncation=0.4):
    """
    Generate image from latent vector and optional class vector.
    latent_vector: torch.Tensor [1,128]
    class_vector: torch.Tensor [1,1000]
    """
    with torch.no_grad():
        z = latent_vector.to(device)
        if class_vector is None:
            class_vector = default_class_vector(device)
        img = G(z, class_vector, truncation)
        img = (img + 1)/2  # scale [-1,1] → [0,1]
    return img
