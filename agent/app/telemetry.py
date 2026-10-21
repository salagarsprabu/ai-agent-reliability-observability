import os
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor


def configure_tracing(service_name: str) -> None:
    resource = Resource.create({
        "service.name": service_name,
        "service.version": "0.1.0",
        "deployment.environment.name": "development",
    })
    provider = TracerProvider(resource=resource)
    endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://localhost:4318")
    provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter(endpoint=f"{endpoint}/v1/traces")))
    trace.set_tracer_provider(provider)


def current_trace_id() -> str:
    context = trace.get_current_span().get_span_context()
    return format(context.trace_id, "032x") if context.is_valid else ""
