import { runtimeConfig } from "../state.js";

const IDAHO_SOLAR_MJ_M2 = {
  1: 7.5,
  2: 10.8,
  3: 15.2,
  4: 19.8,
  5: 23.4,
  6: 26.1,
  7: 26.8,
  8: 23.9,
  9: 18.7,
  10: 12.4,
  11: 7.8,
  12: 6.2,
};

export function apiUrl(path) {
  return runtimeConfig.apiBaseUrl ? `${runtimeConfig.apiBaseUrl}${path}` : path;
}

export async function readJsonResponse(response) {
  const text = await response.text();
  if (!text) {
    return {};
  }
  try {
    return JSON.parse(text);
  } catch {
    return { detail: text };
  }
}

function seasonalSolarRadiationEstimate() {
  const month = new Date().getMonth() + 1;
  return IDAHO_SOLAR_MJ_M2[month];
}

function parseWindMph(windSpeed) {
  const matches = String(windSpeed || "").match(/\d+(?:\.\d+)?/g) || [];
  if (matches.length === 0) {
    throw new Error("NOAA forecast is missing a parseable wind speed.");
  }
  const values = matches.map(Number);
  return Number((values.reduce((sum, value) => sum + value, 0) / values.length).toFixed(2));
}

export async function fetchNOAAWeather(lat, lon) {
  try {
    const pointsResponse = await fetch(`https://api.weather.gov/points/${lat},${lon}`, {
      headers: {
        Accept: "application/geo+json, application/json",
      },
    });
    if (!pointsResponse.ok) {
      throw new Error(`NOAA points lookup failed with status ${pointsResponse.status}`);
    }
    const pointsJson = await readJsonResponse(pointsResponse);
    const forecastHourlyUrl = pointsJson.properties?.forecastHourly;
    if (typeof forecastHourlyUrl !== "string" || forecastHourlyUrl.length === 0) {
      throw new Error("NOAA points lookup did not return forecastHourly.");
    }

    const forecastResponse = await fetch(forecastHourlyUrl, {
      headers: {
        Accept: "application/geo+json, application/json",
      },
    });
    if (!forecastResponse.ok) {
      throw new Error(`NOAA hourly forecast failed with status ${forecastResponse.status}`);
    }
    const forecastJson = await readJsonResponse(forecastResponse);
    const period = forecastJson.properties?.periods?.[0];
    if (!period) {
      throw new Error("NOAA hourly forecast did not include any periods.");
    }
    if (period.temperature == null || period.relativeHumidity?.value == null) {
      throw new Error("NOAA hourly forecast is missing temperature or humidity.");
    }

    return {
      temperatureF: Number(period.temperature),
      humidityPct: Number(period.relativeHumidity.value),
      windMph: parseWindMph(period.windSpeed),
      precipitationIn: Number(period.probabilityOfPrecipitation?.value || 0) > 50 ? 0.1 : 0.0,
      solarRadiationMjM2: seasonalSolarRadiationEstimate(),
    };
  } catch (error) {
    console.error("[helios] NOAA weather auto-population failed", error);
    return null;
  }
}
