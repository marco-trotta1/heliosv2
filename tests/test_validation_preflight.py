from __future__ import annotations

from helios.config import get_settings
from helios.scripts.validation_preflight import build_manifest
from tests.conftest import write_fake_model_artifacts


def test_validation_preflight_manifest_includes_frozen_runtime_state(
    temp_settings_env,
    monkeypatch,
) -> None:
    monkeypatch.setenv("HELIOS_VALIDATION_MODE", "1")
    get_settings.cache_clear()
    write_fake_model_artifacts(
        temp_settings_env["model_path"],
        temp_settings_env["metadata_path"],
    )

    manifest = build_manifest()

    assert manifest["validation_mode"] is True
    assert manifest["model_exists"] is True
    assert manifest["metadata_exists"] is True
    assert manifest["model_hash"]
    assert manifest["metadata_hash"]
    assert manifest["checks"]["validation_mode_enabled"] is True
