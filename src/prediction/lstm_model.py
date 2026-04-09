"""LSTM model for per-node traffic flow prediction."""
import torch
import torch.nn as nn


class LSTM_Deep(nn.Module):
    """2-layer LSTM for per-node traffic prediction.

    Input:  (N, 12, 3) -- N sensors, 12 historical timesteps, 3 features
    Output: (N, 12, 1) -- 12 future flow predictions per sensor
    """

    def __init__(self) -> None:
        super().__init__()
        self.lstm = nn.LSTM(3, 128, num_layers=2, batch_first=True)
        self.fc = nn.Linear(128, 12)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        # x: (N, 12, 3)
        out, _ = self.lstm(x)  # (N, 12, 128)
        out = out[:, -1, :]  # (N, 128) -- last timestep only
        out = self.fc(out)  # (N, 12)
        return out.unsqueeze(-1)  # (N, 12, 1)
