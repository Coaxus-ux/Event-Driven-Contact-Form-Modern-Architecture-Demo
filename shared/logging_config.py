"""
Shared logging configuration for all services in the event-driven architecture.
Provides structured JSON logging with correlation IDs and service context.
"""

import json
import logging
import logging.config
import os
import sys
import traceback
from datetime import datetime, timezone
from typing import Any, Dict, Optional
import uuid


class JSONFormatter(logging.Formatter):
    """Custom JSON formatter for structured logging."""
    
    def __init__(self, service_name: str, service_version: str = "1.0.0"):
        super().__init__()
        self.service_name = service_name
        self.service_version = service_version
        self.hostname = os.getenv('HOSTNAME', 'localhost')
        self.environment = os.getenv('ENVIRONMENT', 'development')
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON."""
        # Base log structure
        log_entry = {
            'timestamp': datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat(),
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'service': {
                'name': self.service_name,
                'version': self.service_version,
                'hostname': self.hostname,
                'environment': self.environment
            },
            'process': {
                'pid': os.getpid(),
                'thread_id': record.thread,
                'thread_name': record.threadName
            },
            'location': {
                'file': record.filename,
                'line': record.lineno,
                'function': record.funcName,
                'module': record.module
            }
        }
        
        # Add correlation ID if available
        correlation_id = getattr(record, 'correlation_id', None)
        if correlation_id:
            log_entry['correlation_id'] = correlation_id
        
        # Add request ID if available
        request_id = getattr(record, 'request_id', None)
        if request_id:
            log_entry['request_id'] = request_id
        
        # Add user ID if available
        user_id = getattr(record, 'user_id', None)
        if user_id:
            log_entry['user_id'] = user_id
        
        # Add custom fields
        extra_fields = getattr(record, 'extra_fields', {})
        if extra_fields:
            log_entry['extra'] = extra_fields
        
        # Add exception information
        if record.exc_info:
            log_entry['exception'] = {
                'type': record.exc_info[0].__name__,
                'message': str(record.exc_info[1]),
                'traceback': traceback.format_exception(*record.exc_info)
            }
        
        # Add stack trace for errors
        if record.levelno >= logging.ERROR and not record.exc_info:
            log_entry['stack_trace'] = traceback.format_stack()
        
        return json.dumps(log_entry, ensure_ascii=False)


class CorrelationFilter(logging.Filter):
    """Filter to add correlation ID to log records."""
    
    def filter(self, record: logging.LogRecord) -> bool:
        """Add correlation ID to record if not present."""
        if not hasattr(record, 'correlation_id'):
            # Try to get from thread-local storage or generate new one
            correlation_id = getattr(self._get_current_context(), 'correlation_id', None)
            if not correlation_id:
                correlation_id = str(uuid.uuid4())
            record.correlation_id = correlation_id
        
        return True
    
    def _get_current_context(self):
        """Get current context (placeholder for thread-local storage)."""
        # In a real implementation, this would use threading.local()
        # or contextvars for async contexts
        return type('Context', (), {})()


def setup_logging(
    service_name: str,
    service_version: str = "1.0.0",
    log_level: str = None,
    log_format: str = "json",
    enable_console: bool = True,
    enable_file: bool = False,
    log_file_path: str = None
) -> None:
    """
    Set up structured logging for a service.
    
    Args:
        service_name: Name of the service
        service_version: Version of the service
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_format: Format type ('json' or 'text')
        enable_console: Enable console logging
        enable_file: Enable file logging
        log_file_path: Path to log file
    """
    # Determine log level
    if log_level is None:
        log_level = os.getenv('LOG_LEVEL', 'INFO').upper()
    
    # Validate log level
    numeric_level = getattr(logging, log_level, None)
    if not isinstance(numeric_level, int):
        raise ValueError(f'Invalid log level: {log_level}')
    
    # Create formatters
    if log_format.lower() == 'json':
        formatter = JSONFormatter(service_name, service_version)
    else:
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
    
    # Create handlers
    handlers = []
    
    if enable_console:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(formatter)
        console_handler.addFilter(CorrelationFilter())
        handlers.append(console_handler)
    
    if enable_file and log_file_path:
        # Ensure log directory exists
        os.makedirs(os.path.dirname(log_file_path), exist_ok=True)
        
        file_handler = logging.FileHandler(log_file_path)
        file_handler.setFormatter(formatter)
        file_handler.addFilter(CorrelationFilter())
        handlers.append(file_handler)
    
    # Configure logging
    logging.basicConfig(
        level=numeric_level,
        handlers=handlers,
        force=True
    )
    
    # Set specific logger levels
    logging.getLogger('kafka').setLevel(logging.WARNING)
    logging.getLogger('urllib3').setLevel(logging.WARNING)
    logging.getLogger('requests').setLevel(logging.WARNING)
    
    # Log startup message
    logger = logging.getLogger(service_name)
    logger.info(
        f"Logging configured for {service_name} v{service_version}",
        extra={
            'extra_fields': {
                'log_level': log_level,
                'log_format': log_format,
                'console_enabled': enable_console,
                'file_enabled': enable_file,
                'log_file': log_file_path
            }
        }
    )


def get_logger(name: str) -> logging.Logger:
    """Get a logger with the specified name."""
    return logging.getLogger(name)


def log_with_correlation(
    logger: logging.Logger,
    level: int,
    message: str,
    correlation_id: str = None,
    request_id: str = None,
    user_id: str = None,
    extra_fields: Dict[str, Any] = None,
    exc_info: bool = False
) -> None:
    """
    Log a message with correlation and context information.
    
    Args:
        logger: Logger instance
        level: Log level (logging.DEBUG, INFO, etc.)
        message: Log message
        correlation_id: Correlation ID for request tracing
        request_id: Request ID
        user_id: User ID
        extra_fields: Additional fields to include
        exc_info: Include exception information
    """
    extra = {}
    
    if correlation_id:
        extra['correlation_id'] = correlation_id
    
    if request_id:
        extra['request_id'] = request_id
    
    if user_id:
        extra['user_id'] = user_id
    
    if extra_fields:
        extra['extra_fields'] = extra_fields
    
    logger.log(level, message, extra=extra, exc_info=exc_info)


class LoggerMixin:
    """Mixin class to add logging capabilities to any class."""
    
    @property
    def logger(self) -> logging.Logger:
        """Get logger for this class."""
        return logging.getLogger(f"{self.__class__.__module__}.{self.__class__.__name__}")
    
    def log_info(self, message: str, **kwargs) -> None:
        """Log info message."""
        log_with_correlation(self.logger, logging.INFO, message, **kwargs)
    
    def log_warning(self, message: str, **kwargs) -> None:
        """Log warning message."""
        log_with_correlation(self.logger, logging.WARNING, message, **kwargs)
    
    def log_error(self, message: str, **kwargs) -> None:
        """Log error message."""
        log_with_correlation(self.logger, logging.ERROR, message, **kwargs)
    
    def log_debug(self, message: str, **kwargs) -> None:
        """Log debug message."""
        log_with_correlation(self.logger, logging.DEBUG, message, **kwargs)


# Performance logging utilities
def log_performance(
    logger: logging.Logger,
    operation: str,
    duration_ms: float,
    correlation_id: str = None,
    extra_fields: Dict[str, Any] = None
) -> None:
    """Log performance metrics."""
    fields = {
        'operation': operation,
        'duration_ms': duration_ms,
        'performance': True
    }
    
    if extra_fields:
        fields.update(extra_fields)
    
    log_with_correlation(
        logger,
        logging.INFO,
        f"Operation '{operation}' completed in {duration_ms:.2f}ms",
        correlation_id=correlation_id,
        extra_fields=fields
    )


def log_event(
    logger: logging.Logger,
    event_type: str,
    event_data: Dict[str, Any],
    correlation_id: str = None
) -> None:
    """Log event information."""
    log_with_correlation(
        logger,
        logging.INFO,
        f"Event: {event_type}",
        correlation_id=correlation_id,
        extra_fields={
            'event_type': event_type,
            'event_data': event_data,
            'event_log': True
        }
    )


# Context manager for performance logging
class PerformanceLogger:
    """Context manager for logging operation performance."""
    
    def __init__(
        self,
        logger: logging.Logger,
        operation: str,
        correlation_id: str = None,
        extra_fields: Dict[str, Any] = None
    ):
        self.logger = logger
        self.operation = operation
        self.correlation_id = correlation_id
        self.extra_fields = extra_fields or {}
        self.start_time = None
    
    def __enter__(self):
        self.start_time = datetime.now(timezone.utc)
        log_with_correlation(
            self.logger,
            logging.DEBUG,
            f"Starting operation: {self.operation}",
            correlation_id=self.correlation_id,
            extra_fields={'operation_start': True, **self.extra_fields}
        )
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        end_time = datetime.now(timezone.utc)
        duration_ms = (end_time - self.start_time).total_seconds() * 1000
        
        if exc_type is None:
            log_performance(
                self.logger,
                self.operation,
                duration_ms,
                self.correlation_id,
                self.extra_fields
            )
        else:
            log_with_correlation(
                self.logger,
                logging.ERROR,
                f"Operation '{self.operation}' failed after {duration_ms:.2f}ms",
                correlation_id=self.correlation_id,
                extra_fields={
                    'operation': self.operation,
                    'duration_ms': duration_ms,
                    'operation_failed': True,
                    **self.extra_fields
                },
                exc_info=True
            )

