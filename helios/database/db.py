from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from sqlalchemy import JSON, Column, DateTime, Float, ForeignKey, Integer, MetaData, String, Table, and_, create_engine, func, select
from sqlalchemy.engine import Engine

from helios.schemas.inputs import FeedbackCreateRequest
from helios.schemas.inputs import PredictionRequest
from helios.schemas.outputs import PredictionResponse


DATABASE_PATH = Path("data/helios.db")
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
)

_engine: Engine | None = None


def get_engine() -> Engine:
    global _engine
    if _engine is None:
        DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)
        _engine = create_engine(f"sqlite:///{DATABASE_PATH}", future=True)
    return _engine


def init_db() -> None:
    metadata.create_all(get_engine())


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


def get_feedback_rows(*, crop_type: str | None = None, recommendation_type: str | None = None) -> list[dict[str, Any]]:
    engine = get_engine()
    query = select(feedback)
    if crop_type:
        query = query.where(feedback.c.crop_type == crop_type)
    if recommendation_type:
        query = query.where(feedback.c.recommendation_type == recommendation_type)

    with engine.connect() as connection:
        rows = connection.execute(query).mappings().all()
    return [dict(row) for row in rows]
