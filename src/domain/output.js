import { formatPercent, formatTimestamp, formatWindow } from "./format.js";

const WINDOW_SENTENCES = {
  "monitor next forecast cycle": "through the next forecast cycle",
  "next available permitted window": "at the next available window",
  tonight: "tonight",
  morning: "tomorrow morning",
  afternoon: "this afternoon",
  evening: "this evening",
  anytime: "whenever you can",
};

export function formatWindowSentence(timingWindow) {
  if (!timingWindow) return "soon";
  const key = String(timingWindow).toLowerCase();
  return WINDOW_SENTENCES[key] || "soon";
}

function classifyStressTickLevel(moisture) {
  if (moisture <= 0.15) return "high";
  if (moisture <= 0.25) return "moderate";
  return "low";
}

function classifyConfidence(score) {
  if (score >= 0.75) return { level: "high", text: "high confidence", italic: false };
  if (score >= 0.5) return { level: "mostly", text: "mostly sure", italic: false };
  if (score >= 0.4) return { level: "less", text: "less certain than usual", italic: false };
  return { level: "limited", text: "limited data — gather more", italic: true };
}

function classifyStressQualifier(prob) {
  if (prob >= 0.6) return { level: "high", icon: "⬤", text: "high stress in 24–72h" };
  if (prob >= 0.3) return { level: "moderate", icon: "◐", text: "moderate stress in window" };
  return { level: "low", icon: "○", text: "low stress" };
}

export function buildDecisionCardData(run) {
  const confidenceScore = Number(run?.confidenceScore ?? 0);
  const stressProbability = Number(run?.stressProbability ?? 0);
  const recommendedAmountIn = Number(run?.recommendedAmountIn ?? 0);
  const decision = run?.decision || "wait";
  const timingWindow = run?.timingWindow || "";
  const predicted = run?.predicted || { moisture24h: 0, moisture48h: 0, moisture72h: 0 };
  const currentMoisture = Number(run?.inputSnapshot?.currentMoisture ?? 0);

  const timingSentence = formatWindowSentence(timingWindow);
  const amount = recommendedAmountIn.toFixed(2);

  let state;
  let headline;
  if (confidenceScore < 0.4 || predicted.moisture24h === 0) {
    state = "insufficient";
    headline = "Not enough confident signal yet — gather another moisture reading before acting.";
  } else if (stressProbability >= 0.85) {
    state = "urgent";
    headline = `Stress is high — irrigate ${amount} inches as soon as you can.`;
  } else if (decision === "water" && recommendedAmountIn > 0) {
    state = "action";
    headline = `We think you'll need to irrigate ${amount} inches ${timingSentence}.`;
  } else {
    state = "all-clear";
    headline = `Soil's holding water — no irrigation needed ${timingSentence}.`;
  }

  const forceEmpty = state === "insufficient";
  const forecastStrip = [
    { label: "now", value: currentMoisture, stressLevel: classifyStressTickLevel(currentMoisture), isEmpty: forceEmpty || currentMoisture === 0 },
    { label: "24h", value: predicted.moisture24h, stressLevel: classifyStressTickLevel(predicted.moisture24h), isEmpty: forceEmpty || predicted.moisture24h === 0 },
    { label: "48h", value: predicted.moisture48h, stressLevel: classifyStressTickLevel(predicted.moisture48h), isEmpty: forceEmpty || predicted.moisture48h === 0 },
    { label: "72h", value: predicted.moisture72h, stressLevel: classifyStressTickLevel(predicted.moisture72h), isEmpty: forceEmpty || predicted.moisture72h === 0 },
  ];

  const stressQualifier = state === "insufficient" ? null : classifyStressQualifier(stressProbability);
  const confidenceQualifier = classifyConfidence(confidenceScore);

  return {
    headline,
    state,
    forecastStrip,
    stressQualifier,
    confidenceQualifier,
  };
}

function formatZoneMoistureSummary(zoneMoistureSummary) {
  const entries = Object.entries(zoneMoistureSummary || {});
  if (entries.length === 0) {
    return null;
  }
  return entries
    .map(([sensorId, moisture]) => `${sensorId}: ${(Number(moisture) * 100).toFixed(1)}% VWC`)
    .join(", ");
}

export function recommendationTone(run) {
  return run.decision === "water"
    ? {
        spotlight: "spotlight-water",
        pill: "bg-[var(--accent-warm-soft)] text-[var(--accent-warm)]",
        amount: "text-[var(--accent-warm)]",
      }
    : {
        spotlight: "spotlight-wait",
        pill: "bg-[var(--accent-mint-soft)] text-[var(--accent-mint)]",
        amount: "text-[var(--accent-mint)]",
      };
}

export function serializeRunForCopy(run) {
  const lines = [
    `Run: ${run.title}`,
    `Timestamp: ${formatTimestamp(run.timestamp)}`,
    `Decision: ${run.decision.toUpperCase()}`,
    `Recommended amount: ${run.recommendedAmountIn.toFixed(2)} in`,
    `Timing window: ${formatWindow(run.timingWindow)}`,
    `Heuristic confidence: ${formatPercent(run.confidenceScore)}`,
    `Stress probability: ${formatPercent(run.stressProbability)}`,
    `Reference ET: ${run.estimatedEtIn.toFixed(2)} in/day`,
    `Forecast 24h: ${run.predicted.moisture24h.toFixed(2)}`,
    `Forecast 48h: ${run.predicted.moisture48h.toFixed(2)}`,
    `Forecast 72h: ${run.predicted.moisture72h.toFixed(2)}`,
  ];
  if (run.drivingZone) {
    lines.push(`Driving zone: ${run.drivingZone}`);
  }
  const zoneSummary = formatZoneMoistureSummary(run.zoneMoistureSummary);
  if (zoneSummary) {
    lines.push(`Latest zone moisture: ${zoneSummary}`);
    lines.push(`High variability flag: ${run.highVariabilityFlag ? "Yes" : "No"}`);
  }
  if (run.backendSnapshot) {
    lines.push("");
    lines.push("Build provenance:");
    lines.push(
      `Validation mode: ${
        run.backendSnapshot.validationMode === true
          ? "enabled"
          : run.backendSnapshot.validationMode === false
            ? "disabled"
            : "unknown"
      }`,
    );
    if (run.backendSnapshot.modelHash) {
      lines.push(`Model hash: ${run.backendSnapshot.modelHash}`);
    }
    if (run.backendSnapshot.trainingDate) {
      lines.push(`Training date: ${run.backendSnapshot.trainingDate}`);
    }
    if (run.backendSnapshot.apiVersion) {
      lines.push(`API version: ${run.backendSnapshot.apiVersion}`);
    }
  }
  lines.push("");
  lines.push("Drivers:");
  lines.push(...run.drivers.map((driver) => `- ${driver}`));
  lines.push("");
  lines.push("Prompt:");
  lines.push(run.prompt);
  if (run.recommendationAdjustment) {
    lines.push("");
    lines.push(`Base recommendation: ${run.recommendationAdjustment.baseRecommendationIn.toFixed(2)} in`);
    lines.push(`Adjustment factor: ${run.recommendationAdjustment.adjustmentFactor.toFixed(2)}x`);
    lines.push(`Adjustment reason: ${run.recommendationAdjustment.reason}`);
  }
  if (run.regionalInsights) {
    lines.push(`Regional success rate: ${Math.round(run.regionalInsights.successRate * 100)}%`);
    lines.push(`Regional samples: ${run.regionalInsights.totalSamples}`);
  }
  if (run.sourceLabel) {
    lines.push(`Recommendation source: ${run.sourceLabel}`);
  }
  return lines.join("\n");
}
