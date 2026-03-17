from __future__ import annotations

import pytest

from helios.api.runtime import build_runtime
from helios.config import get_settings
from tests.conftest import write_fake_model_artifacts


def test_build_runtime_is_degraded_without_model_artifacts(temp_settings_env) -> None:
    runtime = build_runtime(get_settings())

    assert runtime.ready is False
    assert runtime.database_ready is True
    assert any("Model artifacts" in issue for issue in runtime.startup_issues)


def test_build_runtime_is_ready_with_fake_model_artifacts(temp_settings_env) -> None:
    write_fake_model_artifacts(
        temp_settings_env["model_path"],
        temp_settings_env["metadata_path"],
    )

    runtime = build_runtime(get_settings())

    assert runtime.ready is True
    assert runtime.recommendation_service is not None


def test_build_runtime_can_fail_fast_when_strict_startup_is_enabled(
    temp_settings_env,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("HELIOS_STRICT_MODEL_STARTUP", "1")
    get_settings.cache_clear()

    with pytest.raises(RuntimeError):
        build_runtime(get_settings())
