from fastapi import FastAPI
from prometheus_client import CollectorRegistry
from prometheus_fastapi_instrumentator import Instrumentator


def setup_metrics(app: FastAPI) -> None:
    """Expose Prometheus HTTP metrics at /metrics.

    A fresh registry per app instance keeps re-creating the app (e.g. in tests)
    from raising duplicate-timeseries errors on the global registry.
    """
    registry = CollectorRegistry()
    Instrumentator(registry=registry).instrument(app).expose(
        app, endpoint="/metrics", include_in_schema=False
    )
