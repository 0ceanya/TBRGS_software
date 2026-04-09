"""FastAPI dependency functions for shared app state."""
from __future__ import annotations

from fastapi import Request

from src.data.pems_client import PEMSClient


def get_npz_data(request: Request) -> dict:
    """Inject pre-loaded graph data from lifespan."""
    return request.app.state.npz_data


def get_pems_client(request: Request) -> PEMSClient:
    """Inject the PEMS API client from lifespan."""
    return request.app.state.pems_client


def get_providers(request: Request) -> dict:
    """Inject the shared provider registry from lifespan."""
    return request.app.state.providers
