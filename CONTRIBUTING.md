# Contributing

## Scope

Helios is an early-stage irrigation decision-support prototype. Keep contributions small, testable, and explicit. Avoid changing predictive behavior or interface contracts unless the change is required and documented.

## Local setup

```bash
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install --upgrade pip
python3 -m pip install -r requirements-dev.txt
```

Optional training flow for backend readiness:

```bash
python3 -m helios.scripts.generate_sample_data --rows 2500
python3 -m helios.models.train_model
```

## Run tests

```bash
pytest
```

The GitHub Actions workflow runs the same test command on Python 3.11.

## Branch and PR guidance

- Create a focused branch from `main`.
- Keep PRs narrow and explain user-facing impact.
- Update docs when setup, dependencies, or runtime behavior changes.
- Include tests for backend or schema changes when practical.
- Do not commit secrets, generated local databases, model artifacts, or notebook checkpoints.

## Review expectations

- Preserve current product behavior unless the PR clearly states otherwise.
- Prefer conservative fixes over speculative refactors.
- Call out known limitations rather than hiding them.
