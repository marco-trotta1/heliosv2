import { formatPercent, formatTimestamp, formatWindow } from "./format.js";

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
