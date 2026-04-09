"""Tests for global error handling middleware."""
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from src.api.middleware import global_exception_handler


class TestGlobalExceptionHandler:
    def test_unhandled_exception_returns_json(self):
        """Unhandled exception -> 500 JSON with 'error' and 'detail' keys."""
        app = FastAPI()
        app.add_exception_handler(Exception, global_exception_handler)

        @app.get("/boom")
        async def boom():
            raise RuntimeError("something broke internally")

        with TestClient(app, raise_server_exceptions=False) as client:
            resp = client.get("/boom")

        assert resp.status_code == 500
        body = resp.json()
        assert "error" in body
        assert "detail" in body
        assert body["error"] == "InternalServerError"
        # detail should be generic -- not leak internal message
        assert "something broke internally" not in body["detail"]

    def test_error_field_is_string(self):
        """error field must be a string."""
        app = FastAPI()
        app.add_exception_handler(Exception, global_exception_handler)

        @app.get("/err")
        async def err():
            raise ValueError("bad input")

        with TestClient(app, raise_server_exceptions=False) as client:
            resp = client.get("/err")

        assert isinstance(resp.json()["error"], str)
        assert isinstance(resp.json()["detail"], str)
