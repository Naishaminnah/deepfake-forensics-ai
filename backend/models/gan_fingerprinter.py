import torch
import torch.nn as nn
import torch.nn.functional as F

class SEBlock(nn.Module):
    def __init__(self, c, r=16):
        super().__init__()
        self.fc1 = nn.Linear(c, c // r)
        self.fc2 = nn.Linear(c // r, c)

    def forward(self, x):
        b, c, _, _ = x.shape
        y = F.adaptive_avg_pool2d(x, 1).view(b, c)
        y = F.relu(self.fc1(y))
        y = torch.sigmoid(self.fc2(y)).view(b, c, 1, 1)
        return x * y


class ResidualBlock(nn.Module):
    def __init__(self, c):
        super().__init__()
        self.conv1 = nn.Conv2d(c, c, 3, padding=1)
        self.conv2 = nn.Conv2d(c, c, 3, padding=1)
        self.se = SEBlock(c)

    def forward(self, x):
        out = F.relu(self.conv1(x))
        out = self.conv2(out)
        out = self.se(out)
        return F.relu(out + x)


class GANFingerprinter(nn.Module):
    def __init__(self, num_classes):
        super().__init__()

        self.hpf = nn.Conv2d(3, 3, kernel_size=3, padding=1, bias=False)
        self.hpf.weight.data = torch.tensor(
            [[[[-1, -1, -1], 
               [-1,  8, -1],
               [-1, -1, -1]]]] * 3,
            dtype=torch.float
        )

        self.features = nn.Sequential(
            nn.Conv2d(3, 32, 3, padding=1),
            ResidualBlock(32),
            nn.MaxPool2d(2),

            nn.Conv2d(32, 64, 3, padding=1),
            ResidualBlock(64),
            nn.MaxPool2d(2),

            nn.Conv2d(64, 128, 3, padding=1),
            ResidualBlock(128),
            ResidualBlock(128),
            nn.AdaptiveAvgPool2d(1)
        )

        self.classifier = nn.Linear(128, num_classes)

    def forward(self, x):
        x = self.hpf(x)
        x = self.features(x)
        x = x.view(x.size(0), -1)
        return self.classifier(x)
