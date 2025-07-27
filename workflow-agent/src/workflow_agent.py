"""
Workflow Agent for Event-Driven Architecture PoC
Consumes ContactFormSubmitted events and executes automated business workflows.
"""

import json
import logging
import os
import time
import requests
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional, List
import uuid

from kafka import KafkaConsumer
from kafka.errors import KafkaError
from marshmallow import ValidationError

from event_models import BaseEvent, ContactFormSubmittedSchema, EventTypes, EventSources, transform_event
from event_publisher import EventPublisher
from workflow_engine import WorkflowEngine, WorkflowStep, WorkflowDefinition


class WorkflowAgent:
    """
    Workflow Agent that consumes events and executes automated business processes.
    """
    
    def __init__(self):
        """Initialize the workflow agent."""
        self.logger = logging.getLogger(__name__)
        
        # Kafka configuration
        self.kafka_bootstrap_servers = os.getenv('KAFKA_BOOTSTRAP_SERVERS', 'localhost:9092')
        self.kafka_topic = os.getenv('KAFKA_TOPIC', 'events.contact_form')
        self.consumer_group = os.getenv('KAFKA_CONSUMER_GROUP', 'workflow-agent')
        
        # CRM API configuration
        self.crm_api_base = os.getenv('CRM_API_BASE', 'http://localhost:5000/api')
        self.crm_api_timeout = int(os.getenv('CRM_API_TIMEOUT', '30'))
        
        # Service configuration
        self.service_name = 'workflow-agent'
        self.service_version = '1.0.0'
        
        # Initialize components
        self.consumer = None
        self.event_publisher = EventPublisher()
        self.workflow_engine = WorkflowEngine()
        self.running = False
        
        # Metrics
        self.metrics = {
            'workflows_executed': 0,
            'workflows_failed': 0,
            'events_processed': 0,
            'events_failed': 0,
            'crm_calls_successful': 0,
            'crm_calls_failed': 0,
            'start_time': time.time()
        }
        
        # Initialize workflow definitions
        self._setup_workflows()
    
    def _setup_workflows(self):
        """Set up workflow definitions."""
        # Contact Form Processing Workflow
        contact_workflow_steps = [
            WorkflowStep(
                name="tag_lead",
                order=1,
                handler=self._tag_lead_step,
                description="Analyze form data and assign appropriate tags"
            ),
            WorkflowStep(
                name="assign_responsible",
                order=2,
                handler=self._assign_responsible_step,
                description="Determine and assign responsible team member"
            ),
            WorkflowStep(
                name="schedule_followup",
                order=3,
                handler=self._schedule_followup_step,
                description="Schedule follow-up activities and calendar events"
            )
        ]
        
        contact_workflow = WorkflowDefinition(
            id="contact_form_processing",
            name="Contact Form Processing Workflow",
            version="1.0.0",
            description="Automated workflow for processing contact form submissions",
            steps=contact_workflow_steps,
            timeout_minutes=10
        )
        
        self.workflow_engine.register_workflow(contact_workflow)
        self.logger.info("Workflow definitions initialized")
    
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
            'max_poll_records': 5,
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
    
    def _tag_lead_step(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Step 1: Analyze form data and assign appropriate tags.
        
        Args:
            context: Workflow execution context
            
        Returns:
            Dict containing step output
        """
        form_data = context['form_data']
        
        tags = []
        
        # Source tag
        tags.append('web_lead')
        
        # Company size analysis
        company = form_data.get('company', '').lower()
        if any(keyword in company for keyword in ['enterprise', 'corporation', 'corp', 'inc', 'ltd']):
            tags.append('enterprise_interest')
        elif any(keyword in company for keyword in ['startup', 'tech', 'software']):
            tags.append('startup_interest')
        else:
            tags.append('sme_interest')
        
        # Message analysis for priority
        message = form_data.get('message', '').lower()
        if any(keyword in message for keyword in ['urgent', 'asap', 'immediately', 'critical']):
            tags.append('high_priority')
        elif any(keyword in message for keyword in ['enterprise', 'large scale', 'production', 'mission critical']):
            tags.append('high_priority')
        else:
            tags.append('standard_priority')
        
        # Interest area analysis
        if any(keyword in message for keyword in ['event', 'kafka', 'microservice', 'architecture']):
            tags.append('architecture_interest')
        if any(keyword in message for keyword in ['scale', 'performance', 'throughput']):
            tags.append('scalability_interest')
        if any(keyword in message for keyword in ['integration', 'api', 'connect']):
            tags.append('integration_interest')
        
        self.logger.info(f"Assigned tags: {tags}")
        
        return {
            'tags_assigned': tags,
            'analysis_completed': True,
            'priority_level': 'high' if 'high_priority' in tags else 'standard'
        }
    
    def _assign_responsible_step(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Step 2: Determine and assign responsible team member.
        
        Args:
            context: Workflow execution context
            
        Returns:
            Dict containing step output
        """
        form_data = context['form_data']
        previous_output = context.get('previous_step_outputs', {}).get('tag_lead', {})
        tags = previous_output.get('tags_assigned', [])
        
        # Assignment logic based on tags and company info
        if 'enterprise_interest' in tags:
            assigned_to = 'sales_team_enterprise'
            assignment_reason = 'enterprise_company_detected'
        elif 'startup_interest' in tags:
            assigned_to = 'sales_team_startup'
            assignment_reason = 'startup_company_detected'
        elif 'architecture_interest' in tags:
            assigned_to = 'technical_team_architecture'
            assignment_reason = 'technical_architecture_inquiry'
        elif 'integration_interest' in tags:
            assigned_to = 'technical_team_integration'
            assignment_reason = 'integration_specific_inquiry'
        else:
            assigned_to = 'sales_team_general'
            assignment_reason = 'general_inquiry'
        
        # Priority-based escalation
        if 'high_priority' in tags:
            if 'enterprise' in assigned_to:
                assigned_to = 'sales_director_enterprise'
            else:
                assigned_to = f"{assigned_to}_priority"
        
        self.logger.info(f"Assigned to: {assigned_to} (reason: {assignment_reason})")
        
        return {
            'assigned_to': assigned_to,
            'assignment_reason': assignment_reason,
            'escalated': 'high_priority' in tags
        }
    
    def _schedule_followup_step(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Step 3: Schedule follow-up activities and calendar events.
        
        Args:
            context: Workflow execution context
            
        Returns:
            Dict containing step output
        """
        form_data = context['form_data']
        previous_outputs = context.get('previous_step_outputs', {})
        tags = previous_outputs.get('tag_lead', {}).get('tags_assigned', [])
        assigned_to = previous_outputs.get('assign_responsible', {}).get('assigned_to', 'sales_team_general')
        
        # Determine follow-up timing based on priority
        if 'high_priority' in tags:
            followup_hours = 4  # 4 hours for high priority
            followup_type = 'phone_call'
        elif 'enterprise_interest' in tags:
            followup_hours = 24  # 1 day for enterprise
            followup_type = 'phone_call'
        else:
            followup_hours = 48  # 2 days for standard
            followup_type = 'email'
        
        # Calculate follow-up time
        followup_time = datetime.now(timezone.utc) + timedelta(hours=followup_hours)
        
        # Generate calendar event ID (mock)
        calendar_event_id = f"cal_{str(uuid.uuid4())}"
        
        # Determine preferred contact method
        preferred_method = form_data.get('preferred_contact_method', 'email')
        if preferred_method == 'phone' and form_data.get('phone'):
            followup_type = 'phone_call'
        elif preferred_method == 'both':
            followup_type = 'phone_call'  # Prefer phone for 'both'
        
        self.logger.info(f"Scheduled {followup_type} follow-up for {followup_time.isoformat()}")
        
        return {
            'followup_scheduled_at': followup_time.isoformat(),
            'followup_type': followup_type,
            'calendar_event_id': calendar_event_id,
            'assigned_to': assigned_to,
            'priority_level': 'high' if 'high_priority' in tags else 'standard'
        }
    
    def _create_crm_lead(self, form_data: Dict[str, Any], workflow_output: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Create a lead in the CRM system.
        
        Args:
            form_data: Original form submission data
            workflow_output: Output from workflow execution
            
        Returns:
            Dict containing CRM response or None if failed
        """
        start_time = time.time()
        
        try:
            # Extract workflow results
            tag_output = workflow_output.get('steps', {}).get('tag_lead', {}).get('output', {})
            assign_output = workflow_output.get('steps', {}).get('assign_responsible', {}).get('output', {})
            
            # Prepare CRM lead data
            lead_data = {
                'name': form_data['name'],
                'email': form_data['email'],
                'company': form_data['company'],
                'phone': form_data.get('phone'),
                'message': form_data['message'],
                'source': 'web',
                'priority': 'medium',
                'tags': tag_output.get('tags_assigned', []),
                'assigned_to': assign_output.get('assigned_to')
            }
            
            # Make API call to CRM
            response = requests.post(
                f"{self.crm_api_base}/internal/leads",
                json=lead_data,
                headers={'Content-Type': 'application/json'},
                timeout=self.crm_api_timeout
            )
            
            response_time_ms = int((time.time() - start_time) * 1000)
            
            if response.status_code == 201:
                crm_data = response.json()
                self.metrics['crm_calls_successful'] += 1
                
                self.logger.info(f"CRM lead created successfully: {crm_data.get('id')}")
                
                return {
                    'lead_id': crm_data.get('id'),
                    'lead_status': crm_data.get('status', 'NUEVO'),
                    'crm_response_time_ms': response_time_ms,
                    'data_synchronized': True
                }
            else:
                self.logger.error(f"CRM API error: {response.status_code} - {response.text}")
                self.metrics['crm_calls_failed'] += 1
                return None
                
        except requests.exceptions.Timeout:
            self.logger.error(f"CRM API timeout after {self.crm_api_timeout}s")
            self.metrics['crm_calls_failed'] += 1
            return None
        except requests.exceptions.RequestException as e:
            self.logger.error(f"CRM API request failed: {e}")
            self.metrics['crm_calls_failed'] += 1
            return None
        except Exception as e:
            self.logger.error(f"Unexpected error creating CRM lead: {e}")
            self.metrics['crm_calls_failed'] += 1
            return None
    
    def _process_contact_form_event(self, event_data: Dict[str, Any]) -> bool:
        """
        Process a ContactFormSubmitted event.
        
        Args:
            event_data: The event data
            
        Returns:
            bool: True if processed successfully, False otherwise
        """
        try:
            self.logger.info(f"Processing event: {event_data}")
            # Validate event structure
            schema = ContactFormSubmittedSchema()
            
            validated_event = schema.load(event_data)
            
            # Extract form data
            form_data = event_data['data']['form_data']
            correlation_id = event_data['correlation_id']
            
            self.logger.info(f"Processing contact form workflow: {correlation_id}")
            
            # Execute workflow
            workflow_context = {
                'form_data': form_data,
                'event_id': event_data['id'],
                'correlation_id': correlation_id,
                'source_event': event_data
            }
            
            workflow_result = self.workflow_engine.execute_workflow(
                workflow_id="contact_form_processing",
                context=workflow_context
            )
            
            if workflow_result['status'] == 'completed':
                # Create lead in CRM
                crm_result = self._create_crm_lead(form_data, workflow_result)
                
                if crm_result:
                    # Publish WorkflowCompleted event
                    workflow_completed_data = {
                        'workflow': {
                            'workflow_id': workflow_result['workflow_id'],
                            'workflow_version': workflow_result['workflow_version'],
                            'execution_id': workflow_result['execution_id'],
                            'started_at': workflow_result['started_at'],
                            'completed_at': workflow_result['completed_at'],
                            'total_duration_ms': workflow_result['total_duration_ms'],
                            'status': workflow_result['status']
                        },
                        'steps': [
                            {
                                'step_name': step_name,
                                'step_order': step_data['order'],
                                'started_at': step_data['started_at'],
                                'completed_at': step_data['completed_at'],
                                'duration_ms': step_data['duration_ms'],
                                'status': step_data['status'],
                                'output': step_data['output']
                            }
                            for step_name, step_data in workflow_result['steps'].items()
                        ],
                        'crm_integration': crm_result
                    }
                    
                    workflow_event = BaseEvent.create(
                        event_type=EventTypes.WORKFLOW_COMPLETED,
                        source=EventSources.WORKFLOW_AGENT,
                        data=workflow_completed_data,
                        correlation_id=correlation_id,
                        causation_id=event_data['id']
                    )
                    
                    if self.event_publisher.publish_event(workflow_event, 'workflow_completed'):
                        self.logger.info(f"WorkflowCompleted event published: {workflow_event.id}")
                    else:
                        self.logger.error(f"Failed to publish WorkflowCompleted event for {correlation_id}")
                    
                    self.metrics['workflows_executed'] += 1
                    return True
                else:
                    self.logger.error(f"Failed to create CRM lead for {correlation_id}")
                    self.metrics['workflows_failed'] += 1
                    return False
            else:
                self.logger.error(f"Workflow execution failed for {correlation_id}: {workflow_result.get('error')}")
                self.metrics['workflows_failed'] += 1
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
        """Start the workflow agent."""
        self.logger.info(f"Starting {self.service_name} v{self.service_version}")
        
        try:
            # Initialize Kafka consumer
            self._initialize_consumer()
            
            self.running = True
            self.logger.info(f"Workflow agent started, listening to topic: {self.kafka_topic}")
            
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
            self.logger.error(f"Fatal error in workflow agent: {e}", exc_info=True)
        finally:
            self.stop()
    
    def stop(self):
        """Stop the workflow agent."""
        self.logger.info("Stopping workflow agent...")
        self.running = False
        
        if self.consumer:
            self.consumer.close()
        
        if self.event_publisher:
            self.event_publisher.close()
        
        self.logger.info("Workflow agent stopped")
    
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
            'crm_api': {
                'base_url': self.crm_api_base,
                'timeout': self.crm_api_timeout
            },
            'workflows': {
                'registered': len(self.workflow_engine.workflows),
                'available': list(self.workflow_engine.workflows.keys())
            }
        }


def main():
    """Main entry point for the workflow agent."""
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    logger = logging.getLogger(__name__)
    logger.info("Initializing Workflow Agent...")
    
    # Create and start service
    agent = WorkflowAgent()
    
    try:
        agent.start()
    except Exception as e:
        logger.error(f"Failed to start workflow agent: {e}")
        return 1
    
    return 0


if __name__ == '__main__':
    exit(main())

