"""
Unit tests for contact form routes in the API service.
"""

import json
import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timezone

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from main import create_app
from services.event_publisher import EventPublisher


@pytest.fixture
def app():
    """Create test Flask application."""
    app = create_app()
    app.config['TESTING'] = True
    return app


@pytest.fixture
def client(app):
    """Create test client."""
    return app.test_client()


@pytest.fixture
def mock_event_publisher():
    """Mock event publisher."""
    with patch('routes.contact.EventPublisher') as mock_publisher_class:
        mock_publisher = Mock(spec=EventPublisher)
        mock_publisher_class.return_value = mock_publisher
        mock_publisher.publish_event.return_value = True
        yield mock_publisher


class TestContactFormSubmission:
    """Test contact form submission functionality."""
    
    def test_submit_contact_form_success(self, client, mock_event_publisher):
        """Test successful contact form submission."""
        form_data = {
            'name': 'John Doe',
            'email': 'john.doe@example.com',
            'company': 'Acme Corp',
            'phone': '+1-555-0123',
            'message': 'I am interested in your event-driven architecture solutions.',
            'preferred_contact_method': 'email',
            'consent_marketing': True,
            'consent_data_processing': True
        }
        
        response = client.post('/api/contact/submit', 
                             data=json.dumps(form_data),
                             content_type='application/json')
        
        assert response.status_code == 201
        
        response_data = json.loads(response.data)
        assert response_data['success'] is True
        assert 'event_id' in response_data
        assert 'correlation_id' in response_data
        assert response_data['message'] == 'Contact form submitted successfully'
        
        # Verify event publisher was called
        mock_event_publisher.publish_event.assert_called_once()
    
    def test_submit_contact_form_missing_required_fields(self, client):
        """Test contact form submission with missing required fields."""
        form_data = {
            'name': 'John Doe',
            'email': 'john.doe@example.com'
            # Missing required fields: company, message, consent fields
        }
        
        response = client.post('/api/contact/submit',
                             data=json.dumps(form_data),
                             content_type='application/json')
        
        assert response.status_code == 400
        
        response_data = json.loads(response.data)
        assert response_data['success'] is False
        assert 'validation_errors' in response_data
    
    def test_submit_contact_form_invalid_email(self, client):
        """Test contact form submission with invalid email."""
        form_data = {
            'name': 'John Doe',
            'email': 'invalid-email',
            'company': 'Acme Corp',
            'message': 'Test message',
            'preferred_contact_method': 'email',
            'consent_marketing': True,
            'consent_data_processing': True
        }
        
        response = client.post('/api/contact/submit',
                             data=json.dumps(form_data),
                             content_type='application/json')
        
        assert response.status_code == 400
        
        response_data = json.loads(response.data)
        assert response_data['success'] is False
        assert 'validation_errors' in response_data
    
    def test_submit_contact_form_invalid_preferred_contact_method(self, client):
        """Test contact form submission with invalid preferred contact method."""
        form_data = {
            'name': 'John Doe',
            'email': 'john.doe@example.com',
            'company': 'Acme Corp',
            'message': 'Test message',
            'preferred_contact_method': 'invalid_method',
            'consent_marketing': True,
            'consent_data_processing': True
        }
        
        response = client.post('/api/contact/submit',
                             data=json.dumps(form_data),
                             content_type='application/json')
        
        assert response.status_code == 400
        
        response_data = json.loads(response.data)
        assert response_data['success'] is False
        assert 'validation_errors' in response_data
    
    def test_submit_contact_form_missing_consent(self, client):
        """Test contact form submission without required consent."""
        form_data = {
            'name': 'John Doe',
            'email': 'john.doe@example.com',
            'company': 'Acme Corp',
            'message': 'Test message',
            'preferred_contact_method': 'email',
            'consent_marketing': False,
            'consent_data_processing': False
        }
        
        response = client.post('/api/contact/submit',
                             data=json.dumps(form_data),
                             content_type='application/json')
        
        assert response.status_code == 400
        
        response_data = json.loads(response.data)
        assert response_data['success'] is False
        assert 'consent is required' in response_data['message'].lower()
    
    def test_submit_contact_form_event_publishing_failure(self, client, mock_event_publisher):
        """Test contact form submission when event publishing fails."""
        mock_event_publisher.publish_event.return_value = False
        
        form_data = {
            'name': 'John Doe',
            'email': 'john.doe@example.com',
            'company': 'Acme Corp',
            'message': 'Test message',
            'preferred_contact_method': 'email',
            'consent_marketing': True,
            'consent_data_processing': True
        }
        
        response = client.post('/api/contact/submit',
                             data=json.dumps(form_data),
                             content_type='application/json')
        
        assert response.status_code == 500
        
        response_data = json.loads(response.data)
        assert response_data['success'] is False
        assert 'failed to publish event' in response_data['message'].lower()
    
    def test_submit_contact_form_invalid_json(self, client):
        """Test contact form submission with invalid JSON."""
        response = client.post('/api/contact/submit',
                             data='invalid json',
                             content_type='application/json')
        
        assert response.status_code == 400
        
        response_data = json.loads(response.data)
        assert response_data['success'] is False
    
    def test_submit_contact_form_empty_request(self, client):
        """Test contact form submission with empty request."""
        response = client.post('/api/contact/submit',
                             data=json.dumps({}),
                             content_type='application/json')
        
        assert response.status_code == 400
        
        response_data = json.loads(response.data)
        assert response_data['success'] is False
        assert 'validation_errors' in response_data
    
    def test_submit_contact_form_long_message(self, client, mock_event_publisher):
        """Test contact form submission with very long message."""
        form_data = {
            'name': 'John Doe',
            'email': 'john.doe@example.com',
            'company': 'Acme Corp',
            'message': 'A' * 3000,  # Very long message
            'preferred_contact_method': 'email',
            'consent_marketing': True,
            'consent_data_processing': True
        }
        
        response = client.post('/api/contact/submit',
                             data=json.dumps(form_data),
                             content_type='application/json')
        
        assert response.status_code == 400
        
        response_data = json.loads(response.data)
        assert response_data['success'] is False
        assert 'validation_errors' in response_data


class TestContactFormValidation:
    """Test contact form validation logic."""
    
    @pytest.mark.parametrize("name,expected_valid", [
        ("John Doe", True),
        ("Jane Smith-Johnson", True),
        ("José García", True),
        ("", False),
        ("A" * 101, False),  # Too long
        ("123", False),  # Numbers only
    ])
    def test_name_validation(self, client, name, expected_valid):
        """Test name field validation."""
        form_data = {
            'name': name,
            'email': 'test@example.com',
            'company': 'Test Corp',
            'message': 'Test message',
            'preferred_contact_method': 'email',
            'consent_marketing': True,
            'consent_data_processing': True
        }
        
        response = client.post('/api/contact/submit',
                             data=json.dumps(form_data),
                             content_type='application/json')
        
        if expected_valid:
            assert response.status_code in [201, 500]  # 500 if event publishing fails
        else:
            assert response.status_code == 400
    
    @pytest.mark.parametrize("email,expected_valid", [
        ("test@example.com", True),
        ("user.name+tag@domain.co.uk", True),
        ("invalid-email", False),
        ("@domain.com", False),
        ("user@", False),
        ("", False),
    ])
    def test_email_validation(self, client, email, expected_valid):
        """Test email field validation."""
        form_data = {
            'name': 'John Doe',
            'email': email,
            'company': 'Test Corp',
            'message': 'Test message',
            'preferred_contact_method': 'email',
            'consent_marketing': True,
            'consent_data_processing': True
        }
        
        response = client.post('/api/contact/submit',
                             data=json.dumps(form_data),
                             content_type='application/json')
        
        if expected_valid:
            assert response.status_code in [201, 500]  # 500 if event publishing fails
        else:
            assert response.status_code == 400


class TestHealthEndpoint:
    """Test health check endpoint."""
    
    def test_health_endpoint(self, client):
        """Test health check endpoint returns success."""
        response = client.get('/health')
        
        assert response.status_code == 200
        
        response_data = json.loads(response.data)
        assert response_data['status'] == 'healthy'
        assert 'timestamp' in response_data
        assert 'version' in response_data


class TestCORSHeaders:
    """Test CORS headers are properly set."""
    
    def test_cors_headers_on_options(self, client):
        """Test CORS headers on OPTIONS request."""
        response = client.options('/api/contact/submit')
        
        assert response.status_code == 200
        assert 'Access-Control-Allow-Origin' in response.headers
        assert 'Access-Control-Allow-Methods' in response.headers
        assert 'Access-Control-Allow-Headers' in response.headers
    
    def test_cors_headers_on_post(self, client):
        """Test CORS headers on POST request."""
        form_data = {
            'name': 'John Doe',
            'email': 'john.doe@example.com',
            'company': 'Acme Corp',
            'message': 'Test message',
            'preferred_contact_method': 'email',
            'consent_marketing': True,
            'consent_data_processing': True
        }
        
        response = client.post('/api/contact/submit',
                             data=json.dumps(form_data),
                             content_type='application/json')
        
        assert 'Access-Control-Allow-Origin' in response.headers

