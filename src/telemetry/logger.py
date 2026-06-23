"""
Structured Logging — JSON-formatted, machine-parseable logs.

Uses structlog for structured logging throughout the application.
All logs are JSON-formatted for easy ingestion into Supabase
or any log aggregation system.
"""

import structlog


def setup_logging(log_level: str = "info"):
    """Configure structlog for the application."""
    structlog.configure(
        processors=[
            structlog.stdlib.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.stdlib.BoundLogger,
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )
