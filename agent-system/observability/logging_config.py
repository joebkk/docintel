"""Structured logging configuration for agent system."""

import logging
import sys
from pathlib import Path
from typing import Optional
import structlog
from datetime import datetime

from config import settings


def setup_logging(
    log_level: Optional[str] = None,
    log_file: Optional[str] = None
):
    """
    Configure structured logging for the application.

    Sets up structlog with JSON formatting for production
    and human-readable formatting for development.

    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR)
        log_file: Optional log file path
    """
    level = log_level or settings.log_level
    log_level_int = getattr(logging, level.upper(), logging.INFO)

    # Create logs directory if using file logging
    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)

    # Configure standard logging
    logging.basicConfig(
        format="%(message)s",
        level=log_level_int,
        stream=sys.stdout
    )

    # Add file handler if specified
    if log_file:
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(log_level_int)
        logging.root.addHandler(file_handler)

    # Configure structlog
    processors = [
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
    ]

    # Use JSON renderer for production, ConsoleRenderer for development
    if settings.log_level.upper() == "DEBUG":
        processors.append(structlog.dev.ConsoleRenderer())
    else:
        processors.append(structlog.processors.JSONRenderer())

    structlog.configure(
        processors=processors,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )


def get_logger(name: str) -> structlog.BoundLogger:
    """
    Get a structured logger instance.

    Args:
        name: Logger name (typically __name__)

    Returns:
        Structured logger instance

    Usage:
        logger = get_logger(__name__)
        logger.info("agent_request_started", agent="research", query="...")
    """
    return structlog.get_logger(name)


# Logging utilities

def log_agent_execution(
    logger: structlog.BoundLogger,
    agent_name: str,
    event: str,
    **kwargs
):
    """
    Log agent execution event with standard fields.

    Args:
        logger: Logger instance
        agent_name: Name of the agent
        event: Event description
        **kwargs: Additional context fields
    """
    logger.info(
        event,
        agent=agent_name,
        timestamp=datetime.now().isoformat(),
        **kwargs
    )


def log_rag_api_call(
    logger: structlog.BoundLogger,
    endpoint: str,
    status: str,
    duration_ms: float,
    **kwargs
):
    """
    Log RAG API call with standard fields.

    Args:
        logger: Logger instance
        endpoint: API endpoint called
        status: Call status (success/error)
        duration_ms: Call duration in milliseconds
        **kwargs: Additional context
    """
    logger.info(
        "rag_api_call",
        endpoint=endpoint,
        status=status,
        duration_ms=round(duration_ms, 2),
        **kwargs
    )


def log_workflow_event(
    logger: structlog.BoundLogger,
    workflow_id: str,
    event: str,
    **kwargs
):
    """
    Log workflow execution event.

    Args:
        logger: Logger instance
        workflow_id: Workflow identifier
        event: Event description
        **kwargs: Additional context
    """
    logger.info(
        event,
        workflow_id=workflow_id,
        timestamp=datetime.now().isoformat(),
        **kwargs
    )


def log_error(
    logger: structlog.BoundLogger,
    error: Exception,
    context: str,
    **kwargs
):
    """
    Log an error with context.

    Args:
        logger: Logger instance
        error: Exception that occurred
        context: Description of what was happening
        **kwargs: Additional context
    """
    logger.error(
        "error_occurred",
        error_type=type(error).__name__,
        error_message=str(error),
        context=context,
        **kwargs,
        exc_info=True
    )


# Context managers for logging spans

class LogSpan:
    """
    Context manager for logging a span of execution.

    Usage:
        with LogSpan(logger, "research_execution", agent="research"):
            result = await agent.execute(query)
    """

    def __init__(
        self,
        logger: structlog.BoundLogger,
        span_name: str,
        **context
    ):
        self.logger = logger
        self.span_name = span_name
        self.context = context
        self.start_time = None

    def __enter__(self):
        self.start_time = datetime.now()
        self.logger.info(
            f"{self.span_name}_started",
            **self.context
        )
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        duration = (datetime.now() - self.start_time).total_seconds() * 1000

        if exc_type is None:
            self.logger.info(
                f"{self.span_name}_completed",
                duration_ms=round(duration, 2),
                **self.context
            )
        else:
            self.logger.error(
                f"{self.span_name}_failed",
                duration_ms=round(duration, 2),
                error_type=exc_type.__name__,
                error_message=str(exc_val),
                **self.context
            )

        return False  # Don't suppress exceptions
