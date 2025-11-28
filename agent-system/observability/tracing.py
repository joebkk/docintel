"""OpenTelemetry distributed tracing configuration."""

from typing import Optional, Any
from functools import wraps
from contextlib import contextmanager
import asyncio

from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.jaeger.thrift import JaegerExporter
from opentelemetry.sdk.resources import Resource
from opentelemetry.trace import Status, StatusCode

from config import settings


# Global tracer instance
_tracer: Optional[trace.Tracer] = None


def setup_tracing(service_name: str = "docintel-agents"):
    """
    Configure OpenTelemetry tracing with Jaeger backend.

    Args:
        service_name: Name of the service for tracing
    """
    if not settings.enable_tracing:
        return

    global _tracer

    # Create resource with service name
    resource = Resource.create({
        "service.name": service_name,
        "service.version": "1.0.0"
    })

    # Create tracer provider
    provider = TracerProvider(resource=resource)

    # Configure Jaeger exporter
    jaeger_exporter = JaegerExporter(
        agent_host_name="jaeger",  # Docker service name
        agent_port=6831,
    )

    # Add batch span processor
    provider.add_span_processor(
        BatchSpanProcessor(jaeger_exporter)
    )

    # Set as global tracer provider
    trace.set_tracer_provider(provider)

    # Get tracer instance
    _tracer = trace.get_tracer(__name__)


def get_tracer() -> trace.Tracer:
    """Get the global tracer instance."""
    global _tracer

    if _tracer is None:
        # If tracing not set up, return a no-op tracer
        return trace.get_tracer(__name__)

    return _tracer


@contextmanager
def trace_span(
    name: str,
    attributes: Optional[dict[str, Any]] = None
):
    """
    Context manager for creating a trace span.

    Usage:
        with trace_span("research_execution", {"agent": "research", "query": query}):
            result = await agent.execute(query)

    Args:
        name: Span name
        attributes: Optional span attributes
    """
    if not settings.enable_tracing:
        # No-op context manager if tracing disabled
        yield None
        return

    tracer = get_tracer()

    with tracer.start_as_current_span(name) as span:
        if attributes:
            for key, value in attributes.items():
                span.set_attribute(key, str(value))

        try:
            yield span
        except Exception as e:
            span.set_status(Status(StatusCode.ERROR, str(e)))
            span.record_exception(e)
            raise


def trace_async(span_name: Optional[str] = None, attributes_fn=None):
    """
    Decorator for tracing async functions.

    Usage:
        @trace_async("agent_execute")
        async def execute(self, query):
            ...

    Args:
        span_name: Name for the span (defaults to function name)
        attributes_fn: Optional function to extract attributes from args/kwargs
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            if not settings.enable_tracing:
                return await func(*args, **kwargs)

            name = span_name or f"{func.__module__}.{func.__name__}"

            # Extract attributes if function provided
            attributes = {}
            if attributes_fn:
                attributes = attributes_fn(*args, **kwargs)

            with trace_span(name, attributes):
                return await func(*args, **kwargs)

        return wrapper
    return decorator


def trace_sync(span_name: Optional[str] = None, attributes_fn=None):
    """
    Decorator for tracing synchronous functions.

    Usage:
        @trace_sync("memory_lookup")
        def retrieve_memories(self, query):
            ...

    Args:
        span_name: Name for the span (defaults to function name)
        attributes_fn: Optional function to extract attributes from args/kwargs
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            if not settings.enable_tracing:
                return func(*args, **kwargs)

            name = span_name or f"{func.__module__}.{func.__name__}"

            # Extract attributes if function provided
            attributes = {}
            if attributes_fn:
                attributes = attributes_fn(*args, **kwargs)

            with trace_span(name, attributes):
                return func(*args, **kwargs)

        return wrapper
    return decorator


# Helper functions for common tracing scenarios

def trace_agent_execution(agent_name: str):
    """
    Decorator specifically for tracing agent execution.

    Usage:
        @trace_agent_execution("research_agent")
        async def execute(self, query):
            ...
    """
    def attributes_fn(*args, **kwargs):
        # args[0] is self, args[1] is typically the query
        query = args[1] if len(args) > 1 else kwargs.get("query", "")
        return {
            "agent.name": agent_name,
            "agent.query": str(query)[:200]  # Truncate long queries
        }

    return trace_async(
        span_name=f"agent.{agent_name}.execute",
        attributes_fn=attributes_fn
    )


def trace_workflow(workflow_pattern: str):
    """
    Decorator for tracing workflow execution.

    Usage:
        @trace_workflow("sequential")
        async def _execute_sequential(self, workflow, decomposition):
            ...
    """
    def attributes_fn(*args, **kwargs):
        # Extract workflow info
        workflow = args[1] if len(args) > 1 else None
        attrs = {"workflow.pattern": workflow_pattern}

        if workflow and hasattr(workflow, "workflow_id"):
            attrs["workflow.id"] = workflow.workflow_id

        return attrs

    return trace_async(
        span_name=f"workflow.{workflow_pattern}",
        attributes_fn=attributes_fn
    )


def add_span_event(event_name: str, attributes: Optional[dict[str, Any]] = None):
    """
    Add an event to the current span.

    Usage:
        with trace_span("agent_execution"):
            add_span_event("query_decomposed", {"num_queries": 3})
            ...

    Args:
        event_name: Name of the event
        attributes: Optional event attributes
    """
    if not settings.enable_tracing:
        return

    span = trace.get_current_span()
    if span and span.is_recording():
        span.add_event(event_name, attributes or {})


def set_span_attribute(key: str, value: Any):
    """
    Set an attribute on the current span.

    Args:
        key: Attribute key
        value: Attribute value
    """
    if not settings.enable_tracing:
        return

    span = trace.get_current_span()
    if span and span.is_recording():
        span.set_attribute(key, str(value))
