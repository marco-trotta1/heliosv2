// ── Client-side input validation (Phase 4B) ────────────────────────────────────

/**
 * Validates the form state object.
 * Returns a human-readable error string on failure, or null on success.
 *
 * @param {object} form
 * @returns {string | null}
 */
export function validateForm(form) {
  // Field identification
  if (!form.fieldName || String(form.fieldName).trim().length === 0) {
    return "Field name is required.";
  }

  // Location
  const lat = Number(form.locationLat);
  const lon = Number(form.locationLon);
  if (Number.isNaN(lat) || lat < -90 || lat > 90) {
    return "Latitude must be between -90 and 90.";
  }
  if (Number.isNaN(lon) || lon < -180 || lon > 180) {
    return "Longitude must be between -180 and 180.";
  }

  // Soil moisture readings — must be plausible volumetric water content (0–1)
  const currentMoisture = Number(form.currentMoisture);
  const lagOne = Number(form.lagOneMoisture);
  const lagTwo = Number(form.lagTwoMoisture);
  if (Number.isNaN(currentMoisture) || currentMoisture < 0 || currentMoisture > 1) {
    return "Current soil moisture must be between 0 and 1.";
  }
  if (Number.isNaN(lagOne) || lagOne < 0 || lagOne > 1) {
    return "6-hour lag moisture must be between 0 and 1.";
  }
  if (Number.isNaN(lagTwo) || lagTwo < 0 || lagTwo > 1) {
    return "12-hour lag moisture must be between 0 and 1.";
  }

  // Weather
  const tempC = Number(form.temperatureC);
  if (Number.isNaN(tempC) || tempC < -50 || tempC > 70) {
    return "Temperature must be between -50 °C and 70 °C.";
  }
  const humidity = Number(form.humidityPct);
  if (Number.isNaN(humidity) || humidity < 0 || humidity > 100) {
    return "Relative humidity must be between 0% and 100%.";
  }
  const wind = Number(form.windMps);
  if (Number.isNaN(wind) || wind < 0 || wind > 75) {
    return "Wind speed must be between 0 and 75 m/s.";
  }
  const precip = Number(form.precipitationMm);
  if (Number.isNaN(precip) || precip < 0) {
    return "Precipitation cannot be negative.";
  }
  const solar = Number(form.solarRadiationMjM2);
  if (Number.isNaN(solar) || solar < 0 || solar > 50) {
    return "Solar radiation must be between 0 and 50 MJ/m².";
  }

  // Operational
  const fieldArea = Number(form.fieldAreaHa);
  if (Number.isNaN(fieldArea) || fieldArea <= 0) {
    return "Field area must be a positive number.";
  }
  const pumpCap = Number(form.pumpCapacity);
  if (Number.isNaN(pumpCap) || pumpCap <= 0) {
    return "Pump capacity must be a positive number.";
  }
  const maxVol = Number(form.maxIrrigationVolume);
  if (Number.isNaN(maxVol) || maxVol < 0) {
    return "Maximum irrigation volume cannot be negative.";
  }
  const budget = Number(form.budgetDollars);
  if (Number.isNaN(budget) || budget < 0) {
    return "Budget cannot be negative.";
  }

  // Soil
  const infiltration = Number(form.infiltrationRate);
  if (Number.isNaN(infiltration) || infiltration <= 0) {
    return "Infiltration rate must be a positive number.";
  }
  const slope = Number(form.slopePct);
  if (Number.isNaN(slope) || slope < 0 || slope > 100) {
    return "Slope must be between 0% and 100%.";
  }

  // Irrigation windows — at least one water window required to allow scheduling
  if (!Array.isArray(form.waterWindow) || form.waterWindow.length === 0) {
    return "At least one water availability window must be selected.";
  }

  return null;
}
