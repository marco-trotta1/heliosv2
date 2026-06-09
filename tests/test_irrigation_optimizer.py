from __future__ import annotations

from helios.optimizer.irrigation_optimizer import OptimizationInputs, generate_irrigation_plan


def _inputs(
    *,
    predicted_moisture: dict[str, float],
    stress_probability: float = 0.5,
    irrigation_type: str = "pivot",
    max_irrigation_volume_in: float = 5.0,
    recent_precipitation_in: float = 0.0,
    estimated_et_in: float = 0.0,
    growth_stage: str = "vegetative",
    drainage_class: str = "moderate",
    et_is_fallback: bool = False,
) -> OptimizationInputs:
    return OptimizationInputs(
        predicted_moisture=predicted_moisture,
        stress_probability=stress_probability,
        soil_texture="loam",
        infiltration_rate_in_per_hour=5.0,
        pump_capacity_in_per_hour=5.0,
        water_rights_schedule=["tonight", "tomorrow_morning"],
        energy_price_window=["tonight"],
        max_irrigation_volume_in=max_irrigation_volume_in,
        field_area_acres=10.0,
        budget_dollars=10000.0,
        estimated_et_in=estimated_et_in,
        recent_precipitation_in=recent_precipitation_in,
        model_rmse=0.1,
        sensor_count=6,
        physical_sensor_count=2,
        irrigation_type=irrigation_type,
        growth_stage=growth_stage,
        drainage_class=drainage_class,
        et_is_fallback=et_is_fallback,
    )


def test_high_stress_uses_72h_dry_threshold_for_water_decision() -> None:
    predicted = {
        "moisture_24h": 0.22,
        "moisture_48h": 0.19,
        "moisture_72h": 0.17,
    }

    low_stress_plan = generate_irrigation_plan(
        _inputs(predicted_moisture=predicted, stress_probability=0.79)
    )
    high_stress_plan = generate_irrigation_plan(
        _inputs(predicted_moisture=predicted, stress_probability=0.80)
    )

    assert low_stress_plan["decision"] == "wait"
    assert high_stress_plan["decision"] == "water"
    assert high_stress_plan["recommended_amount_in"] > 0.0


def test_irrigation_efficiency_converts_net_deficit_to_gross_applied_inches() -> None:
    predicted = {
        "moisture_24h": 0.20,
        "moisture_48h": 0.16,
        "moisture_72h": 0.15,
    }

    drip_plan = generate_irrigation_plan(
        _inputs(predicted_moisture=predicted, irrigation_type="drip")
    )
    flood_plan = generate_irrigation_plan(
        _inputs(predicted_moisture=predicted, irrigation_type="flood")
    )

    assert drip_plan["recommended_amount_in"] == 0.57
    assert flood_plan["recommended_amount_in"] == 0.78


def test_precipitation_is_not_subtracted_after_model_forecast() -> None:
    predicted = {
        "moisture_24h": 0.20,
        "moisture_48h": 0.16,
        "moisture_72h": 0.15,
    }

    dry_plan = generate_irrigation_plan(
        _inputs(predicted_moisture=predicted, recent_precipitation_in=0.0)
    )
    rainy_plan = generate_irrigation_plan(
        _inputs(predicted_moisture=predicted, recent_precipitation_in=1.0)
    )

    assert rainy_plan["recommended_amount_in"] == dry_plan["recommended_amount_in"]


def test_peak_growth_stage_receives_more_water_than_low_demand_stage() -> None:
    predicted = {
        "moisture_24h": 0.20,
        "moisture_48h": 0.16,
        "moisture_72h": 0.15,
    }

    flowering_plan = generate_irrigation_plan(
        _inputs(predicted_moisture=predicted, estimated_et_in=0.3, growth_stage="flowering")
    )
    maturity_plan = generate_irrigation_plan(
        _inputs(predicted_moisture=predicted, estimated_et_in=0.3, growth_stage="maturity")
    )

    assert flowering_plan["recommended_amount_in"] > maturity_plan["recommended_amount_in"]


def test_well_drained_soil_receives_more_gross_water_than_poorly_drained() -> None:
    predicted = {
        "moisture_24h": 0.20,
        "moisture_48h": 0.16,
        "moisture_72h": 0.15,
    }

    well_plan = generate_irrigation_plan(
        _inputs(predicted_moisture=predicted, drainage_class="well")
    )
    poor_plan = generate_irrigation_plan(
        _inputs(predicted_moisture=predicted, drainage_class="poor")
    )

    assert well_plan["recommended_amount_in"] > poor_plan["recommended_amount_in"]


def test_climatology_fallback_et_lowers_confidence() -> None:
    predicted = {
        "moisture_24h": 0.20,
        "moisture_48h": 0.16,
        "moisture_72h": 0.15,
    }

    live_plan = generate_irrigation_plan(
        _inputs(predicted_moisture=predicted, et_is_fallback=False)
    )
    fallback_plan = generate_irrigation_plan(
        _inputs(predicted_moisture=predicted, et_is_fallback=True)
    )

    assert fallback_plan["confidence_score"] < live_plan["confidence_score"]


def test_water_decision_requires_minimum_actionable_amount() -> None:
    plan = generate_irrigation_plan(
        _inputs(
            predicted_moisture={
                "moisture_24h": 0.18,
                "moisture_48h": 0.17,
                "moisture_72h": 0.16,
            },
            max_irrigation_volume_in=0.004,
        )
    )

    assert plan["decision"] == "wait"
    assert plan["recommended_amount_in"] == 0.0
