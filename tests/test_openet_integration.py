from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from helios.utils.openet import fetch_monthly_et


def test_fetch_returns_list(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPENET_API_KEY", "test-key")

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = [
        {"time": "2023-04-01", "et": 42},
        {"time": "2023-05-01", "et": 91},
    ]

    with patch("helios.utils.openet.requests.post", return_value=mock_response):
        result = fetch_monthly_et(-114.45, 43.60, "2023-04-01", "2023-05-31")

    assert isinstance(result, list)
    assert len(result) == 2
    assert result[0]["et"] == 42


def test_fetch_raises_on_http_error(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPENET_API_KEY", "test-key")

    mock_response = MagicMock()
    mock_response.status_code = 401
    mock_response.text = "Unauthorized"

    with patch("helios.utils.openet.requests.post", return_value=mock_response):
        with pytest.raises(RuntimeError):
            fetch_monthly_et(-114.45, 43.60, "2023-04-01", "2023-05-31")


def test_fetch_raises_on_missing_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("OPENET_API_KEY", raising=False)

    with pytest.raises(RuntimeError):
        fetch_monthly_et(-114.45, 43.60, "2023-04-01", "2023-05-31")
