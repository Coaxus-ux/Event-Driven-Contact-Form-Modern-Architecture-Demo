"""
Mailer Service for Event-Driven Architecture PoC
Consumes ContactFormSubmitted events and sends personalized emails.
"""

import json
import logging
import os
import smtplib
import time
from datetime import datetime, timezone
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Dict, Any, Optional
import uuid

from kafka import KafkaConsumer
from kafka.errors import KafkaError
import pystache
from marshmallow import ValidationError

from event_models import BaseEvent, ContactFormSubmittedSchema, EventTypes, EventSources, transform_event
from event_publisher import EventPublisher
from template_engine import TemplateEngine


class MailerService:
    """
    Mailer service that consumes events and sends emails.
    """
    
    def __init__(self):
        """Initialize the mailer service."""
        self.logger = logging.getLogger(__name__)
        
        # Kafka configuration
        self.kafka_bootstrap_servers = os.getenv('KAFKA_BOOTSTRAP_SERVERS', 'localhost:9092')
        self.kafka_topic = os.getenv('KAFKA_TOPIC', 'events.contact_form')
        self.consumer_group = os.getenv('KAFKA_CONSUMER_GROUP', 'mailer-service')
        
        # SMTP configuration (defaults to MailHog for development)
        self.logger.info(f"------> {os.getenv('SMTP_HOST')}")
        self.smtp_host = os.getenv('SMTP_HOST', 'mailhog')
        self.smtp_port = int(os.getenv('SMTP_PORT', '1025'))  # MailHog default port
        self.smtp_username = os.getenv('SMTP_USERNAME', '')
        self.smtp_password = os.getenv('SMTP_PASSWORD', '')
        self.smtp_use_tls = os.getenv('SMTP_USE_TLS', 'false').lower() == 'true'  # MailHog doesn't use TLS by default
        self.from_email = os.getenv('FROM_EMAIL', 'noreply@example.com')
        self.from_name = os.getenv('FROM_NAME', 'Event-Driven PoC')
        
        # Service configuration
        self.service_name = 'mailer-service'
        self.service_version = '1.0.0'
        
        # Initialize components
        self.consumer = None
        self.event_publisher = EventPublisher()
        self.template_engine = TemplateEngine()
        self.running = False
        
        # Metrics
        self.metrics = {
            'emails_sent': 0,
            'emails_failed': 0,
            'events_processed': 0,
            'events_failed': 0,
            'start_time': time.time()
        }
    
    def _initialize_consumer(self):
        """Initialize Kafka consumer with retry logic."""
        consumer_config = {
            'bootstrap_servers': self.kafka_bootstrap_servers.split(','),
            'group_id': self.consumer_group,
            'auto_offset_reset': 'earliest',
            'enable_auto_commit': True,
            'auto_commit_interval_ms': 1000,
            'value_deserializer': lambda m: json.loads(m.decode('utf-8')),
            'key_deserializer': lambda k: k.decode('utf-8') if k else None,
            'session_timeout_ms': 30000,
            'heartbeat_interval_ms': 10000,
            'max_poll_records': 10,
            'max_poll_interval_ms': 300000
        }
        
        max_retries = 5
        retry_delay = 1
        
        for attempt in range(max_retries):
            try:
                self.consumer = KafkaConsumer(self.kafka_topic, **consumer_config)
                self.logger.info(f"Kafka consumer initialized successfully on attempt {attempt + 1}")
                return
            except Exception as e:
                self.logger.warning(f"Failed to initialize Kafka consumer (attempt {attempt + 1}/{max_retries}): {e}")
                if attempt < max_retries - 1:
                    time.sleep(retry_delay)
                    retry_delay *= 2
                else:
                    self.logger.error("Failed to initialize Kafka consumer after all retries")
                    raise
    
    def _send_email(self, to_email: str, subject: str, html_content: str, 
                   text_content: str, correlation_id: str) -> Dict[str, Any]:
        """
        Send email via SMTP.
        
        Args:
            to_email: Recipient email address
            subject: Email subject
            html_content: HTML email content
            text_content: Plain text email content
            correlation_id: Correlation ID for tracing
            
        Returns:
            Dict containing delivery information
        """
        start_time = time.time()
        
        try:
            # Create message
            msg = MIMEMultipart('alternative')
            msg['Subject'] = subject
            msg['From'] = f"{self.from_name} <{self.from_email}>"
            msg['To'] = to_email
            msg['Message-ID'] = f"<{uuid.uuid4()}@{self.smtp_host}>"
            msg['X-Correlation-ID'] = correlation_id
            
            # Attach text and HTML parts
            text_part = MIMEText(text_content, 'plain', 'utf-8')
            html_part = MIMEText(html_content, 'html', 'utf-8')
            
            msg.attach(text_part)
            msg.attach(html_part)
            
            # Send email
            self.logger.info(f"------> {self.smtp_host}")
            if self.smtp_host in ('localhost', 'mailhog') and self.smtp_port == 1025:
                with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                    smtp_response = server.send_message(msg)
                    self.logger.info(f"Email sent to MailHog: To={to_email}, Subject={subject}")
                    self.logger.info(f"Check MailHog UI at http://localhost:8025 to view the email")
            else:
                # Real SMTP
                with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                    if self.smtp_use_tls:
                        server.starttls()
                    if self.smtp_username and self.smtp_password:
                        server.login(self.smtp_username, self.smtp_password)
                    
                    smtp_response = server.send_message(msg)
                    self.logger.info(f"Email sent successfully to {to_email}")
            
            processing_duration = int((time.time() - start_time) * 1000)
            content_size = len(html_content.encode('utf-8')) + len(text_content.encode('utf-8'))
            
            return {
                'success': True,
                'message_id': msg['Message-ID'],
                'smtp_response': str(smtp_response),
                'delivery_attempt': 1,
                'processing_duration_ms': processing_duration,
                'content_size_bytes': content_size
            }
            
        except Exception as e:
            processing_duration = int((time.time() - start_time) * 1000)
            self.logger.error(f"Failed to send email to {to_email}: {e}")
            
            return {
                'success': False,
                'error': str(e),
                'delivery_attempt': 1,
                'processing_duration_ms': processing_duration,
                'content_size_bytes': 0
            }
    
    def _process_contact_form_event(self, event_data: Dict[str, Any]) -> bool:
        """
        Process a ContactFormSubmitted event.
        
        Args:
            event_data: The event data
            
        Returns:
            bool: True if processed successfully, False otherwise
        """
        try:
            # Validate event structure
            schema = ContactFormSubmittedSchema()
            validated_event = schema.load(event_data)
            
            # Extract form data
            form_data = event_data['data']['form_data']
            correlation_id = event_data['correlation_id']
            
            self.logger.info(f"Processing contact form event: {correlation_id}")
            
            # Prepare template data
            template_data = {
                'name': form_data['name'].split()[0],  # First name only
                'full_name': form_data['name'],
                'email': form_data['email'],
                'company': form_data['company'],
                'phone': form_data.get('phone', 'Not provided'),
                'message': form_data['message'],
                'preferred_contact_method': form_data['preferred_contact_method'],
                'submission_date': datetime.now().strftime('%B %d, %Y'),
                'submission_time': datetime.now().strftime('%I:%M %p'),
                'correlation_id': correlation_id
            }
            
            # Generate email content
            subject = f"Thank you for your interest, {template_data['name']}!"
            html_content = self.template_engine.render_html_template('contact_confirmation', template_data)
            text_content = self.template_engine.render_text_template('contact_confirmation', template_data)
            
            # Send email
            delivery_result = self._send_email(
                to_email=form_data['email'],
                subject=subject,
                html_content=html_content,
                text_content=text_content,
                correlation_id=correlation_id
            )
            
            if delivery_result['success']:
                # Publish EmailDispatched event
                email_dispatched_data = {
                    'email_details': {
                        'recipient': form_data['email'],
                        'subject': subject,
                        'template_name': 'contact_confirmation',
                        'template_version': '1.0.0',
                        'personalization_data': {
                            'name': template_data['name'],
                            'company': template_data['company']
                        }
                    },
                    'delivery': {
                        'message_id': delivery_result['message_id'],
                        'smtp_response': delivery_result['smtp_response'],
                        'delivery_attempt': delivery_result['delivery_attempt'],
                        'processing_duration_ms': delivery_result['processing_duration_ms'],
                        'content_size_bytes': delivery_result['content_size_bytes']
                    },
                    'tracking': {
                        'tracking_pixel_url': f"https://track.example.com/open/{correlation_id}",
                        'unsubscribe_url': f"https://example.com/unsubscribe/{correlation_id}",
                        'click_tracking_enabled': True
                    }
                }
                
                email_event = BaseEvent.create(
                    event_type=EventTypes.EMAIL_DISPATCHED,
                    source=EventSources.MAILER_SERVICE,
                    data=email_dispatched_data,
                    correlation_id=correlation_id,
                    causation_id=event_data['id']
                )
                
                if self.event_publisher.publish_event(email_event, 'email_dispatched'):
                    self.logger.info(f"EmailDispatched event published: {email_event.id}")
                else:
                    self.logger.error(f"Failed to publish EmailDispatched event for {correlation_id}")
                
                self.metrics['emails_sent'] += 1
                return True
            else:
                self.logger.error(f"Failed to send email for {correlation_id}: {delivery_result.get('error')}")
                self.metrics['emails_failed'] += 1
                return False
                
        except ValidationError as e:
            self.logger.error(f"Event validation failed: {e.messages}")
            self.metrics['events_failed'] += 1
            return False
        except Exception as e:
            self.logger.error(f"Error processing contact form event: {e}", exc_info=True)
            self.metrics['events_failed'] += 1
            return False
    
    def start(self):
        """Start the mailer service."""
        self.logger.info(f"Starting {self.service_name} v{self.service_version}")
        
        try:
            # Initialize Kafka consumer
            self._initialize_consumer()
            
            self.running = True
            self.logger.info(f"Mailer service started, listening to topic: {self.kafka_topic}")
            
            # Main event loop
            for message in self.consumer:
                if not self.running:
                    break
                
                try:
                    event_data = message.value
                    
                    # Check if this is a ContactFormSubmitted event
                    if event_data.get('type') == EventTypes.CONTACT_FORM_SUBMITTED:
                        success = self._process_contact_form_event(transform_event(event_data))
                        if success:
                            self.metrics['events_processed'] += 1
                        else:
                            self.metrics['events_failed'] += 1
                    else:
                        self.logger.debug(f"Ignoring event type: {event_data.get('type')}")
                    
                except Exception as e:
                    self.logger.error(f"Error processing message: {e}", exc_info=True)
                    self.metrics['events_failed'] += 1
                    
        except KeyboardInterrupt:
            self.logger.info("Received interrupt signal, shutting down...")
        except Exception as e:
            self.logger.error(f"Fatal error in mailer service: {e}", exc_info=True)
        finally:
            self.stop()
    
    def stop(self):
        """Stop the mailer service."""
        self.logger.info("Stopping mailer service...")
        self.running = False
        
        if self.consumer:
            self.consumer.close()
        
        if self.event_publisher:
            self.event_publisher.close()
        
        self.logger.info("Mailer service stopped")
    
    def get_health_status(self) -> Dict[str, Any]:
        """Get health status of the service."""
        uptime = time.time() - self.metrics['start_time']
        
        return {
            'status': 'healthy' if self.running else 'stopped',
            'service': self.service_name,
            'version': self.service_version,
            'uptime_seconds': int(uptime),
            'metrics': self.metrics.copy(),
            'kafka': {
                'connected': self.consumer is not None,
                'topic': self.kafka_topic,
                'consumer_group': self.consumer_group
            },
            'smtp': {
                'host': self.smtp_host,
                'port': self.smtp_port,
                'use_tls': self.smtp_use_tls,
                'mailhog_ui': f"http://{self.smtp_host}:8025" if self.smtp_host == 'localhost' and self.smtp_port == 1025 else None
            }
        }


def main():
    """Main entry point for the mailer service."""
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    logger = logging.getLogger(__name__)
    logger.info("Initializing Mailer Service...")
    
    # Create and start service
    service = MailerService()
    
    try:
        service.start()
    except Exception as e:
        logger.error(f"Failed to start mailer service: {e}")
        return 1
    
    return 0


if __name__ == '__main__':
    exit(main())

