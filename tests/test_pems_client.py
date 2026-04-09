"""Tests for PEMSClient (TC-13)."""
import numpy as np
import pytest
from src.data import PEMSClient, PEMSUnavailableError


class TestPEMSClientConfiguration:
    def test_is_configured_false_when_no_key(self):
        client = PEMSClient(api_key=None)
        assert client.is_configured() is False

    def test_is_configured_true_when_key_set(self):
        client = PEMSClient(api_key="test-key")
        assert client.is_configured() is True


class TestFetchRecentReadings:
    def test_raises_when_not_configured(self):
        client = PEMSClient(api_key=None)
        with pytest.raises(PEMSUnavailableError):
            client.fetch_recent_readings(["400001"])

    def test_returns_correct_shape(self):
        client = PEMSClient(api_key="test-key")
        result = client.fetch_recent_readings(["400001", "400002"], steps=5)
        assert set(result.keys()) == {"400001", "400002"}
        for arr in result.values():
            assert arr.shape == (5, 3)

    def test_flow_in_valid_range(self):
        client = PEMSClient(api_key="test-key")
        result = client.fetch_recent_readings(["400001"], steps=12)
        flow_col = result["400001"][:, 0]
        assert (flow_col >= 200).all() and (flow_col <= 1500).all()

    def test_speed_in_valid_range(self):
        client = PEMSClient(api_key="test-key")
        result = client.fetch_recent_readings(["400001"], steps=12)
        speed_col = result["400001"][:, 1]
        assert (speed_col >= 20).all() and (speed_col <= 85).all()

    def test_time_of_day_in_valid_range(self):
        client = PEMSClient(api_key="test-key")
        result = client.fetch_recent_readings(["400001"], steps=12)
        tod_col = result["400001"][:, 2]
        assert (tod_col >= 0.0).all() and (tod_col < 1.0).all()

    def test_empty_sensor_ids_returns_empty_dict(self):
        client = PEMSClient(api_key="test-key")
        result = client.fetch_recent_readings([], steps=5)
        assert result == {}

    def test_raises_value_error_for_zero_steps(self):
        client = PEMSClient(api_key="test-key")
        with pytest.raises(ValueError, match="steps must be a positive integer"):
            client.fetch_recent_readings(["400001"], steps=0)

    def test_raises_value_error_for_negative_steps(self):
        client = PEMSClient(api_key="test-key")
        with pytest.raises(ValueError, match="steps must be a positive integer"):
            client.fetch_recent_readings(["400001"], steps=-1)


class TestLocalMode:
    """Tests for graph.npz-backed local data mode (no API key needed)."""

    NPZ_PATH = "data/graph.npz"

    def test_is_configured_with_npz_and_no_key(self):
        client = PEMSClient(api_key=None, npz_path=self.NPZ_PATH)
        assert client.is_configured() is True

    def test_returns_correct_shape(self):
        client = PEMSClient(api_key=None, npz_path=self.NPZ_PATH)
        result = client.fetch_recent_readings(["400001", "400017"], steps=5)
        assert set(result.keys()) == {"400001", "400017"}
        for arr in result.values():
            assert arr.shape == (5, 3)

    def test_flow_in_valid_range(self):
        client = PEMSClient(api_key=None, npz_path=self.NPZ_PATH)
        result = client.fetch_recent_readings(["400001"], steps=12)
        flow = result["400001"][:, 0]
        assert (flow >= 200).all() and (flow <= 1500).all()

    def test_speed_in_valid_range(self):
        client = PEMSClient(api_key=None, npz_path=self.NPZ_PATH)
        result = client.fetch_recent_readings(["400001"], steps=12)
        speed = result["400001"][:, 1]
        assert (speed >= 20).all() and (speed <= 85).all()

    def test_no_api_key_no_npz_raises(self):
        client = PEMSClient(api_key=None, npz_path=None)
        with pytest.raises(PEMSUnavailableError):
            client.fetch_recent_readings(["400001"])
