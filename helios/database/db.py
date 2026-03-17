from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from sqlalchemy import JSON, Column, DateTime, Float, ForeignKey, Integer, MetaData, String, Table, and_, create_engine, func, inspect, select, text
from sqlalchemy.engine import Engine

from helios.config import get_settings
from helios.schemas.inputs import FeedbackCreateRequest, PredictionRequest
from helios.schemas.outputs import PredictionResponse


metadata = MetaData()

prediction_runs = Table(
    "prediction_runs",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("created_at", DateTime(timezone=True), server_default=func.now(), nullable=False),
    Column("field_id", String, nullable=False),
    Column("request_json", JSON, nullable=False),
    Column("response_json", JSON, nullable=False),
    Column("decision", String, nullable=False),
    Column("recommended_amount_mm", Float, nullable=False),
    Column("confidence_score", Float, nullable=False),
)

sensor_snapshots = Table(
    "sensor_snapshots",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("prediction_run_id", ForeignKey("prediction_runs.id"), nullable=False),
    Column("timestamp", DateTime(timezone=True), nullable=False),
    Column("volumetric_water_content", Float, nullable=False),
)

feedback = Table(
    "feedback",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("farm_id", String, nullable=False, index=True),
    Column("timestamp", DateTime(timezone=True), nullable=False, index=True),
    Column("crop_type", String, nullable=False, index=True),
    Column("recommendation_type", String, nullable=False, index=True),
    Column("recommendation_value", String, nullable=False),
    Column("outcome", String, nullable=False),
    Column("yield_delta", Float, nullable=True),
    Column("notes", String, nullable=True),
    Column("location_lat", Float, nullable=False),
    Column("location_lon", Float, nullable=False),
    Column("soil_texture", String, nullable=True),
    Column("irrigation_type", String, nullable=True),
    Column("growth_stage", String, nullable=True),
    Column("season_month", Integer, nullable=True),
)

_engine: Engine | None = None


def _database_path() -> Path:
    return get_settings().database_path


def get_engine() -> Engine:
    global _engine
    if _engine is None:
        database_path = _database_path()
        database_path.parent.mkdir(parents=True, exist_ok=True)
        _engine = create_engine(
            f"sqlite:///{database_path}",
            future=True,
            connect_args={"check_same_thread": False},
            pool_pre_ping=True,
        )
    return _engine


def reset_engine() -> None:
    global _engine
    if _engine is not None:
        _engine.dispose()
    _engine = None


def init_db() -> None:
    engine = get_engine()
    metadata.create_all(engine)
    _migrate_feedback_table(engine)


def _migrate_feedback_table(engine: Engine) -> None:
    existing_columns = {column["name"] for column in inspect(engine).get_columns("feedback")}
    optional_columns = {
        "soil_texture": "TEXT",
        "irrigation_type": "TEXT",
        "growth_stage": "TEXT",
        "season_month": "INTEGER",
    }
    with engine.begin() as connection:
        for column_name, column_type in optional_columns.items():
            if column_name in existing_columns:
                continue
            connection.execute(text(f"ALTER TABLE feedback ADD COLUMN {column_name} {column_type}"))
        connection.execute(text("CREATE INDEX IF NOT EXISTS ix_feedback_crop_type ON feedback (crop_type)"))
        connection.execute(text("CREATE INDEX IF NOT EXISTS ix_feedback_recommendation_type ON feedback (recommendation_type)"))
        connection.execute(text("CREATE INDEX IF NOT EXISTS ix_feedback_farm_id ON feedback (farm_id)"))
        connection.execute(text("CREATE INDEX IF NOT EXISTS ix_feedback_timestamp ON feedback (timestamp)"))


def save_prediction_run(request: PredictionRequest, response: PredictionResponse) -> int:
    engine = get_engine()
    with engine.begin() as connection:
        result = connection.execute(
            prediction_runs.insert().values(
                field_id=request.field_id,
                request_json=request.model_dump(mode="json"),
                response_json=response.model_dump(mode="json"),
                decision=response.decision,
                recommended_amount_mm=response.recommended_amount_mm,
                confidence_score=response.confidence_score,
            )
        )
        run_id = int(result.inserted_primary_key[0])
        connection.execute(
            sensor_snapshots.insert(),
            [
                {
                    "prediction_run_id": run_id,
                    "timestamp": reading.timestamp,
                    "volumetric_water_content": reading.volumetric_water_content,
                }
                for reading in request.soil_moisture_readings
            ],
        )
    return run_id


def get_recent_runs(limit: int = 20) -> list[dict[str, Any]]:
    engine = get_engine()
    with engine.connect() as connection:
        rows = connection.execute(
            select(prediction_runs).order_by(prediction_runs.c.created_at.desc()).limit(limit)
        ).mappings()
        return [dict(row) for row in rows]


def insert_feedback(payload: FeedbackCreateRequest) -> int:
    engine = get_engine()
    with engine.begin() as connection:
        result = connection.execute(
            feedback.insert().values(
                farm_id=payload.farm_id,
                timestamp=payload.timestamp,
                crop_type=payload.crop_type,
                recommendation_type=payload.recommendation_type,
                recommendation_value=payload.recommendation_value,
                outcome=payload.outcome,
                yield_delta=payload.yield_delta,
                notes=payload.notes,
                location_lat=payload.location_lat,
                location_lon=payload.location_lon,
                soil_texture=payload.soil_texture,
                irrigation_type=payload.irrigation_type,
                growth_stage=payload.growth_stage,
                season_month=payload.timestamp.month,
            )
        )
        return int(result.inserted_primary_key[0])


def find_duplicate_feedback(
    *,
    farm_id: str,
    timestamp: datetime,
    recommendation_type: str,
    window: timedelta,
) -> int | None:
    engine = get_engine()
    window_start = timestamp - window
    window_end = timestamp + window
    with engine.connect() as connection:
        row = connection.execute(
            select(feedback.c.id)
            .where(
                and_(
                    feedback.c.farm_id == farm_id,
                    feedback.c.recommendation_type == recommendation_type,
                    feedback.c.timestamp >= window_start,
                    feedback.c.timestamp <= window_end,
                )
            )
            .limit(1)
        ).first()
    if row is None:
        return None
    return int(row[0])


def get_feedback_rows(
    *,
    crop_type: str | None = None,
    recommendation_type: str | None = None,
    soil_texture: str | None = None,
    irrigation_type: str | None = None,
) -> list[dict[str, Any]]:
    engine = get_engine()
    query = select(feedback)
    if crop_type:
        query = query.where(feedback.c.crop_type == crop_type)
    if recommendation_type:
        query = query.where(feedback.c.recommendation_type == recommendation_type)
    if soil_texture:
        query = query.where(feedback.c.soil_texture == soil_texture)
    if irrigation_type:
        query = query.where(feedback.c.irrigation_type == irrigation_type)

    with engine.connect() as connection:
        rows = connection.execute(query).mappings().all()
    return [dict(row) for row in rows]
