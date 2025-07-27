"""
Event models and schemas for the Mailer service.
Shared event definitions for consistent event handling.
"""

import json
from datetime import datetime, timezone
from typing import Dict, Any, Optional
from dataclasses import dataclass, asdict
from marshmallow import Schema, fields, validate, post_load
import uuid


@dataclass
class BaseEvent:
    """Base event structure following CloudEvents specification."""
    id: str
    occurred_at: str
    source: str
    type: str
    version: str
    correlation_id: str
    causation_id: Optional[str] = None
    data: Optional[Dict[str, Any]] = None

    @classmethod
    def create(cls, event_type: str, source: str, data: Dict[str, Any], 
               correlation_id: Optional[str] = None, causation_id: Optional[str] = None):
        """Create a new event with auto-generated metadata."""
        event_id = str(uuid.uuid4())
        if correlation_id is None:
            correlation_id = event_id
            
        return cls(
            id=event_id,
            occurred_at=datetime.now(timezone.utc).isoformat(),
            source=source,
            type=event_type,
            version="1.0",
            correlation_id=correlation_id,
            causation_id=causation_id,
            data=data
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert event to dictionary for serialization."""
        return asdict(self)

    def to_json(self) -> str:
        """Convert event to JSON string."""
        return json.dumps(self.to_dict(), default=str)


class BaseEventSchema(Schema):
    """Marshmallow schema for base event validation."""
    id = fields.Str(required=True, validate=validate.Length(min=1))
    occurred_at = fields.DateTime(required=True, format='iso')
    source = fields.Str(required=True, validate=validate.Length(min=1))
    type = fields.Str(required=True, validate=validate.Length(min=1))
    version = fields.Str(required=True, validate=validate.Regexp(r'^\d+\.\d+$'))
    correlation_id = fields.Str(required=True, validate=validate.Length(min=1))
    causation_id = fields.Str(allow_none=True)
    data = fields.Dict(allow_none=True)

    @post_load
    def make_event(self, data, **kwargs):
        if isinstance(data, BaseEvent):
            return data
        return BaseEvent(**data)


# Contact Form Submission Event Schemas
class ContactFormDataSchema(Schema):
    """Schema for contact form data validation."""
    name = fields.Str(required=True, validate=validate.Length(min=1, max=100))
    email = fields.Email(required=True)
    company = fields.Str(required=True, validate=validate.Length(min=1, max=100))
    phone = fields.Str(allow_none=True, validate=validate.Length(max=20))
    message = fields.Str(required=True, validate=validate.Length(min=10, max=2000))
    preferred_contact_method = fields.Str(
        required=True, 
        validate=validate.OneOf(['email', 'phone', 'both'])
    )
    consent_marketing = fields.Bool(required=True)
    consent_data_processing = fields.Bool(required=True)


class ContactFormMetadataSchema(Schema):
    """Schema for contact form metadata."""
    user_agent = fields.Str(required=True)
    ip_address = fields.Str(required=True)
    referrer = fields.Str(allow_none=True)
    session_id = fields.Str(required=True)
    form_version = fields.Str(required=True)
    submission_duration_ms = fields.Int(required=True, validate=validate.Range(min=0))
    validation_errors = fields.List(fields.Str(), missing=[])


class ContactFormComplianceSchema(Schema):
    """Schema for compliance information."""
    gdpr_applicable = fields.Bool(required=True)
    data_retention_days = fields.Int(required=True, validate=validate.Range(min=1))
    processing_lawful_basis = fields.Str(
        required=True,
        validate=validate.OneOf(['consent', 'contract', 'legal_obligation', 'vital_interests', 'public_task', 'legitimate_interests'])
    )
    consent_timestamp = fields.DateTime(required=True, format='iso')


class ContactFormSubmittedDataSchema(Schema):
    """Schema for ContactFormSubmitted event data."""
    form_data = fields.Nested(ContactFormDataSchema, required=True)
    metadata = fields.Nested(ContactFormMetadataSchema, required=True)
    compliance = fields.Nested(ContactFormComplianceSchema, required=True)


class ContactFormSubmittedSchema(BaseEventSchema):
    """Complete schema for ContactFormSubmitted event."""
    data = fields.Nested(ContactFormSubmittedDataSchema, required=True)

    @post_load
    def make_contact_form_event(self, data, **kwargs):
        if isinstance(data, BaseEvent):
            return data
        return BaseEvent(**data)


# Email Dispatched Event Schemas
class EmailDetailsSchema(Schema):
    """Schema for email details."""
    recipient = fields.Email(required=True)
    subject = fields.Str(required=True, validate=validate.Length(min=1, max=200))
    template_name = fields.Str(required=True)
    template_version = fields.Str(required=True)
    personalization_data = fields.Dict(required=True)


class EmailDeliverySchema(Schema):
    """Schema for email delivery information."""
    message_id = fields.Str(required=True)
    smtp_response = fields.Str(required=True)
    delivery_attempt = fields.Int(required=True, validate=validate.Range(min=1))
    processing_duration_ms = fields.Int(required=True, validate=validate.Range(min=0))
    content_size_bytes = fields.Int(required=True, validate=validate.Range(min=0))


class EmailTrackingSchema(Schema):
    """Schema for email tracking information."""
    tracking_pixel_url = fields.Url(required=True)
    unsubscribe_url = fields.Url(required=True)
    click_tracking_enabled = fields.Bool(required=True)


class EmailDispatchedDataSchema(Schema):
    """Schema for EmailDispatched event data."""
    email_details = fields.Nested(EmailDetailsSchema, required=True)
    delivery = fields.Nested(EmailDeliverySchema, required=True)
    tracking = fields.Nested(EmailTrackingSchema, required=True)


class EmailDispatchedSchema(BaseEventSchema):
    """Complete schema for EmailDispatched event."""
    data = fields.Nested(EmailDispatchedDataSchema, required=True)


# Event type constants
class EventTypes:
    """Constants for event types."""
    CONTACT_FORM_SUBMITTED = "ContactFormSubmitted"
    EMAIL_DISPATCHED = "EmailDispatched"
    WORKFLOW_COMPLETED = "WorkflowCompleted"


# Event source constants
class EventSources:
    """Constants for event sources."""
    WEB = "web"
    MAILER_SERVICE = "mailer-service"
    WORKFLOW_AGENT = "workflow-agent"
    CRM_MOCK = "crm-mock"

def transform_event(raw: dict) -> dict:
    return {
        # Campos de BaseEventSchema
        "id": raw["id"],
        "occurred_at": raw["occurred_at"],
        "source": raw["source"],
        "type": raw["type"],
        "version": raw["version"],
        "correlation_id": raw["correlation_id"],
        # causation_id no viene en tu JSON, lo marcamos explícitamente
        "causation_id": None,
        # Y todo lo que tu esquema llama "data"
        "data": {
            # 1) form_data tal cual viene
            "form_data": raw["form_data"],
            # 2) metadata -> ajusta/refiere los campos existentes
            "metadata": {
                "user_agent": raw["user_agent"],
                "ip_address": raw["ip_address"],
                # estos campos no vienen, cámbialos según tu lógica o déjalos None/por defecto
                "referrer": None,
                "session_id": raw.get("session_id") or "",
                "form_version": "1.0",             # o lo que proceda
                "submission_duration_ms": 0,       # si lo calculas, pon aquí el valor
                "validation_errors": []            # si existen errores, inclúyelos
            },
            # 3) compliance -> debes suministrar algo acorde al esquema
            "compliance": {
                "gdpr_applicable": True,
                "data_retention_days": 365,
                "processing_lawful_basis": "consent",
                "consent_timestamp": raw["occurred_at"]
            }
        }
    }
