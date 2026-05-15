from __future__ import annotations

import hashlib
import json
from pathlib import Path

from fastapi.testclient import TestClient

from tests.conftest import write_fake_model_artifacts


def test_version_returns_hash_and_training_date_without_auth(
    temp_settings_env,
    monkeypatch,
) -> None:
    import helios.api.main as main_module
    from helios.api.runtime import AppRuntime
    from helios.config import get_settings
    from helios.database.db import init_db

    model_path = temp_settings_env["model_path"]
    metadata_path = temp_settings_env["metadata_path"]
    write_fake_model_artifacts(model_path, metadata_path)
    metadata_path.write_text(
        json.dumps(
            {
                "feature_columns": [],
                "training_date": "2026-04-17T23:00:00+00:00",
            }
        )
    )

    monkeypatch.setenv("HELIOS_API_KEY", "secret-test-key")
    get_settings.cache_clear()

    def fake_build_runtime(settings):
        init_db()
        return AppRuntime(
            settings=settings,
            recommendation_service=None,
            database_ready=True,
            startup_issues=[],
        )

    monkeypatch.setattr(main_module, "build_runtime", fake_build_runtime)
    app = main_module.create_app(get_settings())
    with TestClient(app) as client:
        response = client.get("/version")

    expected_hash = hashlib.sha256(Path(model_path).read_bytes()).hexdigest()[:12]
    assert response.status_code == 200
    assert response.json() == {
        "model_artifact_hash": expected_hash,
        "training_date": "2026-04-17T23:00:00+00:00",
        "api_version": "1.0.0",
        "validation_mode": "disabled",
    }


def test_version_returns_model_not_loaded_when_artifact_missing(app_factory) -> None:
    with app_factory(recommendation_service=None, database_ready=True) as client:
        response = client.get("/version")

    assert response.status_code == 200
    assert response.json()["model_artifact_hash"] == "model_not_loaded"
