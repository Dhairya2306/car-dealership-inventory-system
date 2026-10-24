"""Application entry point; feature routers will be added incrementally."""

from fastapi import FastAPI

app = FastAPI(title="Car Dealership Inventory", version="0.1.0")


@app.get("/api/health", tags=["health"])
def health() -> dict[str, str]:
    """Process liveness only; this does not check database readiness."""
    return {"status": "ok"}
