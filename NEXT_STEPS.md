# Next Steps

1. Continue replacing synthetic training assumptions with evaluated real field datasets. USDA LIRF 2012-2013 is now parsed and evaluated as a candidate, but it failed the current cross-season persistence gate, so it was not promoted into shipped model artifacts.
2. Add authentication and tenant isolation before exposing feedback submission on any public deployment.
3. Move prototype rate limiting from in-memory storage to an external store if the API will face public traffic.
4. Add database migrations instead of lightweight SQLite column patching as the schema continues to evolve.
5. Calibrate or replace the current heuristic confidence score with a more defensible uncertainty estimate.
6. Add operator-visible provenance for each recommendation, including model version and artifact timestamp.
7. Persist frontend run history server-side when in live mode instead of only in browser local storage.
8. Add seasonality and geography-aware comparability rules using real agronomic metadata rather than simple month weighting.
9. CI exists for `python3 -m pytest -q` on push/PR to `main`; keep new tests inside that suite.
10. Add explicit operator acknowledgement flows for high-impact recommendations so the prototype cannot be mistaken for an autonomous controller.
11. Add a registry/downloader/parser path for USDA LIRF 2008-2011 (`10.15482/USDA.ADC/1254006`) and evaluate it through the same candidate gates before any training promotion.
