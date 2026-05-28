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


def test_decision_card_action_branch() -> None:
    """decision=water + adequate confidence + recommendedAmountIn>0 -> action headline with amount and timing."""
    output = _run_node(
        _browser_stubs()
        + """
const { buildDecisionCardData } = await import('./src/domain/output.js');
const run = {
  confidenceScore: 0.72,
  stressProbability: 0.55,
  recommendedAmountIn: 0.70,
  decision: 'water',
  timingWindow: 'tonight',
  predicted: { moisture24h: 0.20, moisture48h: 0.17, moisture72h: 0.14 },
  inputSnapshot: { currentMoisture: 0.22 },
};
const out = buildDecisionCardData(run);
console.log(`${out.state}|${out.headline}|${out.stressQualifier.level}|${out.confidenceQualifier.level}|${out.forecastStrip.length}|${out.forecastStrip[3].stressLevel}`);
"""
    )

    assert output == "action|We think you'll need to irrigate 0.70 inches tonight.|moderate|mostly|4|high"


def test_decision_card_all_clear_branch() -> None:
    """decision=wait + recommendedAmountIn=0 -> all-clear headline, no irrigation needed."""
    output = _run_node(
        _browser_stubs()
        + """
const { buildDecisionCardData } = await import('./src/domain/output.js');
const run = {
  confidenceScore: 0.85,
  stressProbability: 0.10,
  recommendedAmountIn: 0,
  decision: 'wait',
  timingWindow: 'monitor next forecast cycle',
  predicted: { moisture24h: 0.32, moisture48h: 0.30, moisture72h: 0.28 },
  inputSnapshot: { currentMoisture: 0.34 },
};
const out = buildDecisionCardData(run);
console.log(`${out.state}|${out.headline}|${out.stressQualifier.level}|${out.confidenceQualifier.text}`);
"""
    )

    assert output == "all-clear|Soil's holding water — no irrigation needed through the next forecast cycle.|low|high confidence"


def test_decision_card_urgent_branch() -> None:
    """stressProbability>=0.85 -> urgent headline regardless of decision."""
    output = _run_node(
        _browser_stubs()
        + """
const { buildDecisionCardData } = await import('./src/domain/output.js');
const run = {
  confidenceScore: 0.7,
  stressProbability: 0.92,
  recommendedAmountIn: 0.85,
  decision: 'water',
  timingWindow: 'tonight',
  predicted: { moisture24h: 0.14, moisture48h: 0.12, moisture72h: 0.10 },
  inputSnapshot: { currentMoisture: 0.16 },
};
const out = buildDecisionCardData(run);
console.log(`${out.state}|${out.headline}|${out.stressQualifier.level}`);
"""
    )

    assert output == "urgent|Stress is high — irrigate 0.85 inches as soon as you can.|high"


def test_decision_card_insufficient_branch() -> None:
    """confidenceScore<0.4 OR predicted.moisture24h===0 -> insufficient state, stressQualifier omitted."""
    output = _run_node(
        _browser_stubs()
        + """
const { buildDecisionCardData } = await import('./src/domain/output.js');
const lowConf = buildDecisionCardData({
  confidenceScore: 0.30,
  stressProbability: 0.5,
  recommendedAmountIn: 0.5,
  decision: 'water',
  timingWindow: 'tonight',
  predicted: { moisture24h: 0.22, moisture48h: 0.20, moisture72h: 0.18 },
  inputSnapshot: { currentMoisture: 0.24 },
});
const missingForecast = buildDecisionCardData({
  confidenceScore: 0.80,
  stressProbability: 0.5,
  recommendedAmountIn: 0.5,
  decision: 'water',
  timingWindow: 'tonight',
  predicted: { moisture24h: 0, moisture48h: 0, moisture72h: 0 },
  inputSnapshot: { currentMoisture: 0 },
});
console.log(`${lowConf.state}|${lowConf.stressQualifier}|${lowConf.confidenceQualifier.italic}|${missingForecast.state}|${missingForecast.forecastStrip[0].isEmpty}`);
"""
    )

    assert output == "insufficient|null|true|insufficient|true"


def test_decision_card_window_sentence_fallback() -> None:
    """formatWindowSentence returns 'soon' for unknown timing window values."""
    output = _run_node(
        _browser_stubs()
        + """
const { formatWindowSentence } = await import('./src/domain/output.js');
console.log([
  formatWindowSentence('tonight'),
  formatWindowSentence('MONITOR NEXT FORECAST CYCLE'),
  formatWindowSentence(''),
  formatWindowSentence(undefined),
  formatWindowSentence('weird-unknown-value'),
].join('|'));
"""
    )

    assert output == "tonight|through the next forecast cycle|soon|soon|soon"
