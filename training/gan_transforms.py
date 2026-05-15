from torchvision import transforms

train_transform = transforms.Compose([
    transforms.Grayscale(num_output_channels=1),   # <-- ADD THIS
    transforms.Resize((224, 224)),
    transforms.ToTensor(),
])

test_transform = transforms.Compose([
    transforms.Grayscale(num_output_channels=1),   # <-- ADD THIS
    transforms.Resize((224, 224)),
    transforms.ToTensor(),
])
