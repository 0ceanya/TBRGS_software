"""Centralised application configuration.

All paths and external credentials are defined here as a single source of
truth.  Values can be overridden through environment variables or a local
``.env`` file — see ``.env.example`` for the full list.

Usage::

    from src.config import settings

    path = settings.GRAPH_NPZ_PATH   # PosixPath('data/graph.npz')
"""

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Path fields below are wired into API endpoints and route finder in Task 3.
    # Until then, consumers still use the same default path strings directly.
    # ------------------------------------------------------------------ paths
    DATA_DIR: Path = Path("data")
    MODELS_DIR: Path = Path("models")
    CACHE_DIR: Path = Path("cache")
    GRAPH_NPZ_PATH: Path = Path("data/graph.npz")

    # ---------------------------------------------------- PEMS API credentials
    PEMS_API_KEY: str | None = None
    PEMS_BASE_URL: str = "https://pems.dot.ca.gov"

    # -------------------------------------------------------- prediction tuning
    PREDICTION_HORIZON_STEPS: int = 12

    # ---------------------------------- GRU / LSTM Z-score normalisation params
    FLOW_NORM_MEAN: float = 1088.8  # Z-score μ from GRU/LSTM training (PEMS-BAY Jan-Jun 2017)
    FLOW_NORM_STD: float = 156.5   # Z-score σ from GRU/LSTM training (PEMS-BAY Jan-Jun 2017)

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
