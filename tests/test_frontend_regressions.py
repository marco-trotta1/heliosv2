from __future__ import annotations

import subprocess
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _run_node(script: str) -> str:
    result = subprocess.run(
        ["node", "--input-type=module", "-e", script],
        cwd=PROJECT_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def _browser_stubs() -> str:
    return """
const storage = { getItem() { return null; }, setItem() {} };
globalThis.window = {
  HELIOS_CONFIG: { mode: 'demo' },
  localStorage: storage,
  tailwind: { refresh() {} },
};
globalThis.localStorage = storage;
globalThis.document = {
  querySelector() { return { innerHTML: '', addEventListener() {} }; },
  querySelectorAll() { return []; },
};
"""


def test_frontend_prediction_request_sends_72h_irrigation_remainder() -> None:
    output = _run_node(
        _browser_stubs()
        + """
const { buildPredictionRequest } = await import('./src/api/run-builders.js');
const inputs = {
  farmId: 'farm',
  fieldName: 'Field',
  temperatureF: 80,
  humidityPct: 50,
  windMph: 5,
  precipitationIn: 0,
  solarRadiationMjM2: 20,
  irrigationType: 'pivot',
  pumpCapacity: 0.2,
  waterWindow: ['tonight'],
  energyWindow: ['tonight'],
  lagTwoMoisture: 0.22,
  lagOneMoisture: 0.21,
  currentMoisture: 0.2,
  soilTexture: 'loam',
  infiltrationRate: 0.47,
  slopePct: 2,
  drainageClass: 'moderate',
  cropType: 'corn',
  growthStage: 'flowering',
  maxIrrigationVolume: 0.7,
  fieldAreaAcres: 50,
  budgetDollars: 1000,
  locationLat: 43,
  locationLon: -116,
  recentIrrigation24h: 0.31,
  recentIrrigation72h: 0.47,
  analysisPrompt: '',
};
const request = buildPredictionRequest(inputs);
console.log(request.recent_irrigation_events.map((event) => Number(event.applied_in.toFixed(2))).join(','));
"""
    )

    assert output == "0.31,0.16"


def test_frontend_prediction_request_clamps_negative_72h_remainder() -> None:
    output = _run_node(
        _browser_stubs()
        + """
const { buildPredictionRequest } = await import('./src/api/run-builders.js');
const inputs = {
  farmId: 'farm',
  fieldName: 'Field',
  temperatureF: 80,
  humidityPct: 50,
  windMph: 5,
  precipitationIn: 0,
  solarRadiationMjM2: 20,
  irrigationType: 'pivot',
  pumpCapacity: 0.2,
  waterWindow: ['tonight'],
  energyWindow: ['tonight'],
  lagTwoMoisture: 0.22,
  lagOneMoisture: 0.21,
  currentMoisture: 0.2,
  soilTexture: 'loam',
  infiltrationRate: 0.47,
  slopePct: 2,
  drainageClass: 'moderate',
  cropType: 'corn',
  growthStage: 'flowering',
  maxIrrigationVolume: 0.7,
  fieldAreaAcres: 50,
  budgetDollars: 1000,
  locationLat: 43,
  locationLon: -116,
  recentIrrigation24h: 0.5,
  recentIrrigation72h: 0.2,
  analysisPrompt: '',
};
const request = buildPredictionRequest(inputs);
console.log(request.recent_irrigation_events.map((event) => Number(event.applied_in.toFixed(2))).join(','));
"""
    )

    assert output == "0.5,0"


def test_frontend_local_plan_uses_72h_high_stress_water_decision() -> None:
    output = _run_node(
        """
const { generateIrrigationPlan } = await import('./src/domain/recommendations.js');
const inputs = {
  soilTexture: 'loam',
  waterWindow: ['tonight'],
  energyWindow: ['tonight'],
  estimatedEtIn: 0,
  precipitationIn: 0,
  irrigationType: 'pivot',
  maxIrrigationVolume: 5,
  pumpCapacity: 5,
  fieldAreaAcres: 10,
  budgetDollars: 10000,
  infiltrationRate: 5,
  modelRmse: 0.1,
  sensorCount: 2,
};
const predicted = { moisture24h: 0.22, moisture48h: 0.19, moisture72h: 0.17 };
const lowStress = generateIrrigationPlan(inputs, predicted, 0.79, 0);
const highStress = generateIrrigationPlan(inputs, predicted, 0.8, 0);
console.log(`${lowStress.decision},${highStress.decision},${highStress.recommendedAmountIn > 0}`);
"""
    )

    assert output == "wait,water,true"


def test_frontend_crop_select_excludes_unsupported_wheat() -> None:
    source = (PROJECT_ROOT / "src/ui/analysis-form.js").read_text()

    assert 'value: "wheat"' not in source
