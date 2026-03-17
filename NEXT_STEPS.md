# Next Steps

1. Replace synthetic training data with real field datasets and document provenance, coverage, and bias limits.
2. Add authentication and tenant isolation before exposing feedback submission on any public deployment.
3. Move prototype rate limiting from in-memory storage to an external store if the API will face public traffic.
4. Add database migrations instead of lightweight SQLite column patching as the schema continues to evolve.
5. Calibrate or replace the current heuristic confidence score with a more defensible uncertainty estimate.
6. Add operator-visible provenance for each recommendation, including model version and artifact timestamp.
7. Persist frontend run history server-side when in live mode instead of only in browser local storage.
8. Add seasonality and geography-aware comparability rules using real agronomic metadata rather than simple month weighting.
9. Introduce a small CI workflow that runs `python3 -m pytest -q` on every push.
10. Add explicit operator acknowledgement flows for high-impact recommendations so the prototype cannot be mistaken for an autonomous controller.
