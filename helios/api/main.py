from __future__ import annotations

from fastapi import FastAPI

from helios.api.routes import router
from helios.database.db import init_db


app = FastAPI(
    title="Helios",
    description="Local prototype for irrigation decision support.",
    version="0.1.0",
)
app.include_router(router)


@app.on_event("startup")
def on_startup() -> None:
    init_db()
