"""DCRNN model for spatial-temporal traffic flow prediction.

Uses Diffusion Convolutional GRU cells operating over the sensor graph.
"""
from __future__ import annotations

import numpy as np
import torch
import torch.nn as nn


class DCGRUCell(nn.Module):
    """Diffusion Convolutional GRU Cell.

    Parameters are named with their shapes to match the checkpoint format.
    """

    def __init__(
        self, input_size: int, hidden_size: int, num_diffusion_steps: int = 3
    ) -> None:
        super().__init__()
        self.hidden_size = hidden_size
        self.num_diffusion_steps = num_diffusion_steps

        in_channels = (input_size + hidden_size) * num_diffusion_steps
        # Gate weights (update + reset combined -> 2*hidden)
        gate_in = in_channels
        gate_out = 2 * hidden_size
        self.register_parameter(
            f"gconv_weight_({gate_in}, {gate_out})",
            nn.Parameter(torch.empty(gate_in, gate_out)),
        )
        self.register_parameter(
            f"gconv_biases_{gate_out}",
            nn.Parameter(torch.zeros(gate_out)),
        )
        # Candidate weight (new gate -> hidden)
        cand_out = hidden_size
        self.register_parameter(
            f"gconv_weight_({gate_in}, {cand_out})",
            nn.Parameter(torch.empty(gate_in, cand_out)),
        )
        self.register_parameter(
            f"gconv_biases_{cand_out}",
            nn.Parameter(torch.zeros(cand_out)),
        )
        # Store key names for forward pass
        self._gate_w_key = f"gconv_weight_({gate_in}, {gate_out})"
        self._gate_b_key = f"gconv_biases_{gate_out}"
        self._cand_w_key = f"gconv_weight_({gate_in}, {cand_out})"
        self._cand_b_key = f"gconv_biases_{cand_out}"

    def _graph_conv(
        self,
        inputs: torch.Tensor,
        hidden: torch.Tensor,
        diff_matrices: list[torch.Tensor],
        weight_key: str,
        bias_key: str,
    ) -> torch.Tensor:
        """Apply diffusion graph convolution."""
        xh = torch.cat([inputs, hidden], dim=-1)  # (N, in+hidden)
        diffused = []
        for A in diff_matrices:
            diffused.append(A @ xh)  # (N, in+hidden)
        stacked = torch.cat(diffused, dim=-1)  # (N, (in+hidden)*steps)
        W = self._parameters[weight_key]
        b = self._parameters[bias_key]
        return stacked @ W + b

    def forward(
        self,
        inputs: torch.Tensor,
        hidden: torch.Tensor,
        diff_matrices: list[torch.Tensor],
    ) -> torch.Tensor:
        """Return new hidden state."""
        gates = self._graph_conv(
            inputs, hidden, diff_matrices, self._gate_w_key, self._gate_b_key
        )
        r, u = torch.chunk(torch.sigmoid(gates), 2, dim=-1)  # (N,H) each

        candidate = self._graph_conv(
            inputs, r * hidden, diff_matrices, self._cand_w_key, self._cand_b_key
        )
        c = torch.tanh(candidate)

        return u * hidden + (1 - u) * c  # (N, hidden_size)


class DCGRUEncoder(nn.Module):
    """Encoder stack of DCGRUCell layers."""

    def __init__(
        self, input_size: int, hidden_size: int, num_layers: int, K: int = 2
    ) -> None:
        super().__init__()
        sizes = [input_size] + [hidden_size] * (num_layers - 1)
        self.dcgru_layers = nn.ModuleList(
            [
                DCGRUCell(sizes[i], hidden_size, num_diffusion_steps=K + 1)
                for i in range(num_layers)
            ]
        )
        self.hidden_size = hidden_size
        self.num_layers = num_layers

    def forward(self, x: torch.Tensor, diff_matrices: list) -> torch.Tensor:
        # x: (N, T, input_size)
        N, T, _ = x.shape
        hiddens = [
            torch.zeros(N, self.hidden_size, device=x.device)
            for _ in range(self.num_layers)
        ]
        for t in range(T):
            inp = x[:, t, :]
            for layer_idx, cell in enumerate(self.dcgru_layers):
                hiddens[layer_idx] = cell(inp, hiddens[layer_idx], diff_matrices)
                inp = hiddens[layer_idx]
        return hiddens[-1]  # (N, hidden_size) -- final hidden of last layer


class DCGRUDecoder(nn.Module):
    """Decoder stack of DCGRUCell layers with autoregressive projection."""

    def __init__(
        self, output_size: int, hidden_size: int, num_layers: int, K: int = 2
    ) -> None:
        super().__init__()
        sizes = [output_size] + [hidden_size] * (num_layers - 1)
        self.dcgru_layers = nn.ModuleList(
            [
                DCGRUCell(sizes[i], hidden_size, num_diffusion_steps=K + 1)
                for i in range(num_layers)
            ]
        )
        self.projection_layer = nn.Linear(hidden_size, output_size)
        self.hidden_size = hidden_size
        self.num_layers = num_layers

    def forward(
        self,
        encoder_hidden: torch.Tensor,
        horizon: int,
        diff_matrices: list,
    ) -> torch.Tensor:
        """Autoregressively decode for ``horizon`` steps."""
        N = encoder_hidden.shape[0]
        hiddens = [encoder_hidden] + [
            torch.zeros(N, self.hidden_size, device=encoder_hidden.device)
            for _ in range(self.num_layers - 1)
        ]
        # Start token: zeros (no teacher forcing at inference)
        decoder_input = torch.zeros(N, 1, device=encoder_hidden.device)
        outputs = []
        for _ in range(horizon):
            inp = decoder_input
            for layer_idx, cell in enumerate(self.dcgru_layers):
                hiddens[layer_idx] = cell(inp, hiddens[layer_idx], diff_matrices)
                inp = hiddens[layer_idx]
            pred = self.projection_layer(hiddens[-1])  # (N, 1)
            outputs.append(pred)
            decoder_input = pred
        return torch.stack(outputs, dim=1)  # (N, horizon, 1)


class DCRNNModel(nn.Module):
    """Diffusion Convolutional RNN for traffic prediction.

    Input:  (N, 12, 3) -- N sensors, 12 historical steps, 3 features
            diff_matrices: list of diffusion operator tensors (K+1 matrices of shape NxN)
    Output: (N, horizon, 1)
    """

    def __init__(self, num_nodes: int = 325, K: int = 2) -> None:
        super().__init__()
        self.encoder_model = DCGRUEncoder(
            input_size=3, hidden_size=128, num_layers=2, K=K
        )
        self.decoder_model = DCGRUDecoder(
            output_size=1, hidden_size=128, num_layers=2, K=K
        )

    def forward(
        self,
        x: torch.Tensor,
        diff_matrices: list,
        horizon: int = 12,
    ) -> torch.Tensor:
        encoder_hidden = self.encoder_model(x, diff_matrices)  # (N, 128)
        return self.decoder_model(
            encoder_hidden, horizon, diff_matrices
        )  # (N, 12, 1)


def compute_diffusion_matrices(adj: np.ndarray, K: int = 2) -> list:
    """Compute K+1 diffusion operator matrices from the adjacency matrix.

    Returns [I, D^{-1}W, (D^{-1}W)^2, ...] as numpy arrays.
    """
    N = adj.shape[0]
    # Row-normalize: D^{-1} W
    row_sum = np.array(adj.sum(axis=1)).flatten()
    row_sum[row_sum == 0] = 1.0  # avoid division by zero
    D_inv = np.diag(1.0 / row_sum)
    A = D_inv @ adj

    matrices = [np.eye(N)]  # A^0 = I
    A_pow = A.copy()
    for _ in range(K):
        matrices.append(A_pow)
        A_pow = A_pow @ A
    return matrices
