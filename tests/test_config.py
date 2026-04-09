"""Tests for Settings configuration (TC-13)."""
import os
import pytest
from src.config import Settings


class TestSettings:
    def test_default_graph_path(self):
        s = Settings()
        assert str(s.GRAPH_NPZ_PATH) == "data/graph.npz"

    def test_default_pems_api_key_is_none(self):
        s = Settings()
        assert s.PEMS_API_KEY is None

    def test_env_var_override(self, monkeypatch):
        monkeypatch.setenv("PEMS_API_KEY", "test-key-123")
        s = Settings()
        assert s.PEMS_API_KEY == "test-key-123"

    def test_flow_norm_constants(self):
        s = Settings()
        assert s.FLOW_NORM_MEAN == pytest.approx(1088.8)
        assert s.FLOW_NORM_STD == pytest.approx(156.5)

    def test_horizon_steps_default(self):
        s = Settings()
        assert s.PREDICTION_HORIZON_STEPS == 12

    def test_extra_env_vars_ignored(self, monkeypatch):
        monkeypatch.setenv("COMPLETELY_UNKNOWN_VAR", "should_be_ignored")
        # Should not raise
        s = Settings()
        assert not hasattr(s, "COMPLETELY_UNKNOWN_VAR")
