from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import joblib
import pandas as pd
from xgboost import XGBRegressor
from sklearn.metrics import root_mean_squared_error
from sklearn.model_selection import KFold, train_test_split
from sklearn.multioutput import MultiOutputRegressor

from helios.data.feature_engineering import TARGET_COLUMNS, build_training_features, prepare_feature_matrix


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Train the Helios soil moisture forecast model.")
    parser.add_argument("--data-path", default="data/sample_training_data.csv")
    parser.add_argument("--model-path", default="artifacts/moisture_model.pkl")
    parser.add_argument("--metadata-path", default="artifacts/model_metadata.json")
    parser.add_argument("--n-estimators", type=int, default=400)
    parser.add_argument("--learning-rate", type=float, default=0.05)
    return parser.parse_args()


def _build_estimator(n_estimators: int, learning_rate: float) -> XGBRegressor:
    return XGBRegressor(
        objective="reg:squarederror",
        n_estimators=n_estimators,
        learning_rate=learning_rate,
        max_depth=6,
        subsample=0.9,
        colsample_bytree=0.9,
        random_state=42,
        verbosity=0,
    )


def _cross_validate(
    features: pd.DataFrame,
    targets: pd.DataFrame,
    n_estimators: int,
    learning_rate: float,
) -> tuple[list[dict[str, float]], dict[str, float]]:
    fold_metrics: list[dict[str, float]] = []
    kfold = KFold(n_splits=5, shuffle=True, random_state=42)

    for train_idx, test_idx in kfold.split(features):
        x_train_fold = features.iloc[train_idx]
        x_test_fold = features.iloc[test_idx]
        y_train_fold = targets.iloc[train_idx]
        y_test_fold = targets.iloc[test_idx]

        x_train_inner, x_val, y_train_inner, y_val = train_test_split(
            x_train_fold,
            y_train_fold,
            test_size=0.15,
            random_state=42,
        )

        target_rmse: dict[str, float] = {}
        for target_name in TARGET_COLUMNS:
            estimator = _build_estimator(n_estimators=n_estimators, learning_rate=learning_rate)
            estimator.fit(
                x_train_inner,
                y_train_inner[target_name],
                eval_set=[(x_val, y_val[target_name])],
                eval_metric="rmse",
                early_stopping_rounds=25,
                verbose=False,
            )
            predictions = estimator.predict(x_test_fold)
            target_rmse[target_name] = float(root_mean_squared_error(y_test_fold[target_name], predictions))

        target_rmse["rmse_mean"] = float(sum(target_rmse.values()) / len(TARGET_COLUMNS))
        fold_metrics.append(target_rmse)

    rmse_by_target = {
        target: float(sum(fold[target] for fold in fold_metrics) / len(fold_metrics))
        for target in TARGET_COLUMNS
    }
    return fold_metrics, rmse_by_target


def _fit_final_model(
    features: pd.DataFrame,
    targets: pd.DataFrame,
    n_estimators: int,
    learning_rate: float,
) -> MultiOutputRegressor:
    x_train, x_val, y_train, y_val = train_test_split(features, targets, test_size=0.1, random_state=42)
    model = MultiOutputRegressor(_build_estimator(n_estimators=n_estimators, learning_rate=learning_rate))
    # Initialize sklearn wrapper state properly
    model.fit(x_train, y_train)
    # Now replace estimators with early-stopped versions
    for i, target_name in enumerate(TARGET_COLUMNS):
        estimator = _build_estimator(n_estimators=n_estimators, learning_rate=learning_rate)
        estimator.fit(
            x_train,
            y_train[target_name],
            eval_set=[(x_val, y_val[target_name])],
            eval_metric="rmse",
            early_stopping_rounds=25,
            verbose=False,
        )
        model.estimators_[i] = estimator
    return model


def train_model(data_path: str, model_path: str, metadata_path: str, n_estimators: int, learning_rate: float) -> None:
    data_frame = pd.read_csv(data_path)
    features, targets = build_training_features(data_frame)
    feature_columns = list(features.columns)
    features = prepare_feature_matrix(features, feature_columns)

    fold_metrics, rmse_by_target = _cross_validate(features, targets, n_estimators, learning_rate)

    x_train, x_val, y_train, y_val = train_test_split(features, targets, test_size=0.1, random_state=42)
    model = _fit_final_model(features, targets, n_estimators, learning_rate)
    val_predictions = model.predict(x_val)
    validation_rmse = float(root_mean_squared_error(y_val, val_predictions))

    artifacts_dir = Path(model_path).parent
    artifacts_dir.mkdir(parents=True, exist_ok=True)
    Path(metadata_path).parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(model, model_path)

    model_hash = hashlib.sha256(Path(model_path).read_bytes()).hexdigest()
    data_hash = hashlib.sha256(Path(data_path).read_bytes()).hexdigest()

    metadata = {
        "trained_at": datetime.now(timezone.utc).isoformat(),
        "feature_columns": feature_columns,
        "target_columns": TARGET_COLUMNS,
        "cv_rmse_mean": float(sum(metric["rmse_mean"] for metric in fold_metrics) / len(fold_metrics)),
        "cv_rmse_by_target": rmse_by_target,
        "validation_rmse": validation_rmse,
        "model_params": {
            "estimator": "XGBRegressor",
            "n_estimators": n_estimators,
            "learning_rate": learning_rate,
            "max_depth": 6,
            "objective": "reg:squarederror",
            "subsample": 0.9,
            "colsample_bytree": 0.9,
        },
        "categorical_mappings": {
            "growth_stage": ["emergence", "vegetative", "flowering", "grain_fill", "maturity"],
            "soil_texture": ["sand", "loam", "clay"],
            "drainage_class": ["poor", "moderate", "well"],
            "irrigation_type": ["pivot", "drip", "flood"],
        },
        "fold_metrics": fold_metrics,
        "model_hash": model_hash,
        "training_data_hash": data_hash,
        "training_rows": len(data_frame),
    }
    Path(metadata_path).write_text(json.dumps(metadata, indent=2))


def main() -> None:
    args = parse_args()
    train_model(
        data_path=args.data_path,
        model_path=args.model_path,
        metadata_path=args.metadata_path,
        n_estimators=args.n_estimators,
        learning_rate=args.learning_rate,
    )


if __name__ == "__main__":
    main()
