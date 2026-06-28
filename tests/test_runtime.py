from __future__ import annotations

import pytest

from helios.api.runtime import build_runtime
from helios.config import get_settings
from helios.data.feature_engineering import build_expected_feature_columns
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


def test_build_runtime_passes_configured_evaluation_artifact_path(
    temp_settings_env,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    evaluation_path = temp_settings_env["metadata_path"].parent / "configured-eval.json"
    monkeypatch.setenv("HELIOS_EVALUATION_ARTIFACT_PATH", str(evaluation_path))
    get_settings.cache_clear()
    write_fake_model_artifacts(
        temp_settings_env["model_path"],
        temp_settings_env["metadata_path"],
    )

    runtime = build_runtime(get_settings())

    assert runtime.ready is True
    assert runtime.recommendation_service is not None
    assert runtime.recommendation_service.evaluation_artifact_path == evaluation_path


def test_build_runtime_fails_when_model_feature_columns_are_missing(temp_settings_env) -> None:
    expected_columns = build_expected_feature_columns()
    write_fake_model_artifacts(
        temp_settings_env["model_path"],
        temp_settings_env["metadata_path"],
        feature_columns=expected_columns[1:],
    )

    with pytest.raises(RuntimeError, match="Model feature schema mismatch") as exc_info:
        build_runtime(get_settings())

    message = str(exc_info.value)
    assert "metadata feature columns:" in message
    assert "feature builder feature columns:" in message
    assert "missing columns:" in message
    assert expected_columns[0] in message


def test_build_runtime_fails_when_model_feature_column_order_changes(temp_settings_env) -> None:
    expected_columns = build_expected_feature_columns()
    write_fake_model_artifacts(
        temp_settings_env["model_path"],
        temp_settings_env["metadata_path"],
        feature_columns=list(reversed(expected_columns)),
    )

    with pytest.raises(RuntimeError) as exc_info:
        build_runtime(get_settings())

    message = str(exc_info.value)
    assert "Model feature schema mismatch" in message
    assert "missing columns: []" in message
    assert "extra columns: []" in message


def test_build_runtime_can_fail_fast_when_strict_startup_is_enabled(
    temp_settings_env,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("HELIOS_STRICT_MODEL_STARTUP", "1")
    get_settings.cache_clear()

    with pytest.raises(RuntimeError):
        build_runtime(get_settings())
