"""GRU encoder-decoder model for traffic flow prediction."""
import torch
import torch.nn as nn


class GRUTrafficPredictor(nn.Module):
    """2-layer GRU encoder-decoder with attention for per-node traffic prediction.

    Input:  (N, 12, 3) -- N sensors, 12 historical timesteps, 3 features
    Output: (N, 12, 1) -- 12 future flow predictions per sensor
    """

    def __init__(self) -> None:
        super().__init__()
        self.encoder_gru = nn.GRU(3, 128, num_layers=2, batch_first=True)
        self.decoder_gru = nn.GRU(128, 128, num_layers=2, batch_first=True)
        self.attention = nn.Linear(128, 1)
        self.fc_out = nn.Sequential(
            nn.Linear(128, 128),
            nn.ReLU(),
            nn.Dropout(0.2),
            nn.Linear(128, 1),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        # x: (N, 12, 3)
        # 1. Encode input sequence
        encoder_out, h_n = self.encoder_gru(x)  # (N,12,128), (2,N,128)

        # 2. Attention over encoder outputs
        scores = self.attention(encoder_out)  # (N, 12, 1)
        weights = torch.softmax(scores, dim=1)  # (N, 12, 1)
        context = (encoder_out * weights).sum(dim=1, keepdim=True)  # (N,1,128)

        # 3. Decode: feed context repeated 12 times, init with encoder hidden
        decoder_in = context.expand(-1, 12, -1)  # (N, 12, 128)
        decoder_out, _ = self.decoder_gru(decoder_in, h_n)  # (N, 12, 128)

        # 4. Project to flow predictions
        return self.fc_out(decoder_out)  # (N, 12, 1)
