import torch
from torchvision import transforms
from PIL import Image

def preprocess_image(img, image_size=256):
    """
    PIL Image → torch tensor [1,3,H,W], scaled [0,1]
    """
    transform = transforms.Compose([
        transforms.Resize((image_size,image_size)),
        transforms.ToTensor()
    ])
    if isinstance(img, Image.Image):
        return transform(img).unsqueeze(0)
    elif isinstance(img, torch.Tensor):
        return img.unsqueeze(0) if img.dim() == 3 else img
    else:
        raise TypeError("Input must be PIL Image or torch.Tensor")

def postprocess_image(tensor):
    """
    torch.Tensor [1,3,H,W], [0,1] → PIL Image
    """
    tensor = tensor.squeeze(0).cpu().clamp(0,1)
    return transforms.ToPILImage()(tensor)
