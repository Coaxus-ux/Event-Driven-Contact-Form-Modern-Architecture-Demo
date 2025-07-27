"""
Event models and schemas for the event-driven architecture.
Implements CloudEvents specification with domain-specific event types.
"""

import uuid
import json
from datetime import datetime, UTC
from typing import Dict, Any, Optional
from dataclasses import dataclass, asdict
from enum import Enum

from marshmallow import Schema, fields, validate, post_load


@dataclass(kw_only=True)
class BaseEvent:
    """Base event structure following CloudEvents specification."""
    id: str
    occurred_at: str
    source: str
    type: str
    version: str
    correlation_id: Optional[str] = None
    trace_id: Optional[str] = None
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert event to dictionary format."""
        return asdict(self)
    
    def to_json(self) -> str:
        """Convert event to JSON string."""
        return json.dumps(self.to_dict(), default=str)
    
    @classmethod
    def generate_id(cls) -> str:
        """Generate a unique event ID."""
        return str(uuid.uuid4())


class EventType(Enum):
    """Enumeration of supported event types."""
    CONTACT_FORM_SUBMITTED = "ContactFormSubmitted"
    CONTACT_FORM_VALIDATED = "contact.form.validated"
    CONTACT_FORM_PROCESSED = "contact.form.processed"
    LEAD_CREATED = "lead.created"
    LEAD_ASSIGNED = "lead.assigned"
    EMAIL_QUEUED = "email.queued"
    EMAIL_SENT = "email.sent"
    EMAIL_DELIVERED = "email.delivered"
    EMAIL_BOUNCED = "email.bounced"
    WORKFLOW_STARTED = "workflow.started"
    WORKFLOW_STEP_COMPLETED = "workflow.step.completed"
    WORKFLOW_COMPLETED = "workflow.completed"
    WORKFLOW_FAILED = "workflow.failed"


@dataclass(kw_only=True)
class ContactFormSubmittedEvent(BaseEvent):
    """Event emitted when a contact form is submitted."""
    submission_id: str
    form_data: Dict[str, Any]
    validation_status: str
    # All required fields above, now fields with defaults below
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    id: str = ""
    occurred_at: str = ""
    source: str = ""
    type: str = ""
    version: str = ""
    correlation_id: Optional[str] = None
    trace_id: Optional[str] = None
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    
    def __post_init__(self):
        if not self.id:
            self.id = self.generate_id()
        if not self.occurred_at:
            self.occurred_at = datetime.now(UTC).isoformat()
        if not self.type:
            self.type = EventType.CONTACT_FORM_SUBMITTED.value
        if not self.version:
            self.version = "1.0"


@dataclass(kw_only=True)
class ContactFormProcessedEvent(BaseEvent):
    """Event emitted when a contact form has been processed."""
    submission_id: str
    processing_result: Dict[str, Any]
    # Required fields above, optional below
    lead_id: Optional[str] = None
    processing_time_ms: Optional[int] = None
    
    def __post_init__(self):
        if not self.id:
            self.id = self.generate_id()
        if not self.occurred_at:
            self.occurred_at = datetime.now(UTC).isoformat()
        if not self.type:
            self.type = EventType.CONTACT_FORM_PROCESSED.value
        if not self.version:
            self.version = "1.0"


@dataclass(kw_only=True)
class LeadCreatedEvent(BaseEvent):
    """Event emitted when a new lead is created."""
    lead_id: str
    contact_info: Dict[str, Any]
    lead_source: str
    # Required fields above, optional below
    lead_score: Optional[int] = None
    assigned_to: Optional[str] = None
    
    def __post_init__(self):
        if not self.id:
            self.id = self.generate_id()
        if not self.occurred_at:
            self.occurred_at = datetime.now(UTC).isoformat()
        if not self.type:
            self.type = EventType.LEAD_CREATED.value
        if not self.version:
            self.version = "1.0"


@dataclass(kw_only=True)
class EmailQueuedEvent(BaseEvent):
    """Event emitted when an email is queued for sending."""
    email_id: str
    recipient: str
    template: str
    template_data: Dict[str, Any]
    # Required fields above, optional below
    priority: str = "normal"
    scheduled_send_time: Optional[str] = None
    
    def __post_init__(self):
        if not self.id:
            self.id = self.generate_id()
        if not self.occurred_at:
            self.occurred_at = datetime.now(UTC).isoformat()
        if not self.type:
            self.type = EventType.EMAIL_QUEUED.value
        if not self.version:
            self.version = "1.0"


@dataclass(kw_only=True)
class EmailSentEvent(BaseEvent):
    """Event emitted when an email has been sent."""
    email_id: str
    recipient: str
    subject: str
    sent_time: str
    smtp_response: Dict[str, Any]
    
    def __post_init__(self):
        if not self.id:
            self.id = self.generate_id()
        if not self.occurred_at:
            self.occurred_at = datetime.now(UTC).isoformat()
        if not self.type:
            self.type = EventType.EMAIL_SENT.value
        if not self.version:
            self.version = "1.0"


@dataclass(kw_only=True)
class WorkflowStartedEvent(BaseEvent):
    """Event emitted when a workflow is started."""
    workflow_id: str
    workflow_type: str
    trigger_event_id: str
    context: Dict[str, Any]
    
    def __post_init__(self):
        if not self.id:
            self.id = self.generate_id()
        if not self.occurred_at:
            self.occurred_at = datetime.now(UTC).isoformat()
        if not self.type:
            self.type = EventType.WORKFLOW_STARTED.value
        if not self.version:
            self.version = "1.0"


@dataclass(kw_only=True)
class WorkflowCompletedEvent(BaseEvent):
    """Event emitted when a workflow is completed."""
    workflow_id: str
    workflow_type: str
    start_time: str
    end_time: str
    duration_ms: int
    status: str
    results: Dict[str, Any]
    
    def __post_init__(self):
        if not self.id:
            self.id = self.generate_id()
        if not self.occurred_at:
            self.occurred_at = datetime.now(UTC).isoformat()
        if not self.type:
            self.type = EventType.WORKFLOW_COMPLETED.value
        if not self.version:
            self.version = "1.0"


# Marshmallow schemas for validation and serialization

class BaseEventSchema(Schema):
    """Base schema for event validation."""
    id = fields.Str(required=True)
    occurred_at = fields.DateTime(required=True)
    source = fields.Str(required=True)
    type = fields.Str(required=True, validate=validate.OneOf([e.value for e in EventType]))
    version = fields.Str(required=True)
    correlation_id = fields.Str(allow_none=True)
    trace_id = fields.Str(allow_none=True)
    user_id = fields.Str(allow_none=True)
    session_id = fields.Str(allow_none=True)


class ContactFormSubmittedEventSchema(BaseEventSchema):
    """Schema for contact form submitted events."""
    submission_id = fields.Str(required=True)
    form_data = fields.Dict(required=True)
    validation_status = fields.Str(required=True, validate=validate.OneOf(['valid', 'invalid', 'pending']))
    ip_address = fields.Str(allow_none=True)
    user_agent = fields.Str(allow_none=True)
    
    @post_load
    def make_event(self, data, **kwargs):
        return ContactFormSubmittedEvent(**data)


class ContactFormProcessedEventSchema(BaseEventSchema):
    """Schema for contact form processed events."""
    submission_id = fields.Str(required=True)
    processing_result = fields.Dict(required=True)
    lead_id = fields.Str(allow_none=True)
    processing_time_ms = fields.Int(allow_none=True)
    
    @post_load
    def make_event(self, data, **kwargs):
        return ContactFormProcessedEvent(**data)


class LeadCreatedEventSchema(BaseEventSchema):
    """Schema for lead created events."""
    lead_id = fields.Str(required=True)
    contact_info = fields.Dict(required=True)
    lead_source = fields.Str(required=True)
    lead_score = fields.Int(allow_none=True, validate=validate.Range(min=0, max=100))
    assigned_to = fields.Str(allow_none=True)
    
    @post_load
    def make_event(self, data, **kwargs):
        return LeadCreatedEvent(**data)


class EmailQueuedEventSchema(BaseEventSchema):
    """Schema for email queued events."""
    email_id = fields.Str(required=True)
    recipient = fields.Email(required=True)
    template = fields.Str(required=True)
    template_data = fields.Dict(required=True)
    priority = fields.Str(validate=validate.OneOf(['low', 'normal', 'high', 'urgent']), missing='normal')
    scheduled_send_time = fields.DateTime(allow_none=True)
    
    @post_load
    def make_event(self, data, **kwargs):
        return EmailQueuedEvent(**data)


class EmailSentEventSchema(BaseEventSchema):
    """Schema for email sent events."""
    email_id = fields.Str(required=True)
    recipient = fields.Email(required=True)
    subject = fields.Str(required=True)
    sent_time = fields.DateTime(required=True)
    smtp_response = fields.Dict(required=True)
    
    @post_load
    def make_event(self, data, **kwargs):
        return EmailSentEvent(**data)


class WorkflowStartedEventSchema(BaseEventSchema):
    """Schema for workflow started events."""
    workflow_id = fields.Str(required=True)
    workflow_type = fields.Str(required=True)
    trigger_event_id = fields.Str(required=True)
    context = fields.Dict(required=True)
    
    @post_load
    def make_event(self, data, **kwargs):
        return WorkflowStartedEvent(**data)


class WorkflowCompletedEventSchema(BaseEventSchema):
    """Schema for workflow completed events."""
    workflow_id = fields.Str(required=True)
    workflow_type = fields.Str(required=True)
    start_time = fields.DateTime(required=True)
    end_time = fields.DateTime(required=True)
    duration_ms = fields.Int(required=True, validate=validate.Range(min=0))
    status = fields.Str(required=True, validate=validate.OneOf(['success', 'failed', 'cancelled']))
    results = fields.Dict(required=True)
    
    @post_load
    def make_event(self, data, **kwargs):
        return WorkflowCompletedEvent(**data)


# Event factory for creating events from dictionaries
def create_event_from_dict(event_data: Dict[str, Any]) -> BaseEvent:
    """Create an event object from a dictionary based on event type."""
    event_type = event_data.get('type')
    
    schema_mapping = {
        EventType.CONTACT_FORM_SUBMITTED.value: ContactFormSubmittedEventSchema(),
        EventType.CONTACT_FORM_PROCESSED.value: ContactFormProcessedEventSchema(),
        EventType.LEAD_CREATED.value: LeadCreatedEventSchema(),
        EventType.EMAIL_QUEUED.value: EmailQueuedEventSchema(),
        EventType.EMAIL_SENT.value: EmailSentEventSchema(),
        EventType.WORKFLOW_STARTED.value: WorkflowStartedEventSchema(),
        EventType.WORKFLOW_COMPLETED.value: WorkflowCompletedEventSchema(),
    }
    
    schema = schema_mapping.get(event_type)
    if not schema:
        raise ValueError(f"Unknown event type: {event_type}")
    
    return schema.load(event_data)

class EventTypes:
    """Constants for event types."""
    CONTACT_FORM_SUBMITTED = "contact.form.submitted"
    EMAIL_DISPATCHED = "EmailDispatched"
    WORKFLOW_COMPLETED = "WorkflowCompleted"

class EventSources:
    """Constants for event sources."""
    WEB = "web"
    MAILER_SERVICE = "mailer-service"
    WORKFLOW_AGENT = "workflow-agent"
    CRM_MOCK = "crm-mock"
