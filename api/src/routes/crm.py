"""
CRM Mock API routes for lead management.
Simulates a CRM system for testing the Workflow Agent integration.
"""

import logging
import time
from datetime import datetime, timezone
from flask import Blueprint, request, jsonify
from marshmallow import Schema, fields, validate, ValidationError
import uuid

from src.models.user import db


# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create blueprint
crm_bp = Blueprint('crm', __name__)


# Lead model for SQLite storage
from sqlalchemy import Column, String, DateTime, Text, Boolean
from src.models.user import db

class Lead(db.Model):
    """Lead model for CRM mock."""
    __tablename__ = 'leads'
    
    id = Column(String(50), primary_key=True)
    name = Column(String(100), nullable=False)
    email = Column(String(100), nullable=False)
    company = Column(String(100), nullable=False)
    phone = Column(String(20), nullable=True)
    message = Column(Text, nullable=False)
    status = Column(String(20), nullable=False, default='NUEVO')
    assigned_to = Column(String(100), nullable=True)
    tags = Column(Text, nullable=True)  # JSON string
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    source = Column(String(50), nullable=False, default='web')
    priority = Column(String(20), nullable=False, default='medium')
    
    def to_dict(self):
        """Convert lead to dictionary."""
        return {
            'id': self.id,
            'name': self.name,
            'email': self.email,
            'company': self.company,
            'phone': self.phone,
            'message': self.message,
            'status': self.status,
            'assigned_to': self.assigned_to,
            'tags': self.tags,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'source': self.source,
            'priority': self.priority
        }


# Validation schemas
class CreateLeadSchema(Schema):
    """Schema for creating a new lead."""
    name = fields.Str(required=True, validate=validate.Length(min=1, max=100))
    email = fields.Email(required=True)
    company = fields.Str(required=True, validate=validate.Length(min=1, max=100))
    phone = fields.Str(allow_none=True, validate=validate.Length(max=20))
    message = fields.Str(required=True, validate=validate.Length(min=1, max=2000))
    source = fields.Str(missing='web', validate=validate.OneOf(['web', 'phone', 'email', 'referral']))
    priority = fields.Str(missing='medium', validate=validate.OneOf(['low', 'medium', 'high', 'urgent']))
    tags = fields.List(fields.Str(), missing=[])
    assigned_to = fields.Str(allow_none=True)


class UpdateLeadSchema(Schema):
    """Schema for updating an existing lead."""
    name = fields.Str(validate=validate.Length(min=1, max=100))
    email = fields.Email()
    company = fields.Str(validate=validate.Length(min=1, max=100))
    phone = fields.Str(allow_none=True, validate=validate.Length(max=20))
    message = fields.Str(validate=validate.Length(min=1, max=2000))
    status = fields.Str(validate=validate.OneOf(['NUEVO', 'CONTACTADO', 'CALIFICADO', 'PROPUESTA', 'CERRADO', 'PERDIDO']))
    assigned_to = fields.Str(allow_none=True)
    tags = fields.List(fields.Str())
    priority = fields.Str(validate=validate.OneOf(['low', 'medium', 'high', 'urgent']))


@crm_bp.route('/internal/leads', methods=['POST'])
def create_lead():
    """
    Create a new lead in the CRM system.
    This endpoint is called by the Workflow Agent.
    """
    start_time = time.time()
    
    try:
        # Validate request
        if not request.is_json:
            return jsonify({'error': 'Content-Type must be application/json'}), 400
        
        request_data = request.get_json()
        if not request_data:
            return jsonify({'error': 'Request body cannot be empty'}), 400
        
        # Validate data against schema
        schema = CreateLeadSchema()
        try:
            validated_data = schema.load(request_data)
        except ValidationError as e:
            logger.warning(f"Lead validation failed: {e.messages}")
            return jsonify({
                'error': 'Invalid lead data',
                'validation_errors': e.messages
            }), 400
        
        # Create new lead
        lead_id = f"lead_{str(uuid.uuid4())}"
        
        # Convert tags list to JSON string for storage
        tags_json = ','.join(validated_data.get('tags', [])) if validated_data.get('tags') else None
        
        lead = Lead(
            id=lead_id,
            name=validated_data['name'],
            email=validated_data['email'],
            company=validated_data['company'],
            phone=validated_data.get('phone'),
            message=validated_data['message'],
            status='NUEVO',
            assigned_to=validated_data.get('assigned_to'),
            tags=tags_json,
            source=validated_data.get('source', 'web'),
            priority=validated_data.get('priority', 'medium'),
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        
        # Save to database
        db.session.add(lead)
        db.session.commit()
        
        # Calculate processing time
        processing_time_ms = int((time.time() - start_time) * 1000)
        
        logger.info(
            f"Lead created successfully: "
            f"id={lead_id}, "
            f"email={validated_data['email']}, "
            f"company={validated_data['company']}, "
            f"processing_time_ms={processing_time_ms}"
        )
        
        # Return created lead
        response_data = lead.to_dict()
        response_data['processing_time_ms'] = processing_time_ms
        
        return jsonify(response_data), 201
        
    except Exception as e:
        logger.error(f"Error creating lead: {e}", exc_info=True)
        db.session.rollback()
        return jsonify({'error': 'Internal server error'}), 500


@crm_bp.route('/internal/leads/<lead_id>', methods=['GET'])
def get_lead(lead_id):
    """Get a specific lead by ID."""
    try:
        lead = Lead.query.filter_by(id=lead_id).first()
        if not lead:
            return jsonify({'error': 'Lead not found'}), 404
        
        return jsonify(lead.to_dict()), 200
        
    except Exception as e:
        logger.error(f"Error retrieving lead {lead_id}: {e}")
        return jsonify({'error': 'Internal server error'}), 500


@crm_bp.route('/internal/leads/<lead_id>', methods=['PUT'])
def update_lead(lead_id):
    """Update an existing lead."""
    try:
        # Find the lead
        lead = Lead.query.filter_by(id=lead_id).first()
        if not lead:
            return jsonify({'error': 'Lead not found'}), 404
        
        # Validate request
        if not request.is_json:
            return jsonify({'error': 'Content-Type must be application/json'}), 400
        
        request_data = request.get_json()
        if not request_data:
            return jsonify({'error': 'Request body cannot be empty'}), 400
        
        # Validate data against schema
        schema = UpdateLeadSchema()
        try:
            validated_data = schema.load(request_data)
        except ValidationError as e:
            return jsonify({
                'error': 'Invalid lead data',
                'validation_errors': e.messages
            }), 400
        
        # Update lead fields
        for field, value in validated_data.items():
            if field == 'tags' and value is not None:
                # Convert tags list to JSON string
                setattr(lead, field, ','.join(value))
            else:
                setattr(lead, field, value)
        
        lead.updated_at = datetime.now(timezone.utc)
        
        # Save changes
        db.session.commit()
        
        logger.info(f"Lead updated successfully: id={lead_id}")
        
        return jsonify(lead.to_dict()), 200
        
    except Exception as e:
        logger.error(f"Error updating lead {lead_id}: {e}")
        db.session.rollback()
        return jsonify({'error': 'Internal server error'}), 500


@crm_bp.route('/internal/leads', methods=['GET'])
def list_leads():
    """List all leads with optional filtering."""
    try:
        # Get query parameters
        status = request.args.get('status')
        assigned_to = request.args.get('assigned_to')
        source = request.args.get('source')
        limit = request.args.get('limit', 50, type=int)
        offset = request.args.get('offset', 0, type=int)
        
        # Build query
        query = Lead.query
        
        if status:
            query = query.filter(Lead.status == status)
        if assigned_to:
            query = query.filter(Lead.assigned_to == assigned_to)
        if source:
            query = query.filter(Lead.source == source)
        
        # Apply pagination
        query = query.offset(offset).limit(limit)
        
        # Execute query
        leads = query.all()
        total_count = Lead.query.count()
        
        return jsonify({
            'leads': [lead.to_dict() for lead in leads],
            'total_count': total_count,
            'limit': limit,
            'offset': offset
        }), 200
        
    except Exception as e:
        logger.error(f"Error listing leads: {e}")
        return jsonify({'error': 'Internal server error'}), 500


@crm_bp.route('/internal/leads/<lead_id>', methods=['DELETE'])
def delete_lead(lead_id):
    """Delete a lead (soft delete by setting status)."""
    try:
        lead = Lead.query.filter_by(id=lead_id).first()
        if not lead:
            return jsonify({'error': 'Lead not found'}), 404
        
        # Soft delete by setting status
        lead.status = 'DELETED'
        lead.updated_at = datetime.now(timezone.utc)
        
        db.session.commit()
        
        logger.info(f"Lead deleted successfully: id={lead_id}")
        
        return '', 204
        
    except Exception as e:
        logger.error(f"Error deleting lead {lead_id}: {e}")
        db.session.rollback()
        return jsonify({'error': 'Internal server error'}), 500


@crm_bp.route('/internal/leads/stats', methods=['GET'])
def get_lead_stats():
    """Get lead statistics for dashboard."""
    try:
        # Count leads by status
        status_counts = {}
        for status in ['NUEVO', 'CONTACTADO', 'CALIFICADO', 'PROPUESTA', 'CERRADO', 'PERDIDO']:
            count = Lead.query.filter_by(status=status).count()
            status_counts[status] = count
        
        # Count leads by source
        source_counts = {}
        for source in ['web', 'phone', 'email', 'referral']:
            count = Lead.query.filter_by(source=source).count()
            source_counts[source] = count
        
        # Total leads
        total_leads = Lead.query.count()
        
        return jsonify({
            'total_leads': total_leads,
            'by_status': status_counts,
            'by_source': source_counts,
            'timestamp': datetime.now(timezone.utc).isoformat()
        }), 200
        
    except Exception as e:
        logger.error(f"Error getting lead stats: {e}")
        return jsonify({'error': 'Internal server error'}), 500


@crm_bp.route('/internal/health', methods=['GET'])
def crm_health():
    """Health check endpoint for CRM mock service."""
    try:
        # Test database connection
        db.session.execute('SELECT 1')
        
        return jsonify({
            'status': 'healthy',
            'service': 'crm-mock',
            'version': '1.0.0',
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'database': 'connected'
        }), 200
        
    except Exception as e:
        logger.error(f"CRM health check failed: {e}")
        return jsonify({
            'status': 'unhealthy',
            'error': str(e),
            'timestamp': datetime.now(timezone.utc).isoformat()
        }), 503

