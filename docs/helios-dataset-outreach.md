# Helios Dataset Outreach Guide

## Purpose

Helios needs datasets that improve irrigation recommendation accuracy, especially measured field outcomes that can replace synthetic or heuristic training labels. A partner does not need to have every category below. Even one clean category can help if it is timestamped, tied to a field, and can be matched to crop, soil, weather, irrigation, or future soil moisture outcomes.

## Highest-Value Dataset Categories

### 1. Field-Validated Soil Moisture Outcomes

This is the most valuable category.

Ask for:
- Field ID or field boundary
- Timestamped sensor readings
- Sensor ID, depth, zone, and calibration status
- Volumetric water content at prediction time
- Observed volumetric water content 24, 48, and 72 hours later
- Notes on probe failures, maintenance, or questionable readings

Why it matters:
Helios predicts soil moisture at 24, 48, and 72 hours. Real observed values at those horizons are the direct ground truth needed to train and validate the model.

### 2. Actual Irrigation Application Logs

Ask for:
- Irrigation start and stop timestamps
- Applied inches or acre-feet
- Flow rate in gpm
- Pump runtime
- Pressure, pivot speed, nozzle package, or drip/flood setup
- Planned amount versus actual amount
- Water source, rotation, curtailment, or delivery constraint notes

Why it matters:
Irrigation is one of the strongest drivers of future soil moisture. Helios currently needs better evidence for what water actually reached the field, not just what was recommended or estimated.

### 3. Multi-Depth Sensor Network Metadata

Ask for:
- Sensor vendor and probe type
- Sensor ID and installation date
- Depth, GPS/row position, and zone
- Raw VWC time series
- Soil-specific calibration coefficients
- Maintenance, relocation, or anomaly flags

Why it matters:
Helios uses sensor readings to identify the driest zone, moisture trend, spread across zones, and confidence. Better sensor metadata improves both the forecast and the trustworthiness of the displayed recommendation.

### 4. Soil Physical Properties

Ask for:
- Soil texture by field, zone, or depth
- Field capacity
- Wilting point
- Available water capacity
- Bulk density
- Infiltration rate
- Drainage class
- Slope and topography
- Root-zone depth
- Lab report, NRCS/SSURGO source, or consultant notes

Why it matters:
Helios currently uses simplified soil classes and hardcoded thresholds. Field-specific soil properties can calibrate dry/wet thresholds and recommended irrigation depth.

### 5. Crop, Phenology, and Management History

Ask for:
- Crop type and variety
- Planting date
- Emergence, vegetative, flowering, grain fill, maturity, and harvest dates
- Observed growth stage by date
- Crop coefficient notes or local extension guidance
- Canopy cover, NDVI, or scouting notes
- Rooting depth observations

Why it matters:
Helios treats crop stage as a major driver of water demand and stress. Local crop-stage data helps replace generic assumptions with farm-specific timing.

### 6. Weather, Rainfall, Solar, and ET

Ask for:
- On-farm weather station data
- Hourly or daily temperature, humidity, wind, and rainfall
- Solar radiation or pyranometer readings
- Forecast issue time and forecast values used for decisions
- AgriMet, gridMET, OpenET, or other ET source
- Field-polygon daily ET if available

Why it matters:
Helios uses weather and ET to forecast drying and stress. Better rainfall, solar, and field-level ET reduce error in near-term moisture forecasts.

### 7. Field Boundaries and Crop Maps

Ask for:
- Field polygon or shapefile
- Acreage
- Crop by field and season
- Planting and harvest windows
- Irrigation method by field
- Field-zone boundaries if variable management is used

Why it matters:
Field polygons make it possible to join sensor, ET, soil, weather, crop, and yield data to the correct place instead of relying on a single latitude/longitude point.

### 8. Recommendation Outcomes, Yield, and Quality

Ask for:
- Whether the operator followed the recommendation
- Actual action taken if they did not follow it
- Researcher or operator water/wait judgment
- Crop stress observations
- Yield by field or zone
- Potato grade, quality, or other crop-specific quality metrics
- Water and energy cost if available

Why it matters:
Helios needs to know not just whether the moisture forecast was close, but whether the recommendation led to better agronomic and economic outcomes.

## Public and Semi-Public Data Worth Using

- USBR AgriMet: weather and crop water use data.
- NRCS SCAN: soil moisture and weather station data.
- NRCS SSURGO/gSSURGO: soil texture, drainage, hydrologic group, and available water capacity.
- NASA SMAP: broad soil-moisture context.
- USDA NASS Cropland Data Layer and CropScape: crop identity and crop map validation.
- OpenET: ET data, ideally daily or field-polygon rather than monthly point estimates.
- NOAA/NBM/HRRR: weather history and quantitative precipitation forecasts.

## Minimum Useful Dataset

If a partner has only one type of data, ask whether it includes:
- A timestamp
- A field identifier or location
- Units
- Sensor/source name
- Crop and season if known
- Notes on whether values are measured, estimated, or manually entered

If those six fields exist, the data may still be useful.

## Ideal Row-Level Schema

For partners with more structured data, the ideal dataset contains:

`field_id`, `farm_id`, `timestamp`, `latitude`, `longitude`, `field_polygon`, `crop_type`, `variety`, `growth_stage`, `planting_date`, `soil_texture`, `field_capacity`, `wilting_point`, `available_water_capacity`, `infiltration_rate`, `drainage_class`, `sensor_id`, `sensor_depth`, `volumetric_water_content`, `irrigation_start`, `irrigation_end`, `applied_inches`, `flow_gpm`, `rain_inches`, `reference_et`, `actual_et`, `temperature_f`, `humidity_pct`, `wind_mph`, `solar_radiation`, `helios_decision`, `helios_recommended_inches`, `observed_vwc_24h`, `observed_vwc_48h`, `observed_vwc_72h`, `researcher_water_wait_judgment`, `operator_action`, `yield`, `quality_grade`, `notes`.

## Exact Email Template

Subject: Data partnership request to improve Helios irrigation accuracy

Hi [Name],

I am reaching out from Irrigant Helios. We are building an irrigation recommendation system that predicts field soil moisture over the next 24, 48, and 72 hours, then recommends whether to irrigate, how much to apply, and when to apply it.

We are looking for real field datasets that can help us improve and validate the accuracy of Helios. You do not need to have every type of data. Even one clean dataset may be useful if it is timestamped and tied to a field, sensor, crop, irrigation event, or measured outcome.

The highest-value data for us would be any of the following:

1. Soil moisture readings, especially observed VWC 24, 48, or 72 hours after an irrigation decision.
2. Actual irrigation logs, including applied inches, flow rate, pump runtime, pressure, pivot speed, or start/stop times.
3. Sensor metadata, including sensor ID, depth, field zone, calibration notes, and maintenance flags.
4. Soil properties, including texture, field capacity, wilting point, infiltration, drainage, slope, or lab/NRCS reports.
5. Crop and growth-stage history, including planting dates, crop type, variety, observed growth stage, and harvest dates.
6. Weather, rainfall, solar radiation, ET, AgriMet, OpenET, or on-farm weather station data.
7. Field boundaries, acreage, crop maps, or irrigation system maps.
8. Outcome data, including operator water/wait judgment, crop stress notes, yield, quality grade, or water/energy cost.

If helpful, we can work with partial exports, spreadsheets, CSVs, shapefiles, raw sensor downloads, screenshots of report structures, or a short call where we map what you already have. We can also start with a small sample before discussing any broader data-sharing process.

Would you be open to a 20-minute call to see whether any of your existing data could help us validate or improve Helios?

Best,

[Your Name]

## Follow-Up Questions for a Call

- What fields or crops does the data cover?
- What seasons or years are available?
- Are readings tied to field IDs, sensor IDs, or GPS coordinates?
- Are irrigation events measured, estimated, or manually entered?
- Is future soil moisture available after irrigation events?
- Are sensor depths and calibration notes available?
- Are field boundaries or acreage available?
- Are yield or quality outcomes available?
- What format is easiest to export: CSV, Excel, shapefile, API, or raw vendor download?

## Prioritization Rule

If a partner asks what matters most, use this order:

1. Measured future VWC at 24, 48, and 72 hours.
2. Actual applied water and timing.
3. Sensor depth, calibration, and metadata.
4. Field soil properties.
5. Crop stage and planting history.
6. Local weather, rainfall, and ET.
7. Field boundaries and crop maps.
8. Yield, quality, stress, and operator judgment.
