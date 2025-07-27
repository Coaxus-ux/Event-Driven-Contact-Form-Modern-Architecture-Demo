"""
Event publisher for the Mailer service.
Publishes EmailDispatched events back to Kafka.
"""

import json
import logging
import os
from typing import Dict, Any, Optional
from kafka import KafkaProducer
from kafka.errors import KafkaError, KafkaTimeoutError
import time

from event_models import BaseEvent


class EventPublisher:
    """Service for publishing events to Kafka with reliability features."""
    
    def __init__(self, bootstrap_servers: Optional[str] = None):
        """Initialize the event publisher with Kafka configuration."""
        self.bootstrap_servers = bootstrap_servers or os.getenv('KAFKA_BOOTSTRAP_SERVERS', 'localhost:9092')
        self.topic_prefix = os.getenv('KAFKA_TOPIC_PREFIX', 'events')
        self.producer = None
        self.logger = logging.getLogger(__name__)
        
        # Configuration for reliable publishing
        self.producer_config = {
            'bootstrap_servers': self.bootstrap_servers.split(','),
            'value_serializer': lambda v: json.dumps(v).encode('utf-8'),
            'key_serializer': lambda k: k.encode('utf-8') if k else None,
            'acks': 'all',
            'retries': 3,
            'retry_backoff_ms': 100,
            'request_timeout_ms': 30000,
            'compression_type': 'gzip',
            'batch_size': 16384,
            'linger_ms': 10,
        }

        
        self._initialize_producer()
    
    def _initialize_producer(self):
        """Initialize the Kafka producer with retry logic."""
        max_retries = 5
        retry_delay = 1
        
        for attempt in range(max_retries):
            try:
                self.producer = KafkaProducer(**self.producer_config)
                self.logger.info(f"Kafka producer initialized successfully on attempt {attempt + 1}")
                return
            except Exception as e:
                self.logger.warning(f"Failed to initialize Kafka producer (attempt {attempt + 1}/{max_retries}): {e}")
                if attempt < max_retries - 1:
                    time.sleep(retry_delay)
                    retry_delay *= 2  # Exponential backoff
                else:
                    self.logger.error("Failed to initialize Kafka producer after all retries")
                    raise
    
    def publish_event(self, event: BaseEvent, topic_suffix: Optional[str] = None) -> bool:
        """
        Publish an event to Kafka.
        
        Args:
            event: The event to publish
            topic_suffix: Optional suffix for the topic name
            
        Returns:
            bool: True if event was published successfully, False otherwise
        """
        if not self.producer:
            self.logger.error("Kafka producer not initialized")
            return False
        
        try:
            # Determine topic name
            topic = f"{self.topic_prefix}.{topic_suffix}" if topic_suffix else f"{self.topic_prefix}.{event.type.lower()}"
            
            # Use correlation_id as the partition key for ordering
            partition_key = event.correlation_id
            
            # Convert event to dictionary for serialization
            event_data = event.to_dict()
            
            # Add metadata for observability
            event_data['_metadata'] = {
                'published_at': time.time(),
                'publisher': 'mailer-service',
                'topic': topic,
                'partition_key': partition_key
            }
            
            # Publish the event
            future = self.producer.send(
                topic=topic,
                key=partition_key,
                value=event_data,
                headers=[
                    ('event_type', event.type.encode('utf-8')),
                    ('event_id', event.id.encode('utf-8')),
                    ('correlation_id', event.correlation_id.encode('utf-8')),
                    ('source', event.source.encode('utf-8'))
                ]
            )
            
            # Wait for the message to be sent (with timeout)
            record_metadata = future.get(timeout=10)
            
            self.logger.info(
                f"Event published successfully: {event.type} "
                f"(id={event.id}, topic={record_metadata.topic}, "
                f"partition={record_metadata.partition}, offset={record_metadata.offset})"
            )
            
            return True
            
        except KafkaTimeoutError as e:
            self.logger.error(f"Timeout publishing event {event.id}: {e}")
            return False
        except KafkaError as e:
            self.logger.error(f"Kafka error publishing event {event.id}: {e}")
            return False
        except Exception as e:
            self.logger.error(f"Unexpected error publishing event {event.id}: {e}")
            return False
    
    def health_check(self) -> Dict[str, Any]:
        """
        Check the health of the event publisher.
        
        Returns:
            Dict containing health status information
        """
        try:
            if not self.producer:
                return {
                    'status': 'unhealthy',
                    'error': 'Producer not initialized'
                }
            
            # Try to get cluster metadata as a health check
            metadata = self.producer.list_topics(timeout=5)
            
            return {
                'status': 'healthy',
                'bootstrap_servers': self.bootstrap_servers,
                'available_topics': len(metadata.topics),
                'producer_config': {
                    'acks': self.producer_config['acks'],
                    'retries': self.producer_config['retries'],
                    'enable_idempotence': self.producer_config['enable_idempotence']
                }
            }
            
        except Exception as e:
            return {
                'status': 'unhealthy',
                'error': str(e)
            }
    
    def close(self):
        """Close the Kafka producer and clean up resources."""
        if self.producer:
            try:
                self.producer.flush(timeout=10)  # Ensure all messages are sent
                self.producer.close(timeout=10)
                self.logger.info("Kafka producer closed successfully")
            except Exception as e:
                self.logger.error(f"Error closing Kafka producer: {e}")
            finally:
                self.producer = None
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()

