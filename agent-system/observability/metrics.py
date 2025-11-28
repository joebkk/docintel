"""Prometheus metrics for agent system monitoring."""

from prometheus_client import (
    Counter,
    Histogram,
    Gauge,
    CollectorRegistry,
    generate_latest,
    CONTENT_TYPE_LATEST
)
import time
from typing import Optional
from functools import wraps
import asyncio

from config import settings


# Create registry
metrics_registry = CollectorRegistry()

# Agent request metrics
agent_requests_total = Counter(
    'agent_requests_total',
    'Total number of agent requests',
    ['agent_name', 'status'],
    registry=metrics_registry
)

agent_request_duration_seconds = Histogram(
    'agent_request_duration_seconds',
    'Agent request duration in seconds',
    ['agent_name'],
    buckets=(0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0, 60.0),
    registry=metrics_registry
)

# RAG API call metrics
rag_api_calls_total = Counter(
    'rag_api_calls_total',
    'Total RAG API calls',
    ['endpoint', 'status'],
    registry=metrics_registry
)

rag_api_duration_seconds = Histogram(
    'rag_api_duration_seconds',
    'RAG API call duration in seconds',
    ['endpoint'],
    buckets=(0.1, 0.5, 1.0, 2.0, 5.0, 10.0),
    registry=metrics_registry
)

# Memory Bank metrics
memory_bank_lookups_total = Counter(
    'memory_bank_lookups_total',
    'Total Memory Bank lookups',
    ['memory_type', 'hit'],
    registry=metrics_registry
)

memory_bank_storage_operations = Counter(
    'memory_bank_storage_operations',
    'Total Memory Bank storage operations',
    ['operation'],  # store, update, delete
    registry=metrics_registry
)

# Session metrics
agent_active_sessions = Gauge(
    'agent_active_sessions',
    'Number of active agent sessions',
    registry=metrics_registry
)

# LLM metrics
llm_tokens_total = Counter(
    'llm_tokens_total',
    'Total LLM tokens consumed',
    ['model', 'token_type'],  # token_type: input, output
    registry=metrics_registry
)

llm_api_calls_total = Counter(
    'llm_api_calls_total',
    'Total LLM API calls',
    ['model', 'status'],
    registry=metrics_registry
)

llm_api_duration_seconds = Histogram(
    'llm_api_duration_seconds',
    'LLM API call duration in seconds',
    ['model'],
    buckets=(0.5, 1.0, 2.0, 5.0, 10.0, 30.0),
    registry=metrics_registry
)

# Workflow metrics
workflow_executions_total = Counter(
    'workflow_executions_total',
    'Total workflow executions',
    ['execution_pattern', 'status'],
    registry=metrics_registry
)

workflow_duration_seconds = Histogram(
    'workflow_duration_seconds',
    'Workflow execution duration in seconds',
    ['execution_pattern'],
    buckets=(1.0, 5.0, 10.0, 30.0, 60.0, 120.0, 300.0),
    registry=metrics_registry
)

workflow_tasks_total = Counter(
    'workflow_tasks_total',
    'Total workflow tasks executed',
    ['task_type', 'status'],
    registry=metrics_registry
)


# Helper functions for tracking metrics

def track_agent_request(agent_name: str):
    """
    Decorator to track agent request metrics.

    Usage:
        @track_agent_request("research_agent")
        async def execute(self, query):
            ...
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            start_time = time.time()
            status = "success"

            try:
                result = await func(*args, **kwargs)
                return result
            except Exception as e:
                status = "error"
                raise
            finally:
                duration = time.time() - start_time
                agent_requests_total.labels(
                    agent_name=agent_name,
                    status=status
                ).inc()
                agent_request_duration_seconds.labels(
                    agent_name=agent_name
                ).observe(duration)

        return wrapper
    return decorator


def track_rag_api_call(endpoint: str):
    """
    Decorator to track RAG API call metrics.

    Usage:
        @track_rag_api_call("unified-search")
        async def search_documents(self, query):
            ...
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            start_time = time.time()
            status = "success"

            try:
                result = await func(*args, **kwargs)

                # Check if result contains error
                if isinstance(result, dict) and "error" in result:
                    status = "error"

                return result
            except Exception as e:
                status = "error"
                raise
            finally:
                duration = time.time() - start_time
                rag_api_calls_total.labels(
                    endpoint=endpoint,
                    status=status
                ).inc()
                rag_api_duration_seconds.labels(
                    endpoint=endpoint
                ).observe(duration)

        return wrapper
    return decorator


def track_memory_lookup(memory_type: str = "general"):
    """
    Decorator to track Memory Bank lookup metrics.

    Usage:
        @track_memory_lookup("fact")
        def retrieve_memories(self, ...):
            ...
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            result = func(*args, **kwargs)

            # Determine if lookup was a hit
            hit = "true" if (result and len(result) > 0) else "false"

            memory_bank_lookups_total.labels(
                memory_type=memory_type,
                hit=hit
            ).inc()

            return result

        return wrapper
    return decorator


def track_llm_call(model_name: str):
    """
    Decorator to track LLM API call metrics.

    Usage:
        @track_llm_call("gemini-2.0-flash-exp")
        async def generate_content_async(self, prompt):
            ...
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            start_time = time.time()
            status = "success"

            try:
                result = await func(*args, **kwargs)

                # Track tokens if available (Gemini doesn't always provide this)
                # This would need to be integrated with actual token counting

                return result
            except Exception as e:
                status = "error"
                raise
            finally:
                duration = time.time() - start_time
                llm_api_calls_total.labels(
                    model=model_name,
                    status=status
                ).inc()
                llm_api_duration_seconds.labels(
                    model=model_name
                ).observe(duration)

        return wrapper
    return decorator


def update_active_sessions(count: int):
    """
    Update the active sessions gauge.

    Args:
        count: Current number of active sessions
    """
    agent_active_sessions.set(count)


def record_memory_operation(operation: str):
    """
    Record a Memory Bank storage operation.

    Args:
        operation: Operation type (store, update, delete)
    """
    memory_bank_storage_operations.labels(operation=operation).inc()


def record_workflow_execution(
    execution_pattern: str,
    duration: float,
    status: str = "success"
):
    """
    Record workflow execution metrics.

    Args:
        execution_pattern: Pattern type (sequential, parallel, loop)
        duration: Execution duration in seconds
        status: Execution status (success, error)
    """
    workflow_executions_total.labels(
        execution_pattern=execution_pattern,
        status=status
    ).inc()

    workflow_duration_seconds.labels(
        execution_pattern=execution_pattern
    ).observe(duration)


def record_workflow_task(task_type: str, status: str):
    """
    Record individual workflow task.

    Args:
        task_type: Type of task (research, analysis, citation)
        status: Task status (pending, in_progress, completed, failed)
    """
    workflow_tasks_total.labels(
        task_type=task_type,
        status=status
    ).inc()


def get_metrics() -> tuple[str, str]:
    """
    Get current metrics in Prometheus format.

    Returns:
        Tuple of (metrics_content, content_type)
    """
    return generate_latest(metrics_registry), CONTENT_TYPE_LATEST
