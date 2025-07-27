"""
Workflow Engine for the Workflow Agent.
Executes multi-step business processes with compensation logic.
"""

import logging
import time
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass, asdict
import uuid


@dataclass
class WorkflowStep:
    """Definition of a single workflow step."""
    name: str
    order: int
    handler: Callable[[Dict[str, Any]], Dict[str, Any]]
    description: str
    timeout_seconds: int = 60
    retry_count: int = 3
    compensation_handler: Optional[Callable[[Dict[str, Any]], Dict[str, Any]]] = None


@dataclass
class WorkflowDefinition:
    """Definition of a complete workflow."""
    id: str
    name: str
    version: str
    description: str
    steps: List[WorkflowStep]
    timeout_minutes: int = 30
    
    def __post_init__(self):
        """Sort steps by order after initialization."""
        self.steps.sort(key=lambda x: x.order)


@dataclass
class WorkflowExecution:
    """Runtime execution state of a workflow."""
    execution_id: str
    workflow_id: str
    workflow_version: str
    started_at: str
    context: Dict[str, Any]
    status: str = 'running'  # running, completed, failed, compensating
    current_step: int = 0
    completed_at: Optional[str] = None
    error: Optional[str] = None
    steps: Dict[str, Dict[str, Any]] = None
    
    def __post_init__(self):
        if self.steps is None:
            self.steps = {}


class WorkflowEngine:
    """
    Engine for executing multi-step workflows with compensation logic.
    """
    
    def __init__(self):
        """Initialize the workflow engine."""
        self.logger = logging.getLogger(__name__)
        self.workflows: Dict[str, WorkflowDefinition] = {}
        self.active_executions: Dict[str, WorkflowExecution] = {}
        
        # Metrics
        self.metrics = {
            'workflows_started': 0,
            'workflows_completed': 0,
            'workflows_failed': 0,
            'workflows_compensated': 0,
            'steps_executed': 0,
            'steps_failed': 0,
            'steps_compensated': 0
        }
    
    def register_workflow(self, workflow: WorkflowDefinition):
        """
        Register a workflow definition.
        
        Args:
            workflow: The workflow definition to register
        """
        self.workflows[workflow.id] = workflow
        self.logger.info(f"Registered workflow: {workflow.id} v{workflow.version} ({len(workflow.steps)} steps)")
    
    def execute_workflow(self, workflow_id: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute a workflow with the given context.
        
        Args:
            workflow_id: ID of the workflow to execute
            context: Execution context data
            
        Returns:
            Dict containing execution results
        """
        if workflow_id not in self.workflows:
            raise ValueError(f"Workflow not found: {workflow_id}")
        
        workflow = self.workflows[workflow_id]
        execution_id = str(uuid.uuid4())
        
        # Create execution state
        execution = WorkflowExecution(
            execution_id=execution_id,
            workflow_id=workflow_id,
            workflow_version=workflow.version,
            started_at=datetime.now(timezone.utc).isoformat(),
            context=context.copy()
        )
        
        self.active_executions[execution_id] = execution
        self.metrics['workflows_started'] += 1
        
        self.logger.info(f"Starting workflow execution: {workflow_id} ({execution_id})")
        
        try:
            # Execute each step in order
            for step in workflow.steps:
                step_result = self._execute_step(execution, step)
                
                if not step_result['success']:
                    # Step failed, initiate compensation
                    execution.status = 'failed'
                    execution.error = step_result.get('error', 'Step execution failed')
                    
                    self.logger.error(f"Step {step.name} failed in execution {execution_id}: {execution.error}")
                    
                    # Run compensation logic
                    compensation_result = self._compensate_workflow(execution)
                    
                    execution.completed_at = datetime.now(timezone.utc).isoformat()
                    self.metrics['workflows_failed'] += 1
                    
                    return self._build_execution_result(execution, compensation_result)
                
                execution.current_step += 1
            
            # All steps completed successfully
            execution.status = 'completed'
            execution.completed_at = datetime.now(timezone.utc).isoformat()
            self.metrics['workflows_completed'] += 1
            
            self.logger.info(f"Workflow execution completed successfully: {execution_id}")
            
            return self._build_execution_result(execution)
            
        except Exception as e:
            execution.status = 'failed'
            execution.error = str(e)
            execution.completed_at = datetime.now(timezone.utc).isoformat()
            
            self.logger.error(f"Workflow execution failed with exception: {execution_id} - {e}", exc_info=True)
            
            # Run compensation logic
            compensation_result = self._compensate_workflow(execution)
            
            self.metrics['workflows_failed'] += 1
            
            return self._build_execution_result(execution, compensation_result)
        
        finally:
            # Clean up active execution
            if execution_id in self.active_executions:
                del self.active_executions[execution_id]
    
    def _execute_step(self, execution: WorkflowExecution, step: WorkflowStep) -> Dict[str, Any]:
        """
        Execute a single workflow step.
        
        Args:
            execution: Current workflow execution
            step: Step to execute
            
        Returns:
            Dict containing step execution results
        """
        step_start_time = time.time()
        
        self.logger.info(f"Executing step: {step.name} (order {step.order}) in execution {execution.execution_id}")
        
        # Initialize step execution state
        step_execution = {
            'order': step.order,
            'started_at': datetime.now(timezone.utc).isoformat(),
            'status': 'running',
            'output': None,
            'error': None,
            'duration_ms': 0,
            'retry_attempts': 0
        }
        
        execution.steps[step.name] = step_execution
        
        # Prepare step context
        step_context = execution.context.copy()
        step_context['execution_id'] = execution.execution_id
        step_context['step_name'] = step.name
        step_context['previous_step_outputs'] = {
            name: data.get('output', {})
            for name, data in execution.steps.items()
            if data.get('status') == 'completed'
        }
        
        # Execute step with retry logic
        for attempt in range(step.retry_count):
            try:
                step_execution['retry_attempts'] = attempt + 1
                
                # Call step handler
                step_output = step.handler(step_context)
                
                # Step completed successfully
                step_execution['status'] = 'completed'
                step_execution['output'] = step_output
                step_execution['completed_at'] = datetime.now(timezone.utc).isoformat()
                step_execution['duration_ms'] = int((time.time() - step_start_time) * 1000)
                
                self.metrics['steps_executed'] += 1
                
                self.logger.info(f"Step {step.name} completed successfully (attempt {attempt + 1})")
                
                return {'success': True, 'output': step_output}
                
            except Exception as e:
                step_error = str(e)
                self.logger.warning(f"Step {step.name} failed on attempt {attempt + 1}: {step_error}")
                
                if attempt < step.retry_count - 1:
                    # Wait before retry (exponential backoff)
                    retry_delay = 2 ** attempt
                    time.sleep(retry_delay)
                else:
                    # Final attempt failed
                    step_execution['status'] = 'failed'
                    step_execution['error'] = step_error
                    step_execution['completed_at'] = datetime.now(timezone.utc).isoformat()
                    step_execution['duration_ms'] = int((time.time() - step_start_time) * 1000)
                    
                    self.metrics['steps_failed'] += 1
                    
                    return {'success': False, 'error': step_error}
        
        # Should not reach here
        return {'success': False, 'error': 'Unknown step execution error'}
    
    def _compensate_workflow(self, execution: WorkflowExecution) -> Dict[str, Any]:
        """
        Run compensation logic for failed workflow.
        
        Args:
            execution: Failed workflow execution
            
        Returns:
            Dict containing compensation results
        """
        if execution.status != 'failed':
            return {'compensation_needed': False}
        
        execution.status = 'compensating'
        self.logger.info(f"Starting compensation for execution: {execution.execution_id}")
        
        compensation_results = []
        workflow = self.workflows[execution.workflow_id]
        
        # Run compensation handlers in reverse order for completed steps
        completed_steps = [
            (step, execution.steps.get(step.name, {}))
            for step in reversed(workflow.steps)
            if execution.steps.get(step.name, {}).get('status') == 'completed'
        ]
        
        for step, step_data in completed_steps:
            if step.compensation_handler:
                try:
                    self.logger.info(f"Running compensation for step: {step.name}")
                    
                    compensation_context = execution.context.copy()
                    compensation_context['step_output'] = step_data.get('output', {})
                    compensation_context['execution_id'] = execution.execution_id
                    
                    compensation_output = step.compensation_handler(compensation_context)
                    
                    compensation_results.append({
                        'step_name': step.name,
                        'status': 'compensated',
                        'output': compensation_output
                    })
                    
                    self.metrics['steps_compensated'] += 1
                    
                except Exception as e:
                    self.logger.error(f"Compensation failed for step {step.name}: {e}")
                    compensation_results.append({
                        'step_name': step.name,
                        'status': 'compensation_failed',
                        'error': str(e)
                    })
            else:
                compensation_results.append({
                    'step_name': step.name,
                    'status': 'no_compensation_handler'
                })
        
        self.metrics['workflows_compensated'] += 1
        
        return {
            'compensation_needed': True,
            'compensation_steps': compensation_results,
            'compensation_completed': True
        }
    
    def _build_execution_result(self, execution: WorkflowExecution, 
                              compensation_result: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Build the final execution result.
        
        Args:
            execution: Workflow execution
            compensation_result: Optional compensation results
            
        Returns:
            Dict containing complete execution results
        """
        start_time = datetime.fromisoformat(execution.started_at.replace('Z', '+00:00'))
        end_time = datetime.fromisoformat(execution.completed_at.replace('Z', '+00:00'))
        total_duration = int((end_time - start_time).total_seconds() * 1000)
        
        result = {
            'execution_id': execution.execution_id,
            'workflow_id': execution.workflow_id,
            'workflow_version': execution.workflow_version,
            'started_at': execution.started_at,
            'completed_at': execution.completed_at,
            'total_duration_ms': total_duration,
            'status': execution.status,
            'steps': execution.steps.copy(),
            'context': execution.context.copy()
        }
        
        if execution.error:
            result['error'] = execution.error
        
        if compensation_result:
            result['compensation'] = compensation_result
        
        return result
    
    def get_workflow_status(self, execution_id: str) -> Optional[Dict[str, Any]]:
        """
        Get the status of a workflow execution.
        
        Args:
            execution_id: ID of the execution to check
            
        Returns:
            Dict containing execution status or None if not found
        """
        if execution_id not in self.active_executions:
            return None
        
        execution = self.active_executions[execution_id]
        
        return {
            'execution_id': execution_id,
            'workflow_id': execution.workflow_id,
            'status': execution.status,
            'current_step': execution.current_step,
            'started_at': execution.started_at,
            'steps_completed': len([s for s in execution.steps.values() if s.get('status') == 'completed']),
            'total_steps': len(self.workflows[execution.workflow_id].steps)
        }
    
    def list_workflows(self) -> List[Dict[str, Any]]:
        """
        List all registered workflows.
        
        Returns:
            List of workflow definitions
        """
        return [
            {
                'id': workflow.id,
                'name': workflow.name,
                'version': workflow.version,
                'description': workflow.description,
                'steps_count': len(workflow.steps),
                'timeout_minutes': workflow.timeout_minutes
            }
            for workflow in self.workflows.values()
        ]
    
    def get_metrics(self) -> Dict[str, Any]:
        """
        Get workflow engine metrics.
        
        Returns:
            Dict containing metrics
        """
        return {
            'registered_workflows': len(self.workflows),
            'active_executions': len(self.active_executions),
            'execution_metrics': self.metrics.copy()
        }

