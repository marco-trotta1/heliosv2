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
// insufficient state forces ALL strip dots empty (per doc state table), even when moisture values are non-zero.
const allEmpty = lowConf.forecastStrip.every((tick) => tick.isEmpty === true);
console.log(`${lowConf.state}|${lowConf.stressQualifier}|${lowConf.confidenceQualifier.italic}|${missingForecast.state}|${missingForecast.forecastStrip[0].isEmpty}|allEmpty=${allEmpty}`);
"""
    )

    assert output == "insufficient|null|true|insufficient|true|allEmpty=true"


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


def test_frontend_maps_api_validation_evidence_into_copy_packet() -> None:
    output = _run_node(
        _browser_stubs()
        + """
const { state } = await import('./src/state.js');
const { mapApiRun } = await import('./src/api/run-builders.js');
state.backend.modelHash = 'runtimehash';
state.backend.trainingDate = '2026-04-17T23:00:00+00:00';
state.backend.apiVersion = '1.0.0';
state.backend.validationMode = true;
const inputs = {
  fieldName: 'North Pivot',
  analysisPrompt: 'Preserve this run for field-test review.',
};
const response = {
  decision: 'water',
  recommended_amount_in: 0.49,
  timing_window: 'tonight',
  confidence_score: 0.74,
  et_source: 'openet-fallback',
  explanation: {
    stress_probability: 0.82,
    drivers: ['low soil moisture'],
    driving_zone: 'sensor-a',
    zone_moisture_summary: { 'sensor-a': 0.20, 'sensor-b': 0.35 },
    high_variability_flag: true,
  },
  predicted_moisture: {
    moisture_24h: 0.2,
    moisture_48h: 0.16,
    moisture_72h: 0.13,
  },
  recommendation_adjustment: {
    base_recommendation_in: 0.49,
    adjusted_recommendation_in: 0.49,
    adjustment_factor: 1,
    reason: 'Validation mode is enabled, so nearby feedback adjustments were disabled for a clean field test.',
  },
  regional_insights: {
    success_rate: 0,
    total_samples: 0,
    weighted_samples: 0,
    comparable_samples: 0,
    radius_miles: 31.07,
  },
  validation_evidence: {
    validation_mode: 'enabled',
    model_artifact_hash: 'abc123def456',
    model_training_date: '2026-04-17T23:00:00+00:00',
    et_source: 'openet-fallback',
    feedback_adjustment_status: 'Validation mode: feedback adjustments disabled',
    driving_zone: 'sensor-a',
    high_variability_flag: true,
    confidence_caveat: 'Heuristic confidence; not a calibrated uncertainty estimate.',
    field_test_caveat: 'Field-test evidence only; no validation-score evidence is attached to this recommendation.',
    preservation_note: 'Copy this evidence packet with the recommendation to preserve the exact field-test context.',
  },
};
const run = mapApiRun(inputs, response);
const banned = ['validated recommendation', 'proven accuracy', 'certified']
  .some((claim) => run.copyText.toLowerCase().includes(claim));
console.log([
  run.validationEvidence.validationMode,
  run.validationEvidence.feedbackAdjustmentStatus,
  run.copyText.includes('Evidence packet'),
  run.copyText.includes('Heuristic confidence; not a calibrated uncertainty estimate.'),
  run.copyText.includes('Validation mode: feedback adjustments disabled'),
  run.copyText.includes('Field-test evidence only'),
  banned,
].join('|'));
"""
    )

    assert output == (
        "enabled|Validation mode: feedback adjustments disabled|true|true|true|true|false"
    )


def test_frontend_result_card_renders_evidence_packet_without_overclaiming() -> None:
    output = _run_node(
        _browser_stubs()
        + """
const { ResultCard } = await import('./src/ui/results.js');
const run = {
  id: 'run-1',
  inputSnapshot: { fieldName: 'North Pivot' },
  timestamp: '2026-04-17T23:00:00+00:00',
  decision: 'water',
  recommendedAmountIn: 0.49,
  timingWindow: 'tonight',
  confidenceScore: 0.74,
  validationEvidence: {
    validationMode: 'enabled',
    modelArtifactHash: 'abc123def456',
    modelTrainingDate: '2026-04-17T23:00:00+00:00',
    etSource: 'openet-fallback',
    feedbackAdjustmentStatus: 'Validation mode: feedback adjustments disabled',
    drivingZone: 'sensor-a',
    highVariabilityFlag: true,
    confidenceCaveat: 'Heuristic confidence; not a calibrated uncertainty estimate.',
    fieldTestCaveat: 'Field-test evidence only; no validation-score evidence is attached to this recommendation.',
    preservationNote: 'Copy this evidence packet with the recommendation to preserve the exact field-test context.',
  },
  backendSnapshot: { validationMode: true },
  etSource: 'openet-fallback',
  copyText: 'Evidence packet',
};
const html = ResultCard(run);
const banned = ['validated recommendation', 'proven accuracy', 'certified']
  .some((claim) => html.toLowerCase().includes(claim));
const detailsIndex = html.indexOf('TECHNICAL DETAILS & REVIEW EVIDENCE');
const evidenceIndex = html.indexOf('evidence-packet-summary');
const technicalTextIndex = html.indexOf('<pre');
console.log([
  html.includes('EVIDENCE PACKET'),
  html.includes('Validation mode: feedback adjustments disabled'),
  html.includes('Heuristic confidence'),
  html.includes('evidence-packet-summary'),
  html.includes('mx-4 my-3'),
  html.includes('text-center'),
  html.includes('bg-[#fbfaf7]'),
  detailsIndex > -1 && evidenceIndex > detailsIndex,
  technicalTextIndex > evidenceIndex,
  banned,
].join('|'));
"""
    )

    assert output == "true|true|true|true|true|true|true|true|true|false"


def test_light_theme_uses_subtle_off_white_surfaces() -> None:
    source = (PROJECT_ROOT / "styles.css").read_text()

    assert "--bg: #fbfaf7;" in source
    assert "--bg-strong: #f3f2ec;" in source
    assert "--panel: #fffefa;" in source
    assert "--panel-muted: #f6f5f0;" in source


def test_frontend_normalize_run_preserves_validation_evidence_packet() -> None:
    output = _run_node(
        _browser_stubs()
        + """
const { normalizeRun } = await import('./src/state.js');
const run = normalizeRun({
  id: 'stored-run',
  title: 'Stored Run',
  timestamp: '2026-04-17T23:00:00+00:00',
  decision: 'water',
  recommendedAmountIn: 0.49,
  timingWindow: 'tonight',
  confidenceScore: 0.74,
  stressProbability: 0.82,
  estimatedEtIn: 0.21,
  predicted: { moisture24h: 0.2, moisture48h: 0.16, moisture72h: 0.13 },
  drivers: ['low soil moisture'],
  inputSnapshot: { fieldName: 'North Pivot' },
  copyText: 'stale copy without packet',
  validation_evidence: {
    validation_mode: 'enabled',
    model_artifact_hash: 'abc123def456',
    model_training_date: '2026-04-17T23:00:00+00:00',
    et_source: 'openet-fallback',
    feedback_adjustment_status: 'Validation mode: feedback adjustments disabled',
    driving_zone: 'sensor-a',
    high_variability_flag: true,
    confidence_caveat: 'Heuristic confidence; not a calibrated uncertainty estimate.',
    field_test_caveat: 'Field-test evidence only; no validation-score evidence is attached to this recommendation.',
    preservation_note: 'Copy this evidence packet with the recommendation to preserve the exact field-test context.',
  },
});
console.log([
  run.validationEvidence.validationMode,
  run.validationEvidence.modelArtifactHash,
  run.copyText.includes('Evidence packet'),
  run.copyText.includes('stale copy without packet'),
].join('|'));
"""
    )

    assert output == "enabled|abc123def456|true|false"
