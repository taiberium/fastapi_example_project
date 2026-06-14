"""OpenTelemetry wiring: export traces, metrics, and logs over OTLP/HTTP.

A no-op unless ``APP_OTEL_ENABLED=true`` — local runs and tests never need a
collector. When on, it points the SDK at ``settings.otel_exporter_otlp_endpoint``
(our Grafana stack's OTLP collector) and auto-instruments FastAPI.
"""

import logging

from fastapi import FastAPI

from app.core.settings import settings

log = logging.getLogger(__name__)

# Module-level guard: re-creating the app (tests) must not double-instrument.
_INSTRUMENTED = False


def configure_telemetry(app: FastAPI) -> bool:
    """Enable OTLP export for ``app``. Returns True only when it instruments now."""
    global _INSTRUMENTED
    if not settings.otel_enabled or _INSTRUMENTED:
        return False

    # Imported lazily so the OTel SDK is only required when telemetry is on.
    from opentelemetry import metrics, trace
    from opentelemetry.exporter.otlp.proto.http._log_exporter import OTLPLogExporter
    from opentelemetry.exporter.otlp.proto.http.metric_exporter import (
        OTLPMetricExporter,
    )
    from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
    from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
    from opentelemetry.sdk._logs import LoggerProvider, LoggingHandler
    from opentelemetry.sdk._logs.export import BatchLogRecordProcessor
    from opentelemetry.sdk.metrics import MeterProvider
    from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
    from opentelemetry.sdk.resources import Resource
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor

    base = settings.otel_exporter_otlp_endpoint.rstrip("/")
    resource = Resource.create({"service.name": settings.otel_service_name})

    tracer_provider = TracerProvider(resource=resource)
    tracer_provider.add_span_processor(
        BatchSpanProcessor(OTLPSpanExporter(endpoint=f"{base}/v1/traces"))
    )
    trace.set_tracer_provider(tracer_provider)

    meter_provider = MeterProvider(
        resource=resource,
        metric_readers=[
            PeriodicExportingMetricReader(
                OTLPMetricExporter(endpoint=f"{base}/v1/metrics")
            )
        ],
    )
    metrics.set_meter_provider(meter_provider)

    # Route stdlib logging into OTLP — sits alongside the existing console handler.
    logger_provider = LoggerProvider(resource=resource)
    logger_provider.add_log_record_processor(
        BatchLogRecordProcessor(OTLPLogExporter(endpoint=f"{base}/v1/logs"))
    )
    logging.getLogger().addHandler(
        LoggingHandler(level=logging.NOTSET, logger_provider=logger_provider)
    )

    # HTTP server spans + per-request metrics, emitted via the providers above.
    FastAPIInstrumentor.instrument_app(
        app, tracer_provider=tracer_provider, meter_provider=meter_provider
    )

    _INSTRUMENTED = True
    log.info(
        "OpenTelemetry enabled -> %s (service=%s)", base, settings.otel_service_name
    )
    return True
