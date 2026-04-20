# Kimberly Test Checklist

Field test date: Tuesday, April 21, 2026

## Monday Must-Do

1. Freeze the test build.

```bash
HELIOS_VALIDATION_MODE=1 python3 -m helios.scripts.validation_preflight \
  --output artifacts/kimberly-validation-manifest.json
```

2. Record the API build state.

```bash
curl -s http://localhost:8000/version
curl -s http://localhost:8000/health
```

3. Run the test suite once from the exact environment you plan to use.

```bash
python3 -m pytest -q
```

4. Confirm `HELIOS_VALIDATION_MODE=1` is set in the backend environment for the field test.

5. Confirm the model artifact and metadata file on disk match the manifest you just froze.

## Before First Field Reading

1. Decide the official scoring rule and write it down:
   `driest sensor`, `mean sensor value`, or `one fixed reference probe`.

2. Keep that rule fixed for the whole test.

3. Verify each submitted sensor has:
   - a stable `sensor_id`
   - at least 3 timestamped readings
   - a consistent field ID

4. Confirm the researchers know Helios currently predicts:
   - `24h`
   - `48h`
   - `72h`

5. Confirm everyone understands Helios is being tested as a research-stage decision-support prototype, not a production-autonomous scheduler.

## Per-Test-Run Capture

Record:

- timestamp
- field ID
- sensor ID
- depth
- observed VWC
- weather used
- recent irrigation
- crop type
- growth stage
- Helios 24h / 48h / 72h forecast
- Helios decision
- Helios recommended amount
- notes on any anomaly

## Do Not Change On Test Day

- git commit
- model artifact
- metadata file
- scoring rule
- validation mode setting

## Success Standard

The cleanest claim you can make after Kimberly is:

- Helios was prospectively tested on-farm under a frozen build
- the protocol matched the deployed model behavior
- the observed MAE and bias were measured against a predefined reference rule

Anything stronger than that should wait for the actual results.
