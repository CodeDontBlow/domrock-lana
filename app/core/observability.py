import logging
import os
from typing import Any

logger = logging.getLogger(__name__)


def configure_otel(app: Any) -> None:
    """Ativa instrumentação OpenTelemetry OTLP HTTP apenas quando OTEL_EXPORTER_OTLP_ENDPOINT está definida."""
    endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "").strip()
    if not endpoint:
        return

    try:
        from opentelemetry import trace
        from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
        from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
        from opentelemetry.sdk.resources import Resource
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor

        service_name = os.getenv("OTEL_SERVICE_NAME", "domrock-lana").strip() or "domrock-lana"
        resource = Resource.create({"service.name": service_name})
        provider = TracerProvider(resource=resource)
        provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter()))
        trace.set_tracer_provider(provider)
        FastAPIInstrumentor.instrument_app(app)
        logger.info("OpenTelemetry OTLP HTTP habilitado para %s", service_name)
    except Exception as exc:
        logger.warning("Falha ao inicializar OpenTelemetry OTLP: %s", exc)


def get_langfuse_callbacks(thread_id: str | None = None) -> list[Any]:
    """Retorna CallbackHandler do Langfuse apenas quando LANGFUSE_PUBLIC_KEY e LANGFUSE_SECRET_KEY estão definidas."""
    public_key = os.getenv("LANGFUSE_PUBLIC_KEY", "").strip()
    secret_key = os.getenv("LANGFUSE_SECRET_KEY", "").strip()
    if not (public_key and secret_key):
        return []

    try:
        try:
            from langfuse.langchain import CallbackHandler
        except ImportError:
            from langfuse.callback import CallbackHandler

        handler = CallbackHandler()
        return [handler]
    except Exception as exc:
        logger.warning("Falha ao inicializar callback do Langfuse (chat_id=%s): %s", thread_id, exc)
        return []
