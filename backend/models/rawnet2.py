import torch
import torch.nn as nn
import torch.nn.functional as F


# =====================================
# 🔧 SincConv (Fully Fixed)
# =====================================
class SincConv(nn.Module):
    def __init__(self, out_channels, kernel_size, sample_rate=16000):
        super().__init__()
        self.out_channels = out_channels
        self.kernel_size = kernel_size
        self.sample_rate = sample_rate

        # enforce odd kernel size
        if kernel_size % 2 == 0:
            kernel_size += 1
        self.kernel_size = kernel_size

        # mel scale filter init
        low_mel = self._mel(80)
        high_mel = self._mel(7600)
        mel = torch.linspace(low_mel, high_mel, out_channels + 1)
        hz = self._mel_inv(mel)

        self.low_hz_ = nn.Parameter(hz[:-1].view(-1, 1))
        self.band_hz_ = nn.Parameter((hz[1:] - hz[:-1]).view(-1, 1))

        # central symmetric axis
        n = torch.arange(-(self.kernel_size // 2), (self.kernel_size // 2) + 1)
        self.register_buffer("n_", n / self.sample_rate)

        # use Hamming window of exact kernel_size length
        self.register_buffer("window_", torch.hamming_window(self.kernel_size))

    def _mel(self, hz):
        return 2595 * torch.log10(torch.tensor(1 + hz / 700.0))

    def _mel_inv(self, mel):
        return 700 * (10 ** (mel / 2595) - 1)

    def forward(self, x):
        device = x.device
        n = self.n_.to(device)
        window = self.window_.to(device)

        low = torch.abs(self.low_hz_) + 50
        high = torch.clamp(low + torch.abs(self.band_hz_), 50, self.sample_rate / 2)

        filters = []
        for i in range(self.out_channels):
            f_low = low[i]
            f_high = high[i]

            sinc_low = 2 * f_low * torch.sinc(2 * f_low * n)
            sinc_high = 2 * f_high * torch.sinc(2 * f_high * n)
            band_pass = sinc_high - sinc_low

            # ensure same size as window
            if band_pass.shape[0] != window.shape[0]:
                min_len = min(band_pass.shape[0], window.shape[0])
                band_pass = band_pass[:min_len]
                window = window[:min_len]

            band_pass = band_pass * window
            band_pass = band_pass / torch.max(torch.abs(band_pass))
            filters.append(band_pass)

        filters = torch.stack(filters).view(self.out_channels, 1, -1)
        return F.conv1d(x, filters, stride=1, padding=self.kernel_size // 2)


# =====================================
# 🔩 Residual Block
# =====================================
class ResidualBlock(nn.Module):
    def __init__(self, in_ch, out_ch, downsample=False):
        super().__init__()
        stride = 2 if downsample else 1
        self.conv1 = nn.Conv1d(in_ch, out_ch, 3, stride=stride, padding=1)
        self.bn1 = nn.BatchNorm1d(out_ch)
        self.conv2 = nn.Conv1d(out_ch, out_ch, 3, padding=1)
        self.bn2 = nn.BatchNorm1d(out_ch)
        self.skip = nn.Conv1d(in_ch, out_ch, 1, stride=stride) if downsample else None

    def forward(self, x):
        out = F.relu(self.bn1(self.conv1(x)))
        out = self.bn2(self.conv2(out))
        res = self.skip(x) if self.skip is not None else x
        return F.relu(out + res)


# =====================================
# 🧠 RawNet2 Model
# =====================================
class RawNet2(nn.Module):
    def __init__(self, num_classes=1):
        super().__init__()
        self.sinc = SincConv(out_channels=64, kernel_size=251)
        self.layer1 = ResidualBlock(64, 128, downsample=True)
        self.layer2 = ResidualBlock(128, 256, downsample=True)
        self.layer3 = ResidualBlock(256, 256)
        self.pool = nn.AdaptiveAvgPool1d(1)
        self.fc = nn.Sequential(
            nn.Linear(256, 64),
            nn.ReLU(),
            nn.Linear(64, num_classes),
            nn.Sigmoid()
        )

    def forward(self, x):
        x = self.sinc(x)
        x = self.layer1(x)
        x = self.layer2(x)
        x = self.layer3(x)
        x = self.pool(x).squeeze(-1)
        return self.fc(x)
