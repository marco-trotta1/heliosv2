export {
  round,
  clip,
  formatPercent,
  formatWindow,
  formatTimestamp,
} from "./domain/format.js";
export {
  estimateReferenceEtIn,
  predictMoistureTrajectory,
  computeStressProbability,
  computeBudgetCap,
  allowedHours,
  selectTimingWindow,
  scoreConfidence,
  generateIrrigationPlan,
  buildDrivers,
  buildSummary,
} from "./domain/recommendations.js";
export { recommendationTone, serializeRunForCopy } from "./domain/output.js";
