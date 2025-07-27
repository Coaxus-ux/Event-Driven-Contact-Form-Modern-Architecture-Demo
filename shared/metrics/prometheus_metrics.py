"""
Prometheus metrics configuration for all services in the event-driven architecture.
Provides standardized metrics collection and exposition.
"""

import time
from typing import Dict, List, Optional, Any
from functools import wraps
from prometheus_client import (
    Counter, Histogram, Gauge, Summary, Info,
    CollectorRegistry, generate_latest, CONTENT_TYPE_LATEST,
    start_http_server, REGISTRY
)
import threading
import os


class ServiceMetrics:
    """Base metrics class for services."""
    
    def __init__(self, service_name: str, service_version: str = "1.0.0", registry: CollectorRegistry = None):
        self.service_name = service_name
        self.service_version = service_version
        self.registry = registry or REGISTRY
        
        # Service info
        self.service_info = Info(
            'service_info',
            'Service information',
            registry=self.registry
        )
        self.service_info.info({
            'name': service_name,
            'version': service_version,
            'environment': os.getenv('ENVIRONMENT', 'development')
        })
        
        # Common metrics
        self.requests_total = Counter(
            'requests_total',
            'Total number of requests',
            ['method', 'endpoint', 'status'],
            registry=self.registry
        )
        
        self.request_duration = Histogram(
            'request_duration_seconds',
            'Request duration in seconds',
            ['method', 'endpoint'],
            buckets=[0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0],
            registry=self.registry
        )
        
        self.active_requests = Gauge(
            'active_requests',
            'Number of active requests',
            registry=self.registry
        )
        
        self.errors_total = Counter(
            'errors_total',
            'Total number of errors',
            ['error_type', 'component'],
            registry=self.registry
        )
        
        # System metrics
        self.memory_usage = Gauge(
            'memory_usage_bytes',
            'Memory usage in bytes',
            registry=self.registry
        )
        
        self.cpu_usage = Gauge(
            'cpu_usage_percent',
            'CPU usage percentage',
            registry=self.registry
        )
        
        # Business metrics
        self.events_processed = Counter(
            'events_processed_total',
            'Total number of events processed',
            ['event_type', 'status'],
            registry=self.registry
        )
        
        self.event_processing_duration = Histogram(
            'event_processing_duration_seconds',
            'Event processing duration in seconds',
            ['event_type'],
            buckets=[0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0],
            registry=self.registry
        )
        
        # Health metrics
        self.health_status = Gauge(
            'health_status',
            'Service health status (1=healthy, 0=unhealthy)',
            registry=self.registry
        )
        
        self.last_health_check = Gauge(
            'last_health_check_timestamp',
            'Timestamp of last health check',
            registry=self.registry
        )
        
        # Initialize health as healthy
        self.health_status.set(1)
        self.last_health_check.set_to_current_time()
    
    def record_request(self, method: str, endpoint: str, status: str, duration: float) -> None:
        """Record request metrics."""
        self.requests_total.labels(method=method, endpoint=endpoint, status=status).inc()
        self.request_duration.labels(method=method, endpoint=endpoint).observe(duration)
    
    def record_error(self, error_type: str, component: str) -> None:
        """Record error metrics."""
        self.errors_total.labels(error_type=error_type, component=component).inc()
    
    def record_event_processed(self, event_type: str, status: str, duration: float) -> None:
        """Record event processing metrics."""
        self.events_processed.labels(event_type=event_type, status=status).inc()
        self.event_processing_duration.labels(event_type=event_type).observe(duration)
    
    def set_health_status(self, healthy: bool) -> None:
        """Set health status."""
        self.health_status.set(1 if healthy else 0)
        self.last_health_check.set_to_current_time()
    
    def update_system_metrics(self, memory_bytes: int, cpu_percent: float) -> None:
        """Update system metrics."""
        self.memory_usage.set(memory_bytes)
        self.cpu_usage.set(cpu_percent)
    
    def get_metrics(self) -> str:
        """Get metrics in Prometheus format."""
        return generate_latest(self.registry)


class APIMetrics(ServiceMetrics):
    """Metrics specific to API services."""
    
    def __init__(self, service_name: str, service_version: str = "1.0.0", registry: CollectorRegistry = None):
        super().__init__(service_name, service_version, registry)
        
        # API-specific metrics
        self.form_submissions = Counter(
            'form_submissions_total',
            'Total number of form submissions',
            ['form_type', 'status'],
            registry=self.registry
        )
        
        self.validation_errors = Counter(
            'validation_errors_total',
            'Total number of validation errors',
            ['field', 'error_type'],
            registry=self.registry
        )
        
        self.kafka_publish_attempts = Counter(
            'kafka_publish_attempts_total',
            'Total number of Kafka publish attempts',
            ['topic', 'status'],
            registry=self.registry
        )
        
        self.kafka_publish_duration = Histogram(
            'kafka_publish_duration_seconds',
            'Kafka publish duration in seconds',
            ['topic'],
            registry=self.registry
        )
    
    def record_form_submission(self, form_type: str, status: str) -> None:
        """Record form submission."""
        self.form_submissions.labels(form_type=form_type, status=status).inc()
    
    def record_validation_error(self, field: str, error_type: str) -> None:
        """Record validation error."""
        self.validation_errors.labels(field=field, error_type=error_type).inc()
    
    def record_kafka_publish(self, topic: str, status: str, duration: float) -> None:
        """Record Kafka publish attempt."""
        self.kafka_publish_attempts.labels(topic=topic, status=status).inc()
        self.kafka_publish_duration.labels(topic=topic).observe(duration)


class MailerMetrics(ServiceMetrics):
    """Metrics specific to Mailer service."""
    
    def __init__(self, service_name: str, service_version: str = "1.0.0", registry: CollectorRegistry = None):
        super().__init__(service_name, service_version, registry)
        
        # Mailer-specific metrics
        self.emails_sent = Counter(
            'emails_sent_total',
            'Total number of emails sent',
            ['template', 'status'],
            registry=self.registry
        )
        
        self.email_send_duration = Histogram(
            'email_send_duration_seconds',
            'Email send duration in seconds',
            ['template'],
            registry=self.registry
        )
        
        self.template_render_duration = Histogram(
            'template_render_duration_seconds',
            'Template render duration in seconds',
            ['template', 'format'],
            registry=self.registry
        )
        
        self.smtp_connections = Gauge(
            'smtp_connections_active',
            'Number of active SMTP connections',
            registry=self.registry
        )
    
    def record_email_sent(self, template: str, status: str, duration: float) -> None:
        """Record email sent."""
        self.emails_sent.labels(template=template, status=status).inc()
        self.email_send_duration.labels(template=template).observe(duration)
    
    def record_template_render(self, template: str, format_type: str, duration: float) -> None:
        """Record template rendering."""
        self.template_render_duration.labels(template=template, format=format_type).observe(duration)


class WorkflowMetrics(ServiceMetrics):
    """Metrics specific to Workflow Agent."""
    
    def __init__(self, service_name: str, service_version: str = "1.0.0", registry: CollectorRegistry = None):
        super().__init__(service_name, service_version, registry)
        
        # Workflow-specific metrics
        self.workflows_executed = Counter(
            'workflows_executed_total',
            'Total number of workflows executed',
            ['workflow_id', 'status'],
            registry=self.registry
        )
        
        self.workflow_duration = Histogram(
            'workflow_duration_seconds',
            'Workflow execution duration in seconds',
            ['workflow_id'],
            registry=self.registry
        )
        
        self.workflow_steps_executed = Counter(
            'workflow_steps_executed_total',
            'Total number of workflow steps executed',
            ['workflow_id', 'step_name', 'status'],
            registry=self.registry
        )
        
        self.active_workflows = Gauge(
            'active_workflows',
            'Number of active workflows',
            registry=self.registry
        )
        
        self.crm_api_calls = Counter(
            'crm_api_calls_total',
            'Total number of CRM API calls',
            ['endpoint', 'status'],
            registry=self.registry
        )
        
        self.crm_api_duration = Histogram(
            'crm_api_duration_seconds',
            'CRM API call duration in seconds',
            ['endpoint'],
            registry=self.registry
        )
    
    def record_workflow_executed(self, workflow_id: str, status: str, duration: float) -> None:
        """Record workflow execution."""
        self.workflows_executed.labels(workflow_id=workflow_id, status=status).inc()
        self.workflow_duration.labels(workflow_id=workflow_id).observe(duration)
    
    def record_workflow_step(self, workflow_id: str, step_name: str, status: str) -> None:
        """Record workflow step execution."""
        self.workflow_steps_executed.labels(
            workflow_id=workflow_id,
            step_name=step_name,
            status=status
        ).inc()
    
    def record_crm_api_call(self, endpoint: str, status: str, duration: float) -> None:
        """Record CRM API call."""
        self.crm_api_calls.labels(endpoint=endpoint, status=status).inc()
        self.crm_api_duration.labels(endpoint=endpoint).observe(duration)


# Decorators for automatic metrics collection
def track_requests(metrics: ServiceMetrics):
    """Decorator to track request metrics."""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.time()
            metrics.active_requests.inc()
            
            try:
                result = func(*args, **kwargs)
                duration = time.time() - start_time
                
                # Extract method and endpoint from Flask request if available
                method = getattr(kwargs.get('request', {}), 'method', 'UNKNOWN')
                endpoint = func.__name__
                status = 'success'
                
                metrics.record_request(method, endpoint, status, duration)
                return result
                
            except Exception as e:
                duration = time.time() - start_time
                method = getattr(kwargs.get('request', {}), 'method', 'UNKNOWN')
                endpoint = func.__name__
                status = 'error'
                
                metrics.record_request(method, endpoint, status, duration)
                metrics.record_error(type(e).__name__, 'request_handler')
                raise
                
            finally:
                metrics.active_requests.dec()
        
        return wrapper
    return decorator


def track_events(metrics: ServiceMetrics):
    """Decorator to track event processing metrics."""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.time()
            
            # Try to extract event type from arguments
            event_type = 'unknown'
            if args and hasattr(args[0], 'get'):
                event_type = args[0].get('type', 'unknown')
            
            try:
                result = func(*args, **kwargs)
                duration = time.time() - start_time
                metrics.record_event_processed(event_type, 'success', duration)
                return result
                
            except Exception as e:
                duration = time.time() - start_time
                metrics.record_event_processed(event_type, 'error', duration)
                metrics.record_error(type(e).__name__, 'event_processor')
                raise
        
        return wrapper
    return decorator


class MetricsServer:
    """HTTP server for exposing Prometheus metrics."""
    
    def __init__(self, port: int = 8000, registry: CollectorRegistry = None):
        self.port = port
        self.registry = registry or REGISTRY
        self.server_thread = None
        self.running = False
    
    def start(self) -> None:
        """Start metrics server."""
        if self.running:
            return
        
        self.server_thread = threading.Thread(
            target=self._run_server,
            daemon=True
        )
        self.server_thread.start()
        self.running = True
    
    def _run_server(self) -> None:
        """Run the metrics server."""
        start_http_server(self.port, registry=self.registry)
    
    def stop(self) -> None:
        """Stop metrics server."""
        self.running = False


# Utility functions
def create_metrics_for_service(service_name: str, service_type: str = "generic") -> ServiceMetrics:
    """Create appropriate metrics instance for a service."""
    service_version = os.getenv('SERVICE_VERSION', '1.0.0')
    
    if service_type.lower() == 'api':
        return APIMetrics(service_name, service_version)
    elif service_type.lower() == 'mailer':
        return MailerMetrics(service_name, service_version)
    elif service_type.lower() == 'workflow':
        return WorkflowMetrics(service_name, service_version)
    else:
        return ServiceMetrics(service_name, service_version)


def setup_metrics_server(port: int = None) -> MetricsServer:
    """Set up and start metrics server."""
    if port is None:
        port = int(os.getenv('METRICS_PORT', 8000))
    
    server = MetricsServer(port)
    server.start()
    return server

