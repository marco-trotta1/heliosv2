from __future__ import annotations

import json
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

import joblib
import pandas as pd

from helios.data.feature_engineering import prepare_feature_matrix


# Physically plausible volumetric water content envelopes by soil texture. Lower bounds sit
# near the permanent wilting point and upper bounds near saturation, kept wide enough to
# bracket each texture's dry/wet decision thresholds. Replaces a meaningless [0, 1] clip
# that allowed agronomically impossible predictions.
TEXTURE_MOISTURE_BOUNDS = {
    "sand": (0.04, 0.30),
    "loam": (0.06, 0.42),
    "clay": (0.10, 0.48),
}
# Fallback envelope matching the training-target clip range when texture is unknown.
DEFAULT_MOISTURE_BOUNDS = (0.05, 0.50)


def _texture_from_features(features: pd.DataFrame) -> str | None:
    for texture in TEXTURE_MOISTURE_BOUNDS:
        column = f"soil_texture_{texture}"
        if column in features.columns and float(features.iloc[0][column]) >= 0.5:
            return texture
    return None


def clip_to_texture_bounds(values: list[float], texture: str | None) -> list[float]:
    low, high = TEXTURE_MOISTURE_BOUNDS.get(texture, DEFAULT_MOISTURE_BOUNDS)
    return [float(max(low, min(high, value))) for value in values]


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
        if self.metadata.get("target_mode", "raw") == "residual_from_current":
            current = float(features.iloc[0]["current_soil_moisture"])
            raw_prediction = [current + float(value) for value in raw_prediction]
        keys = ["moisture_24h", "moisture_48h", "moisture_72h"]
        clipped = clip_to_texture_bounds(list(raw_prediction), _texture_from_features(features))
        return dict(zip(keys, clipped, strict=True))


@lru_cache(maxsize=4)
def _load_model_bundle(model_path: str, metadata_path: str) -> MoistureForecastModel:
    model = joblib.load(model_path)
    metadata = json.loads(Path(metadata_path).read_text())
    return MoistureForecastModel(model=model, feature_columns=metadata["feature_columns"], metadata=metadata)


def clear_model_cache() -> None:
    _load_model_bundle.cache_clear()
