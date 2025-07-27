"""
OpenTelemetry tracing configuration for distributed tracing across services.
Provides automatic instrumentation and manual span creation capabilities.
"""

import os
import logging
from typing import Dict, Any, Optional, Callable
from functools import wraps
from contextlib import contextmanager

from opentelemetry import trace, baggage
from opentelemetry.exporter.jaeger.thrift import JaegerExporter
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.flask import FlaskInstrumentor
from opentelemetry.instrumentation.requests import RequestsInstrumentor
from opentelemetry.instrumentation.kafka import KafkaInstrumentor
from opentelemetry.propagate import inject, extract
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter
from opentelemetry.trace import Status, StatusCode
from opentelemetry.trace.propagation.tracecontext import TraceContextTextMapPropagator


class TracingConfig:
    """Configuration for OpenTelemetry tracing."""
    
    def __init__(
        self,
        service_name: str,
        service_version: str = "1.0.0",
        environment: str = None,
        jaeger_endpoint: str = None,
        otlp_endpoint: str = None,
        console_export: bool = False,
        sample_rate: float = 1.0
    ):
        self.service_name = service_name
        self.service_version = service_version
        self.environment = environment or os.getenv('ENVIRONMENT', 'development')
        self.jaeger_endpoint = jaeger_endpoint or os.getenv('JAEGER_ENDPOINT')
        self.otlp_endpoint = otlp_endpoint or os.getenv('OTLP_ENDPOINT')
        self.console_export = console_export or os.getenv('TRACING_CONSOLE', 'false').lower() == 'true'
        self.sample_rate = sample_rate
        
        self.tracer_provider = None
        self.tracer = None
        self.propagator = TraceContextTextMapPropagator()
    
    def setup_tracing(self) -> None:
        """Set up OpenTelemetry tracing."""
        # Create resource
        resource = Resource.create({
            "service.name": self.service_name,
            "service.version": self.service_version,
            "service.environment": self.environment,
            "service.instance.id": os.getenv('HOSTNAME', 'localhost')
        })
        
        # Create tracer provider
        self.tracer_provider = TracerProvider(resource=resource)
        trace.set_tracer_provider(self.tracer_provider)
        
        # Set up exporters
        self._setup_exporters()
        
        # Get tracer
        self.tracer = trace.get_tracer(self.service_name, self.service_version)
        
        # Set up automatic instrumentation
        self._setup_auto_instrumentation()
        
        logging.getLogger(__name__).info(
            f"Tracing configured for {self.service_name}",
            extra={
                'extra_fields': {
                    'jaeger_endpoint': self.jaeger_endpoint,
                    'otlp_endpoint': self.otlp_endpoint,
                    'console_export': self.console_export,
                    'sample_rate': self.sample_rate
                }
            }
        )
    
    def _setup_exporters(self) -> None:
        """Set up span exporters."""
        processors = []
        
        # Jaeger exporter
        if self.jaeger_endpoint:
            jaeger_exporter = JaegerExporter(
                agent_host_name=self.jaeger_endpoint.split(':')[0],
                agent_port=int(self.jaeger_endpoint.split(':')[1]) if ':' in self.jaeger_endpoint else 14268,
            )
            processors.append(BatchSpanProcessor(jaeger_exporter))
        
        # OTLP exporter
        if self.otlp_endpoint:
            otlp_exporter = OTLPSpanExporter(endpoint=self.otlp_endpoint)
            processors.append(BatchSpanProcessor(otlp_exporter))
        
        # Console exporter for development
        if self.console_export:
            console_exporter = ConsoleSpanExporter()
            processors.append(BatchSpanProcessor(console_exporter))
        
        # Add processors to tracer provider
        for processor in processors:
            self.tracer_provider.add_span_processor(processor)
    
    def _setup_auto_instrumentation(self) -> None:
        """Set up automatic instrumentation."""
        # Instrument HTTP requests
        RequestsInstrumentor().instrument()
        
        # Instrument Kafka (if available)
        try:
            KafkaInstrumentor().instrument()
        except Exception:
            pass  # Kafka instrumentation might not be available
    
    def instrument_flask_app(self, app) -> None:
        """Instrument Flask application."""
        FlaskInstrumentor().instrument_app(app)
    
    def get_tracer(self) -> trace.Tracer:
        """Get the tracer instance."""
        return self.tracer
    
    def inject_context(self, carrier: Dict[str, str]) -> None:
        """Inject tracing context into carrier."""
        inject(carrier, setter=dict.__setitem__)
    
    def extract_context(self, carrier: Dict[str, str]) -> None:
        """Extract tracing context from carrier."""
        return extract(carrier, getter=dict.get)


class TracingMixin:
    """Mixin class to add tracing capabilities to any class."""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._tracer = None
    
    @property
    def tracer(self) -> trace.Tracer:
        """Get tracer for this class."""
        if self._tracer is None:
            self._tracer = trace.get_tracer(
                f"{self.__class__.__module__}.{self.__class__.__name__}"
            )
        return self._tracer
    
    @contextmanager
    def trace_operation(
        self,
        operation_name: str,
        attributes: Dict[str, Any] = None,
        set_status_on_exception: bool = True
    ):
        """Context manager for tracing operations."""
        with self.tracer.start_as_current_span(operation_name) as span:
            if attributes:
                span.set_attributes(attributes)
            
            try:
                yield span
            except Exception as e:
                if set_status_on_exception:
                    span.set_status(Status(StatusCode.ERROR, str(e)))
                    span.record_exception(e)
                raise
    
    def trace_event_processing(
        self,
        event_type: str,
        correlation_id: str = None,
        attributes: Dict[str, Any] = None
    ):
        """Decorator for tracing event processing."""
        def decorator(func):
            @wraps(func)
            def wrapper(*args, **kwargs):
                span_attributes = {
                    'event.type': event_type,
                    'component': 'event_processor'
                }
                
                if correlation_id:
                    span_attributes['correlation.id'] = correlation_id
                
                if attributes:
                    span_attributes.update(attributes)
                
                with self.trace_operation(
                    f"process_event_{event_type}",
                    span_attributes
                ) as span:
                    # Add baggage for correlation ID
                    if correlation_id:
                        baggage.set_baggage('correlation.id', correlation_id)
                    
                    result = func(*args, **kwargs)
                    
                    # Add result information to span
                    if isinstance(result, dict) and 'status' in result:
                        span.set_attribute('result.status', result['status'])
                    
                    return result
            
            return wrapper
        return decorator


def trace_function(
    operation_name: str = None,
    attributes: Dict[str, Any] = None,
    tracer_name: str = None
):
    """Decorator for tracing functions."""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Get tracer
            tracer = trace.get_tracer(tracer_name or func.__module__)
            
            # Determine operation name
            op_name = operation_name or f"{func.__module__}.{func.__name__}"
            
            # Prepare attributes
            span_attributes = {
                'function.name': func.__name__,
                'function.module': func.__module__
            }
            if attributes:
                span_attributes.update(attributes)
            
            with tracer.start_as_current_span(op_name) as span:
                span.set_attributes(span_attributes)
                
                try:
                    result = func(*args, **kwargs)
                    
                    # Add result information if available
                    if hasattr(result, '__len__'):
                        span.set_attribute('result.length', len(result))
                    
                    return result
                    
                except Exception as e:
                    span.set_status(Status(StatusCode.ERROR, str(e)))
                    span.record_exception(e)
                    raise
        
        return wrapper
    return decorator


def trace_kafka_event(event_type: str, correlation_id: str = None):
    """Decorator for tracing Kafka event processing."""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            tracer = trace.get_tracer(func.__module__)
            
            span_attributes = {
                'messaging.system': 'kafka',
                'messaging.operation': 'process',
                'messaging.destination_kind': 'topic',
                'event.type': event_type
            }
            
            if correlation_id:
                span_attributes['correlation.id'] = correlation_id
            
            # Extract context from Kafka message headers if available
            context = None
            if args and hasattr(args[0], 'headers'):
                headers = dict(args[0].headers or [])
                context = extract(headers, getter=dict.get)
            
            with tracer.start_as_current_span(
                f"kafka_process_{event_type}",
                context=context,
                attributes=span_attributes
            ) as span:
                try:
                    result = func(*args, **kwargs)
                    span.set_attribute('processing.status', 'success')
                    return result
                except Exception as e:
                    span.set_status(Status(StatusCode.ERROR, str(e)))
                    span.record_exception(e)
                    span.set_attribute('processing.status', 'error')
                    raise
        
        return wrapper
    return decorator


def trace_http_request(method: str = None, endpoint: str = None):
    """Decorator for tracing HTTP requests."""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            tracer = trace.get_tracer(func.__module__)
            
            # Try to extract HTTP information from Flask request
            request_method = method
            request_endpoint = endpoint
            
            try:
                from flask import request
                request_method = request_method or request.method
                request_endpoint = request_endpoint or request.endpoint
            except (ImportError, RuntimeError):
                pass
            
            span_attributes = {
                'http.method': request_method or 'UNKNOWN',
                'http.route': request_endpoint or func.__name__,
                'component': 'http_handler'
            }
            
            with tracer.start_as_current_span(
                f"http_{request_method}_{request_endpoint}",
                attributes=span_attributes
            ) as span:
                try:
                    result = func(*args, **kwargs)
                    
                    # Add response information
                    if hasattr(result, 'status_code'):
                        span.set_attribute('http.status_code', result.status_code)
                    
                    return result
                    
                except Exception as e:
                    span.set_status(Status(StatusCode.ERROR, str(e)))
                    span.record_exception(e)
                    span.set_attribute('http.status_code', 500)
                    raise
        
        return wrapper
    return decorator


class DistributedTracing:
    """Utilities for distributed tracing across services."""
    
    @staticmethod
    def create_child_span(
        tracer: trace.Tracer,
        operation_name: str,
        parent_context: Optional[Any] = None,
        attributes: Dict[str, Any] = None
    ):
        """Create a child span with optional parent context."""
        span = tracer.start_span(
            operation_name,
            context=parent_context,
            attributes=attributes
        )
        return span
    
    @staticmethod
    def inject_headers_for_http(headers: Dict[str, str]) -> None:
        """Inject tracing headers for HTTP requests."""
        inject(headers, setter=dict.__setitem__)
    
    @staticmethod
    def inject_headers_for_kafka(headers: Dict[str, bytes]) -> None:
        """Inject tracing headers for Kafka messages."""
        carrier = {}
        inject(carrier, setter=dict.__setitem__)
        
        # Convert to bytes for Kafka
        for key, value in carrier.items():
            headers[key] = value.encode('utf-8')
    
    @staticmethod
    def extract_context_from_headers(headers: Dict[str, str]):
        """Extract tracing context from headers."""
        return extract(headers, getter=dict.get)
    
    @staticmethod
    def get_current_trace_id() -> str:
        """Get current trace ID."""
        span = trace.get_current_span()
        if span and span.get_span_context().is_valid:
            return format(span.get_span_context().trace_id, '032x')
        return None
    
    @staticmethod
    def get_current_span_id() -> str:
        """Get current span ID."""
        span = trace.get_current_span()
        if span and span.get_span_context().is_valid:
            return format(span.get_span_context().span_id, '016x')
        return None


# Global tracing configuration instance
_tracing_config: Optional[TracingConfig] = None


def setup_tracing(
    service_name: str,
    service_version: str = "1.0.0",
    **kwargs
) -> TracingConfig:
    """Set up tracing for a service."""
    global _tracing_config
    
    _tracing_config = TracingConfig(service_name, service_version, **kwargs)
    _tracing_config.setup_tracing()
    
    return _tracing_config


def get_tracing_config() -> Optional[TracingConfig]:
    """Get the global tracing configuration."""
    return _tracing_config


def get_tracer(name: str = None) -> trace.Tracer:
    """Get a tracer instance."""
    return trace.get_tracer(name or __name__)

