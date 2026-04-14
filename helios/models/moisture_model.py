from __future__ import annotations

import json
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

import joblib
import pandas as pd

from helios.data.feature_engineering import prepare_feature_matrix


@dataclass
class MoistureForecastModel:
    model: Any
    feature_columns: list[str]
    metadata: dict[str, Any]

    @classmethod
    def load(cls, model_path: Path, metadata_path: Path) -> "MoistureForecastModel":
        return _load_model_bundle(str(model_path), str(metadata_path))

    def predict(self, features: pd.DataFrame) -> dict[str, float]:
        matrix = prepare_feature_matrix(features, self.feature_columns)
        raw_prediction = self.model.predict(matrix)[0]
        keys = ["moisture_24h", "moisture_48h", "moisture_72h"]
        clipped = [float(max(0.0, min(1.0, value))) for value in raw_prediction]
        return dict(zip(keys, clipped, strict=True))


@lru_cache(maxsize=4)
def _load_model_bundle(model_path: str, metadata_path: str) -> MoistureForecastModel:
    model = joblib.load(model_path)
    metadata = json.loads(Path(metadata_path).read_text())
    return MoistureForecastModel(model=model, feature_columns=metadata["feature_columns"], metadata=metadata)


def clear_model_cache() -> None:
    _load_model_bundle.cache_clear()
