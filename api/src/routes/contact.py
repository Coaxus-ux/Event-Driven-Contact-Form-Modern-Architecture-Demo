"""
Contact form routes for handling form submissions and publishing events.
Implements comprehensive validation, error handling, and observability.
"""

import logging
import time
from datetime import datetime, timezone
from flask import Blueprint, request, jsonify, current_app
from marshmallow import ValidationError
from werkzeug.exceptions import BadRequest
import uuid
from src.models.events import EventType
from src.models.events import (
    ContactFormSubmittedEventSchema,
    EventTypes, 
    EventSources,
    EventType
)
from src.services.event_publisher import get_event_publisher


# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create blueprint
contact_bp = Blueprint('contact', __name__)


def get_client_ip():
    """Get the client IP address from request headers."""
    # Check for forwarded headers first (for load balancers/proxies)
    if request.headers.get('X-Forwarded-For'):
        return request.headers.get('X-Forwarded-For').split(',')[0].strip()
    elif request.headers.get('X-Real-IP'):
        return request.headers.get('X-Real-IP')
    else:
        return request.remote_addr


def create_contact_form_event_data(form_data, request_metadata):
    """Create the complete event data structure for ContactFormSubmitted."""
    return {
        'submission_id': str(uuid.uuid4()),
        'form_data': {
            'name': form_data['name'],
            'email': form_data['email'],
            'company': form_data['company'],
            'phone': form_data.get('phone'),
            'message': form_data['message'],
            'preferred_contact_method': form_data['preferred_contact_method'],
            'consent_marketing': form_data['consent_marketing'],
            'consent_data_processing': form_data['consent_data_processing']
        },
        'validation_status': 'valid',  # o 'pending' si estás haciendo validación posterior
        'ip_address': get_client_ip(),
        'user_agent': request.headers.get('User-Agent', 'Unknown'),
    }


@contact_bp.route('/contact', methods=['POST'])
def submit_contact_form():
    """
    Handle contact form submission and publish ContactFormSubmitted event.
    
    Expected JSON payload:
    {
        "form_data": {
            "name": "John Doe",
            "email": "john@example.com",
            "company": "Acme Corp",
            "phone": "+1-555-123-4567",
            "message": "Interested in your services",
            "preferred_contact_method": "email",
            "consent_marketing": true,
            "consent_data_processing": true
        },
        "metadata": {
            "session_id": "sess_123",
            "form_version": "1.0.0",
            "submission_duration_ms": 45000
        }
    }
    """
    start_time = time.time()
    correlation_id = str(uuid.uuid4())
    
    try:
        # Paso 1: Validar content type
        logger.info(f"[Paso 1] Validando content type para correlation_id={correlation_id}")
        if not request.is_json:
            logger.warning(f"[Paso 1] Invalid content type: {request.content_type} para correlation_id={correlation_id}")
            return jsonify({
                'error': 'Content-Type must be application/json',
                'correlation_id': correlation_id
            }), 400
        logger.info(f"[Paso 1] Content type válido para correlation_id={correlation_id}")

        # Paso 2: Obtener datos del request
        logger.info(f"[Paso 2] Obteniendo datos del request para correlation_id={correlation_id}")
        request_data = request.get_json()
        if not request_data:
            logger.warning(f"[Paso 2] Empty request body para correlation_id={correlation_id}")
            return jsonify({
                'error': 'Request body cannot be empty',
                'correlation_id': correlation_id
            }), 400
        logger.info(f"[Paso 2] Datos del request obtenidos para correlation_id={correlation_id}")

        # Paso 3: Extraer form_data y metadata
        logger.info(f"[Paso 3] Extrayendo form_data y metadata para correlation_id={correlation_id}")
        form_data = request_data.get('form_data', {})
        request_metadata = request_data.get('metadata', {})
        logger.info(f"[Paso 3] form_data y metadata extraídos para correlation_id={correlation_id}")

        # Paso 4: Validar campos requeridos
        logger.info(f"[Paso 4] Validando campos requeridos para correlation_id={correlation_id}")
        required_fields = ['name', 'email', 'company', 'message', 'preferred_contact_method', 
                          'consent_marketing', 'consent_data_processing']
        missing_fields = [field for field in required_fields if field not in form_data]
        
        if missing_fields:
            logger.warning(f"[Paso 4] Missing required fields: {missing_fields} para correlation_id={correlation_id}")
            return jsonify({
                'error': 'Missing required fields',
                'missing_fields': missing_fields,
                'correlation_id': correlation_id
            }), 400
        logger.info(f"[Paso 4] Todos los campos requeridos presentes para correlation_id={correlation_id}")

        # Paso 5: Validar consentimiento de procesamiento de datos
        logger.info(f"[Paso 5] Validando consentimiento de procesamiento de datos para correlation_id={correlation_id}")
        if not form_data.get('consent_data_processing'):
            logger.warning(f"[Paso 5] Data processing consent not provided para correlation_id={correlation_id}")
            return jsonify({
                'error': 'Data processing consent is required',
                'correlation_id': correlation_id
            }), 400
        logger.info(f"[Paso 5] Consentimiento de procesamiento de datos otorgado para correlation_id={correlation_id}")

        # Paso 6: Crear event_data completo
        logger.info(f"[Paso 6] Creando event_data completo para correlation_id={correlation_id}")
        event_data = create_contact_form_event_data(form_data, request_metadata)
        logger.info(f"[Paso 6] event_data creado para correlation_id={correlation_id}")

        # Paso 7: Validar event_data contra el schema
        logger.info(f"[Paso 7] Validando event_data contra el schema para correlation_id={correlation_id}")
        schema = ContactFormSubmittedEventSchema()
        try:
            event_for_validation = {
                'id': str(uuid.uuid4()),
                'occurred_at': datetime.now(timezone.utc).isoformat(),
                'source': EventSources.WEB,
                'type': EventType.CONTACT_FORM_SUBMITTED.value,
                'version': '1.0',
                'correlation_id': correlation_id,
                **event_data
            }
            
            validated_event = schema.load(event_for_validation)
            logger.info(f"[Paso 7] Event validation successful para correlation_id={correlation_id}")
            
        except ValidationError as e:
            logger.error(f"[Paso 7] Event validation failed: {e.messages} para correlation_id={correlation_id}")
            return jsonify({
                'error': 'Invalid form data',
                'validation_errors': e.messages,
                'correlation_id': correlation_id
            }), 400

        # Paso 8: Publicar evento a Kafka
        logger.info(f"[Paso 8] Publicando evento a Kafka para correlation_id={correlation_id}")
        event_publisher = get_event_publisher()
        published_event = event_publisher.publish_contact_form_submitted(
            event_data=event_data,
            correlation_id=correlation_id
        )
        
        if not published_event:
            logger.error(f"[Paso 8] Failed to publish event para correlation_id={correlation_id}")
            return jsonify({
                'error': 'Failed to process form submission',
                'correlation_id': correlation_id
            }), 500
        logger.info(f"[Paso 8] Evento publicado en Kafka para correlation_id={correlation_id}")

        # Paso 9: Calcular tiempo de procesamiento
        processing_time_ms = int((time.time() - start_time) * 1000)
        logger.info(f"[Paso 9] Tiempo de procesamiento calculado: {processing_time_ms} ms para correlation_id={correlation_id}")

        # Paso 10: Log de envío exitoso
        logger.info(
            f"[Paso 10] Contact form submitted successfully: "
            f"event_id={published_event.id}, "
            f"correlation_id={correlation_id}, "
            f"email={form_data['email']}, "
            f"company={form_data['company']}, "
            f"processing_time_ms={processing_time_ms}"
        )

        # Paso 11: Responder al cliente
        logger.info(f"[Paso 11] Enviando respuesta de éxito al cliente para correlation_id={correlation_id}")
        return jsonify({
            'message': 'Contact form submitted successfully',
            'event_id': published_event.id,
            'correlation_id': correlation_id,
            'processing_time_ms': processing_time_ms,
            'status': 'accepted'
        }), 202
        
    except BadRequest as e:
        logger.warning(f"[Error] Bad request: {e} para correlation_id={correlation_id}")
        return jsonify({
            'error': 'Invalid request format',
            'correlation_id': correlation_id
        }), 400
        
    except Exception as e:
        logger.error(f"[Error] Unexpected error processing contact form: {e}", exc_info=True)
        return jsonify({
            'error': 'Internal server error',
            'correlation_id': correlation_id
        }), 500


@contact_bp.route('/contact/health', methods=['GET'])
def contact_health():
    """Health check endpoint for contact form service."""
    try:
        # Check event publisher health
        event_publisher = get_event_publisher()
        publisher_health = event_publisher.health_check()
        
        overall_status = 'healthy' if publisher_health['status'] == 'healthy' else 'unhealthy'
        
        health_data = {
            'status': overall_status,
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'service': 'contact-form-api',
            'version': '1.0.0',
            'components': {
                'event_publisher': publisher_health
            }
        }
        
        status_code = 200 if overall_status == 'healthy' else 503
        return jsonify(health_data), status_code
        
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return jsonify({
            'status': 'unhealthy',
            'error': str(e),
            'timestamp': datetime.now(timezone.utc).isoformat()
        }), 503


@contact_bp.route('/contact/metrics', methods=['GET'])
def contact_metrics():
    """Metrics endpoint for monitoring and observability."""
    try:
        # In a real implementation, these would come from a metrics store
        metrics = {
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'service': 'contact-form-api',
            'metrics': {
                'total_submissions': 0,  # Would be tracked in Redis/database
                'successful_submissions': 0,
                'failed_submissions': 0,
                'average_processing_time_ms': 0,
                'event_publisher_status': get_event_publisher().health_check()['status']
            }
        }
        
        return jsonify(metrics), 200
        
    except Exception as e:
        logger.error(f"Metrics collection failed: {e}")
        return jsonify({
            'error': 'Failed to collect metrics',
            'timestamp': datetime.now(timezone.utc).isoformat()
        }), 500


@contact_bp.errorhandler(404)
def not_found(error):
    """Handle 404 errors for contact routes."""
    return jsonify({
        'error': 'Endpoint not found',
        'message': 'The requested endpoint does not exist'
    }), 404


@contact_bp.errorhandler(405)
def method_not_allowed(error):
    """Handle 405 errors for contact routes."""
    return jsonify({
        'error': 'Method not allowed',
        'message': 'The HTTP method is not allowed for this endpoint'
    }), 405


@contact_bp.errorhandler(500)
def internal_error(error):
    """Handle 500 errors for contact routes."""
    logger.error(f"Internal server error: {error}")
    return jsonify({
        'error': 'Internal server error',
        'message': 'An unexpected error occurred'
    }), 500

