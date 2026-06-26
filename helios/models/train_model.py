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
from sklearn.model_selection import GroupKFold, GroupShuffleSplit, KFold, train_test_split
from sklearn.multioutput import MultiOutputRegressor

from helios.data.feature_engineering import TARGET_COLUMNS, build_training_features, prepare_feature_matrix
from helios.data.training_schema import validate_training_frame


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Train the Helios soil moisture forecast model.")
    parser.add_argument("--data-path", default="data/sample_training_data.csv")
    parser.add_argument("--model-path", default="artifacts/moisture_model.pkl")
    parser.add_argument("--metadata-path", default="artifacts/model_metadata.json")
    parser.add_argument("--n-estimators", type=int, default=400)
    parser.add_argument("--learning-rate", type=float, default=0.05)
    parser.add_argument("--group-column", default=None)
    parser.add_argument(
        "--target-mode",
        choices=["raw", "residual_from_current"],
        default="raw",
        help="Train raw future moisture targets or residuals from current_soil_moisture.",
    )
    return parser.parse_args()


def _build_estimator(n_estimators: int, learning_rate: float, *, early_stopping: bool = True) -> XGBRegressor:
    kwargs = {
        "objective": "reg:squarederror",
        "eval_metric": "rmse",
        "n_estimators": n_estimators,
        "learning_rate": learning_rate,
        "max_depth": 6,
        "subsample": 0.9,
        "colsample_bytree": 0.9,
        "random_state": 42,
        "verbosity": 0,
    }
    if early_stopping:
        kwargs["early_stopping_rounds"] = 25
    return XGBRegressor(**kwargs)


def _build_cross_validation_splits(
    *,
    row_count: int,
    groups: pd.Series | None = None,
) -> list[tuple[list[int], list[int]]]:
    row_index = list(range(row_count))
    if groups is None:
        return [(train.tolist(), test.tolist()) for train, test in KFold(n_splits=5, shuffle=True, random_state=42).split(row_index)]

    if groups.isna().any():
        raise ValueError("group_column contains missing values.")
    unique_group_count = int(groups.nunique(dropna=True))
    if unique_group_count < 2:
        raise ValueError("group_column must contain at least 2 distinct non-null groups.")
    splitter = GroupKFold(n_splits=min(5, unique_group_count))
    return [
        (train.tolist(), test.tolist())
        for train, test in splitter.split(row_index, groups=groups)
    ]


def _train_validation_split(
    features: pd.DataFrame,
    targets: pd.DataFrame,
    *,
    groups: pd.Series | None,
    test_size: float,
    allow_small_group_train: bool = False,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame | None, pd.DataFrame | None]:
    if groups is None:
        x_train, x_val, y_train, y_val = train_test_split(features, targets, test_size=test_size, random_state=42)
        return x_train, y_train, x_val, y_val

    unique_group_count = int(groups.nunique(dropna=True))
    if unique_group_count < 2:
        raise ValueError("group_column must contain at least 2 distinct non-null groups.")
    if allow_small_group_train and unique_group_count < 3:
        return features, targets, None, None

    splitter = GroupShuffleSplit(n_splits=1, test_size=test_size, random_state=42)
    train_idx, val_idx = next(splitter.split(features, groups=groups))
    return (
        features.iloc[train_idx],
        targets.iloc[train_idx],
        features.iloc[val_idx],
        targets.iloc[val_idx],
    )


def _cross_validate(
    features: pd.DataFrame,
    targets: pd.DataFrame,
    n_estimators: int,
    learning_rate: float,
    groups: pd.Series | None = None,
) -> tuple[list[dict[str, float]], dict[str, float]]:
    fold_metrics: list[dict[str, float]] = []

    for train_idx, test_idx in _build_cross_validation_splits(row_count=len(features), groups=groups):
        x_train_fold = features.iloc[train_idx]
        x_test_fold = features.iloc[test_idx]
        y_train_fold = targets.iloc[train_idx]
        y_test_fold = targets.iloc[test_idx]
        train_groups = groups.iloc[train_idx] if groups is not None else None

        x_train_inner, y_train_inner, x_val, y_val = _train_validation_split(
            x_train_fold,
            y_train_fold,
            groups=train_groups,
            test_size=0.15,
            allow_small_group_train=True,
        )

        target_rmse: dict[str, float] = {}
        for target_name in TARGET_COLUMNS:
            estimator = _build_estimator(
                n_estimators=n_estimators,
                learning_rate=learning_rate,
                early_stopping=x_val is not None,
            )
            fit_kwargs = {"verbose": False}
            if x_val is not None and y_val is not None:
                fit_kwargs["eval_set"] = [(x_val, y_val[target_name])]
            estimator.fit(x_train_inner, y_train_inner[target_name], **fit_kwargs)
            predictions = estimator.predict(x_test_fold)
            target_rmse[target_name] = float(root_mean_squared_error(y_test_fold[target_name], predictions))

        target_rmse["rmse_mean"] = float(sum(target_rmse.values()) / len(TARGET_COLUMNS))
        if groups is not None:
            target_rmse["train_groups"] = sorted(str(value) for value in groups.iloc[train_idx].dropna().unique())  # type: ignore[assignment]
            target_rmse["test_groups"] = sorted(str(value) for value in groups.iloc[test_idx].dropna().unique())  # type: ignore[assignment]
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
    groups: pd.Series | None = None,
) -> MultiOutputRegressor:
    x_train, y_train, x_val, y_val = _train_validation_split(features, targets, groups=groups, test_size=0.1)
    train_group_count = int(groups.loc[x_train.index].nunique(dropna=True)) if groups is not None else 0
    use_early_stopping = x_val is not None and (groups is None or train_group_count >= 3)
    model = MultiOutputRegressor(_build_estimator(n_estimators=n_estimators, learning_rate=learning_rate))
    model.estimators_ = []
    for target_name in TARGET_COLUMNS:
        estimator = _build_estimator(
            n_estimators=n_estimators,
            learning_rate=learning_rate,
            early_stopping=use_early_stopping,
        )
        fit_kwargs = {"verbose": False}
        if use_early_stopping and x_val is not None and y_val is not None:
            fit_kwargs["eval_set"] = [(x_val, y_val[target_name])]
        estimator.fit(x_train, y_train[target_name], **fit_kwargs)
        model.estimators_.append(estimator)
    model.n_features_in_ = x_train.shape[1]
    return model


def _feature_importances(
    model: MultiOutputRegressor,
    feature_columns: list[str],
) -> dict[str, dict[str, float]]:
    """Per-target feature importances so we can see which features the model actually uses.

    Surfaces, for example, whether weather features carry weight or are being ignored
    because the real (Mickelson) training rows hold them constant.
    """
    importances: dict[str, dict[str, float]] = {}
    for target_name, estimator in zip(TARGET_COLUMNS, model.estimators_, strict=True):
        scores = [float(value) for value in getattr(estimator, "feature_importances_", [])]
        ranked = sorted(zip(feature_columns, scores), key=lambda item: item[1], reverse=True)
        importances[target_name] = {name: round(score, 6) for name, score in ranked}
    return importances


def _validate_training_data(data_frame: pd.DataFrame) -> None:
    validate_training_frame(data_frame, source="combined training data")


def _build_targets_for_mode(
    data_frame: pd.DataFrame,
    targets: pd.DataFrame,
    *,
    target_mode: str,
) -> pd.DataFrame:
    if target_mode == "raw":
        return targets.copy()
    if target_mode != "residual_from_current":
        raise ValueError("target_mode must be one of: raw, residual_from_current")
    if "current_soil_moisture" not in data_frame.columns:
        raise ValueError("residual_from_current target mode requires current_soil_moisture.")

    current = pd.to_numeric(data_frame["current_soil_moisture"], errors="coerce")
    if current.isna().any():
        raise ValueError("current_soil_moisture contains non-numeric values.")
    residual_targets = targets.copy()
    for column in TARGET_COLUMNS:
        residual_targets[column] = pd.to_numeric(targets[column], errors="coerce") - current
    return residual_targets


def train_model(
    data_path: str,
    model_path: str,
    metadata_path: str,
    n_estimators: int,
    learning_rate: float,
    group_column: str | None = None,
    target_mode: str = "raw",
) -> None:
    data_frame = pd.read_csv(data_path)
    _validate_training_data(data_frame)
    groups = None
    if group_column is not None:
        if group_column not in data_frame.columns:
            raise ValueError(f"group_column {group_column!r} is not present in training data.")
        if data_frame[group_column].isna().any():
            raise ValueError(f"group_column {group_column!r} contains missing values.")
        groups = data_frame[group_column].copy()
    features, raw_targets = build_training_features(data_frame)
    targets = _build_targets_for_mode(data_frame, raw_targets, target_mode=target_mode)
    feature_columns = list(features.columns)
    features = prepare_feature_matrix(features, feature_columns)

    fold_metrics, rmse_by_target = _cross_validate(features, targets, n_estimators, learning_rate, groups=groups)

    x_train, y_train, x_val, y_val = _train_validation_split(features, targets, groups=groups, test_size=0.1)
    model = _fit_final_model(features, targets, n_estimators, learning_rate, groups=groups)
    if x_val is None or y_val is None:
        x_val = x_train
        y_val = y_train
    val_predictions = model.predict(x_val)
    validation_rmse = float(root_mean_squared_error(y_val, val_predictions))

    feature_importances = _feature_importances(model, feature_columns)

    artifacts_dir = Path(model_path).parent
    artifacts_dir.mkdir(parents=True, exist_ok=True)
    Path(metadata_path).parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(model, model_path)

    model_hash = hashlib.sha256(Path(model_path).read_bytes()).hexdigest()
    data_hash = hashlib.sha256(Path(data_path).read_bytes()).hexdigest()

    trained_at = datetime.now(timezone.utc).isoformat()
    metadata = {
        "trained_at": trained_at,
        "training_date": trained_at,
        "feature_columns": feature_columns,
        "target_columns": TARGET_COLUMNS,
        "target_mode": target_mode,
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
        "group_column": group_column,
        "cv_splitter": "GroupKFold" if group_column is not None else "KFold",
        "feature_importances": feature_importances,
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
        group_column=args.group_column,
        target_mode=args.target_mode,
    )


if __name__ == "__main__":
    main()
