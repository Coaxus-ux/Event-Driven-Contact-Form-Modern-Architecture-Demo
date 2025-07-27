"""
Unit tests for event publisher in the API service.
"""

import json
import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timezone

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from services.event_publisher import EventPublisher
from models.events import BaseEvent, EventTypes, EventSources


class TestEventPublisher:
    """Test event publisher functionality."""
    
    @pytest.fixture
    def mock_kafka_producer(self):
        """Mock Kafka producer."""
        with patch('services.event_publisher.KafkaProducer') as mock_producer_class:
            mock_producer = Mock()
            mock_producer_class.return_value = mock_producer
            
            # Mock successful send
            mock_future = Mock()
            mock_future.get.return_value = Mock(
                topic='test-topic',
                partition=0,
                offset=123
            )
            mock_producer.send.return_value = mock_future
            
            yield mock_producer
    
    def test_event_publisher_initialization(self, mock_kafka_producer):
        """Test event publisher initialization."""
        publisher = EventPublisher()
        
        assert publisher.producer is not None
        assert publisher.bootstrap_servers == 'localhost:9092'
        assert publisher.topic_prefix == 'events'
    
    def test_publish_event_success(self, mock_kafka_producer):
        """Test successful event publishing."""
        publisher = EventPublisher()
        
        # Create test event
        event_data = {
            'form_data': {
                'name': 'John Doe',
                'email': 'john@example.com',
                'company': 'Acme Corp',
                'message': 'Test message'
            }
        }
        
        event = BaseEvent.create(
            event_type=EventTypes.CONTACT_FORM_SUBMITTED,
            source=EventSources.WEB,
            data=event_data
        )
        
        # Publish event
        result = publisher.publish_event(event, 'contact_form')
        
        assert result is True
        mock_kafka_producer.send.assert_called_once()
        
        # Verify call arguments
        call_args = mock_kafka_producer.send.call_args
        assert call_args[1]['topic'] == 'events.contact_form'
        assert call_args[1]['key'] == event.correlation_id
        assert 'value' in call_args[1]
    
    def test_publish_event_without_topic_suffix(self, mock_kafka_producer):
        """Test event publishing without topic suffix."""
        publisher = EventPublisher()
        
        event_data = {'test': 'data'}
        event = BaseEvent.create(
            event_type=EventTypes.CONTACT_FORM_SUBMITTED,
            source=EventSources.WEB,
            data=event_data
        )
        
        result = publisher.publish_event(event)
        
        assert result is True
        
        # Verify topic name derived from event type
        call_args = mock_kafka_producer.send.call_args
        assert call_args[1]['topic'] == 'events.contactformsubmitted'
    
    def test_publish_event_kafka_timeout(self, mock_kafka_producer):
        """Test event publishing with Kafka timeout."""
        from kafka.errors import KafkaTimeoutError
        
        # Mock timeout error
        mock_future = Mock()
        mock_future.get.side_effect = KafkaTimeoutError("Timeout")
        mock_kafka_producer.send.return_value = mock_future
        
        publisher = EventPublisher()
        
        event_data = {'test': 'data'}
        event = BaseEvent.create(
            event_type=EventTypes.CONTACT_FORM_SUBMITTED,
            source=EventSources.WEB,
            data=event_data
        )
        
        result = publisher.publish_event(event, 'test_topic')
        
        assert result is False
    
    def test_publish_event_kafka_error(self, mock_kafka_producer):
        """Test event publishing with Kafka error."""
        from kafka.errors import KafkaError
        
        # Mock Kafka error
        mock_future = Mock()
        mock_future.get.side_effect = KafkaError("Connection failed")
        mock_kafka_producer.send.return_value = mock_future
        
        publisher = EventPublisher()
        
        event_data = {'test': 'data'}
        event = BaseEvent.create(
            event_type=EventTypes.CONTACT_FORM_SUBMITTED,
            source=EventSources.WEB,
            data=event_data
        )
        
        result = publisher.publish_event(event, 'test_topic')
        
        assert result is False
    
    def test_publish_event_no_producer(self):
        """Test event publishing when producer is not initialized."""
        publisher = EventPublisher()
        publisher.producer = None
        
        event_data = {'test': 'data'}
        event = BaseEvent.create(
            event_type=EventTypes.CONTACT_FORM_SUBMITTED,
            source=EventSources.WEB,
            data=event_data
        )
        
        result = publisher.publish_event(event, 'test_topic')
        
        assert result is False
    
    def test_health_check_healthy(self, mock_kafka_producer):
        """Test health check when publisher is healthy."""
        # Mock successful metadata retrieval
        mock_metadata = Mock()
        mock_metadata.topics = {'topic1': Mock(), 'topic2': Mock()}
        mock_kafka_producer.list_topics.return_value = mock_metadata
        
        publisher = EventPublisher()
        
        health_status = publisher.health_check()
        
        assert health_status['status'] == 'healthy'
        assert health_status['available_topics'] == 2
        assert 'bootstrap_servers' in health_status
        assert 'producer_config' in health_status
    
    def test_health_check_unhealthy_no_producer(self):
        """Test health check when producer is not initialized."""
        publisher = EventPublisher()
        publisher.producer = None
        
        health_status = publisher.health_check()
        
        assert health_status['status'] == 'unhealthy'
        assert 'error' in health_status
    
    def test_health_check_unhealthy_exception(self, mock_kafka_producer):
        """Test health check when exception occurs."""
        # Mock exception during metadata retrieval
        mock_kafka_producer.list_topics.side_effect = Exception("Connection failed")
        
        publisher = EventPublisher()
        
        health_status = publisher.health_check()
        
        assert health_status['status'] == 'unhealthy'
        assert 'error' in health_status
    
    def test_close_publisher(self, mock_kafka_producer):
        """Test closing the event publisher."""
        publisher = EventPublisher()
        
        publisher.close()
        
        mock_kafka_producer.flush.assert_called_once_with(timeout=10)
        mock_kafka_producer.close.assert_called_once_with(timeout=10)
        assert publisher.producer is None
    
    def test_close_publisher_with_error(self, mock_kafka_producer):
        """Test closing the event publisher when error occurs."""
        mock_kafka_producer.flush.side_effect = Exception("Flush failed")
        
        publisher = EventPublisher()
        
        # Should not raise exception
        publisher.close()
        
        assert publisher.producer is None
    
    def test_context_manager(self, mock_kafka_producer):
        """Test event publisher as context manager."""
        with EventPublisher() as publisher:
            assert publisher.producer is not None
        
        # Should be closed after context
        mock_kafka_producer.flush.assert_called_once()
        mock_kafka_producer.close.assert_called_once()


class TestEventSerialization:
    """Test event serialization for Kafka."""
    
    def test_event_metadata_added(self, mock_kafka_producer):
        """Test that metadata is added to events before publishing."""
        publisher = EventPublisher()
        
        event_data = {'test': 'data'}
        event = BaseEvent.create(
            event_type=EventTypes.CONTACT_FORM_SUBMITTED,
            source=EventSources.WEB,
            data=event_data
        )
        
        publisher.publish_event(event, 'test_topic')
        
        # Get the serialized event data
        call_args = mock_kafka_producer.send.call_args
        serialized_event = call_args[1]['value']
        
        assert '_metadata' in serialized_event
        assert 'published_at' in serialized_event['_metadata']
        assert 'publisher' in serialized_event['_metadata']
        assert 'topic' in serialized_event['_metadata']
        assert 'partition_key' in serialized_event['_metadata']
    
    def test_event_headers_set(self, mock_kafka_producer):
        """Test that proper headers are set for events."""
        publisher = EventPublisher()
        
        event_data = {'test': 'data'}
        event = BaseEvent.create(
            event_type=EventTypes.CONTACT_FORM_SUBMITTED,
            source=EventSources.WEB,
            data=event_data
        )
        
        publisher.publish_event(event, 'test_topic')
        
        # Get the headers
        call_args = mock_kafka_producer.send.call_args
        headers = call_args[1]['headers']
        
        header_dict = {k: v.decode('utf-8') for k, v in headers}
        
        assert 'event_type' in header_dict
        assert 'event_id' in header_dict
        assert 'correlation_id' in header_dict
        assert 'source' in header_dict
        
        assert header_dict['event_type'] == EventTypes.CONTACT_FORM_SUBMITTED
        assert header_dict['event_id'] == event.id
        assert header_dict['correlation_id'] == event.correlation_id
        assert header_dict['source'] == EventSources.WEB

