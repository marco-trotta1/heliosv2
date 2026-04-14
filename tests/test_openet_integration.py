from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest

from helios.utils.openet import clear_openet_cache, fetch_monthly_et, resolve_monthly_et_in


@pytest.fixture(autouse=True)
def clear_cache() -> None:
    clear_openet_cache()


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


def test_resolve_monthly_et_in_uses_live_openet_and_cache(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPENET_API_KEY", "test-key")

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = [{"time": "2024-07-01", "et": 85.0}]

    with patch("helios.utils.openet.requests.post", return_value=mock_response) as mocked_post:
        first_value, first_source = resolve_monthly_et_in(
            longitude=-114.45,
            latitude=43.60,
            observed_at=datetime(2024, 7, 18, tzinfo=timezone.utc),
        )
        second_value, second_source = resolve_monthly_et_in(
            longitude=-114.4502,
            latitude=43.6002,
            observed_at=datetime(2024, 7, 22, tzinfo=timezone.utc),
        )

    assert first_source == "openet-live"
    assert second_source == "openet-cache"
    assert first_value == second_value
    assert mocked_post.call_count == 1


def test_resolve_monthly_et_in_falls_back_when_key_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("OPENET_API_KEY", raising=False)

    value, source = resolve_monthly_et_in(
        longitude=-114.45,
        latitude=43.60,
        observed_at=datetime(2024, 8, 5, tzinfo=timezone.utc),
    )

    assert source == "openet-fallback"
    assert value == 0.0876


def test_resolve_monthly_et_in_falls_back_on_http_error(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPENET_API_KEY", "test-key")

    mock_response = MagicMock()
    mock_response.status_code = 503
    mock_response.text = "Unavailable"

    with patch("helios.utils.openet.requests.post", return_value=mock_response):
        value, source = resolve_monthly_et_in(
            longitude=-114.45,
            latitude=43.60,
            observed_at=datetime(2024, 9, 5, tzinfo=timezone.utc),
        )

    assert source == "openet-fallback"
    assert value == 0.0289
