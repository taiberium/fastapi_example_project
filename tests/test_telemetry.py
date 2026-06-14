from fastapi import FastAPI

from app.core import telemetry
from app.core.settings import settings


def test_configure_telemetry_is_noop_when_disabled(monkeypatch) -> None:
    # Disabled is the default — it must never reach for a collector, so tests
    # and local runs work with no OTLP endpoint up.
    monkeypatch.setattr(settings, "otel_enabled", False)
    monkeypatch.setattr(telemetry, "_INSTRUMENTED", False)

    assert telemetry.configure_telemetry(FastAPI()) is False


def test_configure_telemetry_skips_when_already_instrumented(monkeypatch) -> None:
    # Guard so re-creating the app (e.g. in tests) can't double-instrument or
    # re-export — even with telemetry enabled, an already-wired process is a no-op.
    monkeypatch.setattr(settings, "otel_enabled", True)
    monkeypatch.setattr(telemetry, "_INSTRUMENTED", True)

    assert telemetry.configure_telemetry(FastAPI()) is False
