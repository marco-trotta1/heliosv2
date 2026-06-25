// Runs the browser demo's decision policy over a list of scenarios and prints the
// resulting outputs as JSON. Driven by tests/test_demo_backend_parity.py, which compares
// these against the Python backend to prove demo/backend parity. No dependencies.
//
// Usage: node tests/parity/run_js.mjs <scenarios.json>

import { readFileSync } from "node:fs";

import {
  buildDrivers,
  computeStressProbability,
  generateIrrigationPlan,
} from "../../src/domain/recommendations.js";
import { SOIL_THRESHOLDS } from "../../src/constants.js";

const scenarios = JSON.parse(readFileSync(process.argv[2], "utf8"));

const results = scenarios.map((s) => {
  const dryThreshold = SOIL_THRESHOLDS[s.soil_texture].dry;
  const predicted = {
    moisture24h: s.predicted.moisture_24h,
    moisture48h: s.predicted.moisture_48h,
    moisture72h: s.predicted.moisture_72h,
  };
  const stress = computeStressProbability({
    predictedMoisture48h: predicted.moisture48h,
    dryThreshold,
    estimatedEtIn: s.estimated_et_in,
    growthStage: s.growth_stage,
  });
  const inputs = {
    soilTexture: s.soil_texture,
    drainageClass: s.drainage_class,
    irrigationType: s.irrigation_type,
    growthStage: s.growth_stage,
    waterWindow: s.water_window,
    energyWindow: s.energy_window,
    maxIrrigationVolume: s.max_irrigation_volume_in,
    pumpCapacity: s.pump_capacity_in_per_hour,
    fieldAreaAcres: s.field_area_acres,
    budgetDollars: s.budget_dollars,
    infiltrationRate: s.infiltration_rate_in_per_hour,
    modelRmse: s.model_rmse,
    sensorCount: s.sensor_count,
    currentMoisture: s.current_moisture,
    precipitationIn: s.precipitation_in,
  };
  const plan = generateIrrigationPlan(inputs, predicted, stress, s.estimated_et_in);
  const drivers = buildDrivers(inputs, predicted, stress, s.estimated_et_in);
  return {
    stress,
    decision: plan.decision,
    recommended_amount_in: plan.recommendedAmountIn,
    timing_window: plan.timingWindow,
    confidence_score: plan.confidenceScore,
    drivers,
  };
});

process.stdout.write(JSON.stringify(results));
