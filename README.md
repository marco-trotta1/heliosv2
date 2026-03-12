# Helios

Helios is a local prototype of an AI irrigation decision-support system for the Irrigant platform. It ingests weather, soil moisture, and farm constraints, predicts soil moisture over the next 72 hours, estimates crop stress risk, and returns a practical irrigation recommendation.

## Architecture

```text
FastAPI API
  -> Pydantic request validation
  -> RecommendationService
      -> ingestion + feature engineering
      -> LightGBM multi-output forecast model
      -> rule-based irrigation optimizer
      -> SQLite persistence
```

## Project Structure

```text
helios/
  api/
  data/
  database/
  models/
  optimizer/
  schemas/
  scripts/
  services/
  utils/
notebooks/
artifacts/
data/
```

## Local Setup

Use Python 3.11 for the intended runtime.

```bash
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Generate Synthetic Data

```bash
python -m helios.scripts.generate_sample_data --rows 2500
```

This creates `data/sample_training_data.csv`.

## Train the Model

```bash
python -m helios.models.train_model
```

This writes:

- `artifacts/moisture_model.pkl`
- `artifacts/model_metadata.json`

## Run the API

```bash
uvicorn helios.api.main:app --reload
```

Available endpoints:

- `GET /health`
- `POST /predict`

## Example API Call

```bash
curl -X POST http://127.0.0.1:8000/predict \
  -H "Content-Type: application/json" \
  -d '{
    "field_id": "field-001",
    "forecast_horizon_hours": 72,
    "weather": {
      "temperature_c": 31.0,
      "humidity_pct": 38.0,
      "wind_mps": 3.8,
      "precipitation_mm": 0.0,
      "solar_radiation_mj_m2": 24.0,
      "forecast_horizon_hours": 72
    },
    "irrigation_system": {
      "irrigation_type": "pivot",
      "pump_capacity_mm_per_hour": 6.0,
      "water_rights_schedule": ["tonight", "tomorrow_morning"],
      "energy_price_window": ["tonight"]
    },
    "soil_moisture_readings": [
      {
        "timestamp": "2026-03-12T06:00:00Z",
        "field_id": "field-001",
        "volumetric_water_content": 0.22
      },
      {
        "timestamp": "2026-03-12T09:00:00Z",
        "field_id": "field-001",
        "volumetric_water_content": 0.21
      },
      {
        "timestamp": "2026-03-12T12:00:00Z",
        "field_id": "field-001",
        "volumetric_water_content": 0.20
      }
    ],
    "soil_properties": {
      "soil_texture": "loam",
      "infiltration_rate_mm_per_hour": 12.0,
      "slope_pct": 2.5,
      "drainage_class": "moderate"
    },
    "crop": {
      "crop_type": "corn",
      "growth_stage": "flowering"
    },
    "operational": {
      "max_irrigation_volume_mm": 18.0,
      "field_area_ha": 24.0,
      "budget_dollars": 500.0
    },
    "recent_irrigation_events": [
      {
        "timestamp": "2026-03-11T05:00:00Z",
        "applied_mm": 8.0
      }
    ]
  }'
```

## SQLite Storage

Helios stores local prediction history in `data/helios.db`.

- `prediction_runs`: raw request, raw response, decision, amount, confidence
- `sensor_snapshots`: sensor values associated with each prediction run

## Notebook Visualization

Open the notebook after generating predictions or sample data:

```bash
jupyter notebook notebooks/helios_demo.ipynb
```

The notebook visualizes:

- current and forecast soil moisture trajectory
- recommendation outcome and confidence
- recent stored predictions

## Future Integration Points

- `helios/utils/weather_api.py` is the seam for NOAA weather ingestion.
- `helios/data/ingestion.py` can be extended for real sensor payloads.
- `helios/database/db.py` can be swapped for a managed database later.
- FastAPI routes are ready for cloud deployment once infrastructure is added.

## GitHub Pages Repo View

This repository includes a root `index.html` viewer so GitHub Pages can render the codebase directly from the repository.

To publish it:

1. Push the repository to GitHub.
2. In the GitHub repo settings, enable GitHub Pages.
3. Set the source to the `main` branch and the `/ (root)` folder.
4. Open the published Pages URL to browse the repository files in the built-in viewer.

## Limitations

- the model is trained on synthetic data
- ET is an approximate proxy, not a certified agronomic calculator
- recommendation confidence is heuristic, not calibrated uncertainty
- optimization is rule-based rather than a full solver
