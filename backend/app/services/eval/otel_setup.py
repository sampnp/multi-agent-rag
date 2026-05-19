"""
OpenTelemetry setup.
Activates only when OTEL_EXPORTER_OTLP_ENDPOINT is configured.
Falls back to console span export for local debugging.
"""
from app.config import settings


def setup_otel(app) -> None:
    endpoint = getattr(settings, "OTEL_EXPORTER_OTLP_ENDPOINT", None)
    try:
        from opentelemetry import trace
        from opentelemetry.sdk.resources import Resource
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter
        from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

        resource = Resource.create({"service.name": "enterprise-ai-os"})
        provider = TracerProvider(resource=resource)

        if endpoint:
            from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
            exporter = OTLPSpanExporter(endpoint=endpoint)
        else:
            exporter = ConsoleSpanExporter()

        provider.add_span_processor(BatchSpanProcessor(exporter))
        trace.set_tracer_provider(provider)
        FastAPIInstrumentor.instrument_app(app)
    except ImportError:
        pass  # OTel packages not installed — skip silently
    except Exception:
        pass
