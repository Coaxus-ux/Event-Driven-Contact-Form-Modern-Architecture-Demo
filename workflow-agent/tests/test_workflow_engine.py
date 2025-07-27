"""
Unit tests for workflow engine in the Workflow Agent.
"""

import pytest
from unittest.mock import Mock, patch
from datetime import datetime, timezone

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from workflow_engine import WorkflowEngine, WorkflowDefinition, WorkflowStep, WorkflowExecution


class TestWorkflowEngine:
    """Test workflow engine functionality."""
    
    @pytest.fixture
    def sample_workflow_steps(self):
        """Create sample workflow steps."""
        def step1_handler(context):
            return {'step1_result': 'success', 'data': context.get('input_data', 'default')}
        
        def step2_handler(context):
            previous_output = context.get('previous_step_outputs', {}).get('step1', {})
            return {'step2_result': 'success', 'previous_data': previous_output.get('data')}
        
        def step3_handler(context):
            return {'step3_result': 'success', 'final': True}
        
        return [
            WorkflowStep(
                name="step1",
                order=1,
                handler=step1_handler,
                description="First step"
            ),
            WorkflowStep(
                name="step2",
                order=2,
                handler=step2_handler,
                description="Second step"
            ),
            WorkflowStep(
                name="step3",
                order=3,
                handler=step3_handler,
                description="Third step"
            )
        ]
    
    @pytest.fixture
    def sample_workflow(self, sample_workflow_steps):
        """Create sample workflow definition."""
        return WorkflowDefinition(
            id="test_workflow",
            name="Test Workflow",
            version="1.0.0",
            description="A test workflow",
            steps=sample_workflow_steps,
            timeout_minutes=5
        )
    
    def test_workflow_engine_initialization(self):
        """Test workflow engine initialization."""
        engine = WorkflowEngine()
        
        assert engine.workflows == {}
        assert engine.active_executions == {}
        assert 'workflows_started' in engine.metrics
        assert 'workflows_completed' in engine.metrics
        assert 'workflows_failed' in engine.metrics
    
    def test_register_workflow(self, sample_workflow):
        """Test workflow registration."""
        engine = WorkflowEngine()
        
        engine.register_workflow(sample_workflow)
        
        assert 'test_workflow' in engine.workflows
        assert engine.workflows['test_workflow'] == sample_workflow
    
    def test_workflow_steps_sorted_by_order(self):
        """Test that workflow steps are sorted by order."""
        # Create steps in wrong order
        steps = [
            WorkflowStep("step3", 3, lambda x: {}, "Third"),
            WorkflowStep("step1", 1, lambda x: {}, "First"),
            WorkflowStep("step2", 2, lambda x: {}, "Second")
        ]
        
        workflow = WorkflowDefinition(
            id="test",
            name="Test",
            version="1.0",
            description="Test",
            steps=steps
        )
        
        # Steps should be sorted by order
        assert workflow.steps[0].name == "step1"
        assert workflow.steps[1].name == "step2"
        assert workflow.steps[2].name == "step3"
    
    def test_execute_workflow_success(self, sample_workflow):
        """Test successful workflow execution."""
        engine = WorkflowEngine()
        engine.register_workflow(sample_workflow)
        
        context = {'input_data': 'test_input'}
        
        result = engine.execute_workflow('test_workflow', context)
        
        assert result['status'] == 'completed'
        assert result['workflow_id'] == 'test_workflow'
        assert result['workflow_version'] == '1.0.0'
        assert 'execution_id' in result
        assert 'started_at' in result
        assert 'completed_at' in result
        assert 'total_duration_ms' in result
        
        # Check steps execution
        assert len(result['steps']) == 3
        assert 'step1' in result['steps']
        assert 'step2' in result['steps']
        assert 'step3' in result['steps']
        
        # Verify step outputs
        assert result['steps']['step1']['status'] == 'completed'
        assert result['steps']['step1']['output']['step1_result'] == 'success'
        assert result['steps']['step2']['output']['previous_data'] == 'test_input'
        
        # Check metrics
        assert engine.metrics['workflows_completed'] == 1
        assert engine.metrics['workflows_started'] == 1
        assert engine.metrics['steps_executed'] == 3
    
    def test_execute_workflow_not_found(self):
        """Test executing non-existent workflow."""
        engine = WorkflowEngine()
        
        with pytest.raises(ValueError, match="Workflow not found"):
            engine.execute_workflow('nonexistent', {})
    
    def test_execute_workflow_step_failure(self):
        """Test workflow execution with step failure."""
        def failing_step(context):
            raise Exception("Step failed")
        
        def success_step(context):
            return {'result': 'success'}
        
        steps = [
            WorkflowStep("step1", 1, success_step, "Success step"),
            WorkflowStep("step2", 2, failing_step, "Failing step"),
            WorkflowStep("step3", 3, success_step, "Should not execute")
        ]
        
        workflow = WorkflowDefinition(
            id="failing_workflow",
            name="Failing Workflow",
            version="1.0.0",
            description="A workflow that fails",
            steps=steps
        )
        
        engine = WorkflowEngine()
        engine.register_workflow(workflow)
        
        result = engine.execute_workflow('failing_workflow', {})
        
        assert result['status'] == 'failed'
        assert 'error' in result
        assert 'Step failed' in result['error']
        
        # Only first step should have completed
        assert result['steps']['step1']['status'] == 'completed'
        assert result['steps']['step2']['status'] == 'failed'
        assert 'step3' not in result['steps']
        
        # Check metrics
        assert engine.metrics['workflows_failed'] == 1
        assert engine.metrics['steps_executed'] == 1
        assert engine.metrics['steps_failed'] == 1
    
    def test_execute_workflow_with_retry(self):
        """Test workflow step execution with retry logic."""
        call_count = 0
        
        def flaky_step(context):
            nonlocal call_count
            call_count += 1
            if call_count < 3:  # Fail first 2 attempts
                raise Exception(f"Attempt {call_count} failed")
            return {'result': 'success_after_retry'}
        
        steps = [
            WorkflowStep("flaky_step", 1, flaky_step, "Flaky step", retry_count=3)
        ]
        
        workflow = WorkflowDefinition(
            id="retry_workflow",
            name="Retry Workflow",
            version="1.0.0",
            description="A workflow with retries",
            steps=steps
        )
        
        engine = WorkflowEngine()
        engine.register_workflow(workflow)
        
        result = engine.execute_workflow('retry_workflow', {})
        
        assert result['status'] == 'completed'
        assert result['steps']['flaky_step']['status'] == 'completed'
        assert result['steps']['flaky_step']['retry_attempts'] == 3
        assert result['steps']['flaky_step']['output']['result'] == 'success_after_retry'
    
    def test_execute_workflow_with_compensation(self):
        """Test workflow execution with compensation logic."""
        compensation_calls = []
        
        def step1_handler(context):
            return {'step1_data': 'created'}
        
        def step1_compensation(context):
            compensation_calls.append('step1_compensated')
            return {'compensation': 'step1_cleaned_up'}
        
        def step2_handler(context):
            return {'step2_data': 'created'}
        
        def step2_compensation(context):
            compensation_calls.append('step2_compensated')
            return {'compensation': 'step2_cleaned_up'}
        
        def failing_step(context):
            raise Exception("Step 3 failed")
        
        steps = [
            WorkflowStep("step1", 1, step1_handler, "Step 1", compensation_handler=step1_compensation),
            WorkflowStep("step2", 2, step2_handler, "Step 2", compensation_handler=step2_compensation),
            WorkflowStep("step3", 3, failing_step, "Failing step")
        ]
        
        workflow = WorkflowDefinition(
            id="compensation_workflow",
            name="Compensation Workflow",
            version="1.0.0",
            description="A workflow with compensation",
            steps=steps
        )
        
        engine = WorkflowEngine()
        engine.register_workflow(workflow)
        
        result = engine.execute_workflow('compensation_workflow', {})
        
        assert result['status'] == 'failed'
        assert 'compensation' in result
        assert result['compensation']['compensation_needed'] is True
        assert result['compensation']['compensation_completed'] is True
        
        # Compensation should be called in reverse order
        assert compensation_calls == ['step2_compensated', 'step1_compensated']
        
        # Check compensation results
        compensation_steps = result['compensation']['compensation_steps']
        assert len(compensation_steps) == 2
        assert compensation_steps[0]['step_name'] == 'step2'
        assert compensation_steps[0]['status'] == 'compensated'
        assert compensation_steps[1]['step_name'] == 'step1'
        assert compensation_steps[1]['status'] == 'compensated'
    
    def test_get_workflow_status(self, sample_workflow):
        """Test getting workflow execution status."""
        engine = WorkflowEngine()
        engine.register_workflow(sample_workflow)
        
        # Mock active execution
        execution = WorkflowExecution(
            execution_id="test-execution",
            workflow_id="test_workflow",
            workflow_version="1.0.0",
            started_at=datetime.now(timezone.utc).isoformat(),
            context={}
        )
        execution.current_step = 1
        execution.steps = {
            'step1': {'status': 'completed'}
        }
        
        engine.active_executions["test-execution"] = execution
        
        status = engine.get_workflow_status("test-execution")
        
        assert status['execution_id'] == "test-execution"
        assert status['workflow_id'] == "test_workflow"
        assert status['status'] == 'running'
        assert status['current_step'] == 1
        assert status['steps_completed'] == 1
        assert status['total_steps'] == 3
    
    def test_get_workflow_status_not_found(self):
        """Test getting status for non-existent execution."""
        engine = WorkflowEngine()
        
        status = engine.get_workflow_status("nonexistent")
        
        assert status is None
    
    def test_list_workflows(self, sample_workflow):
        """Test listing registered workflows."""
        engine = WorkflowEngine()
        engine.register_workflow(sample_workflow)
        
        workflows = engine.list_workflows()
        
        assert len(workflows) == 1
        assert workflows[0]['id'] == 'test_workflow'
        assert workflows[0]['name'] == 'Test Workflow'
        assert workflows[0]['version'] == '1.0.0'
        assert workflows[0]['steps_count'] == 3
        assert workflows[0]['timeout_minutes'] == 5
    
    def test_get_metrics(self, sample_workflow):
        """Test getting workflow engine metrics."""
        engine = WorkflowEngine()
        engine.register_workflow(sample_workflow)
        
        # Execute a workflow to generate metrics
        engine.execute_workflow('test_workflow', {})
        
        metrics = engine.get_metrics()
        
        assert metrics['registered_workflows'] == 1
        assert metrics['active_executions'] == 0  # Should be cleaned up after completion
        assert 'execution_metrics' in metrics
        assert metrics['execution_metrics']['workflows_completed'] == 1
        assert metrics['execution_metrics']['steps_executed'] == 3


class TestWorkflowStepExecution:
    """Test individual workflow step execution."""
    
    def test_step_execution_context(self):
        """Test that step receives proper context."""
        received_context = {}
        
        def test_step(context):
            received_context.update(context)
            return {'result': 'success'}
        
        steps = [WorkflowStep("test_step", 1, test_step, "Test step")]
        workflow = WorkflowDefinition("test", "Test", "1.0", "Test", steps)
        
        engine = WorkflowEngine()
        engine.register_workflow(workflow)
        
        input_context = {'input_data': 'test_value'}
        engine.execute_workflow('test', input_context)
        
        assert 'execution_id' in received_context
        assert 'step_name' in received_context
        assert 'previous_step_outputs' in received_context
        assert received_context['input_data'] == 'test_value'
    
    def test_step_execution_timing(self):
        """Test that step execution timing is recorded."""
        def slow_step(context):
            import time
            time.sleep(0.1)  # 100ms delay
            return {'result': 'success'}
        
        steps = [WorkflowStep("slow_step", 1, slow_step, "Slow step")]
        workflow = WorkflowDefinition("test", "Test", "1.0", "Test", steps)
        
        engine = WorkflowEngine()
        engine.register_workflow(workflow)
        
        result = engine.execute_workflow('test', {})
        
        step_data = result['steps']['slow_step']
        assert 'started_at' in step_data
        assert 'completed_at' in step_data
        assert 'duration_ms' in step_data
        assert step_data['duration_ms'] >= 100  # Should be at least 100ms


class TestWorkflowErrorHandling:
    """Test workflow error handling scenarios."""
    
    def test_workflow_execution_exception(self):
        """Test handling of unexpected exceptions during workflow execution."""
        def exception_step(context):
            raise RuntimeError("Unexpected error")
        
        steps = [WorkflowStep("exception_step", 1, exception_step, "Exception step")]
        workflow = WorkflowDefinition("test", "Test", "1.0", "Test", steps)
        
        engine = WorkflowEngine()
        engine.register_workflow(workflow)
        
        result = engine.execute_workflow('test', {})
        
        assert result['status'] == 'failed'
        assert 'Unexpected error' in result['error']
    
    def test_compensation_handler_exception(self):
        """Test handling of exceptions in compensation handlers."""
        def success_step(context):
            return {'result': 'success'}
        
        def failing_compensation(context):
            raise Exception("Compensation failed")
        
        def failing_step(context):
            raise Exception("Step failed")
        
        steps = [
            WorkflowStep("step1", 1, success_step, "Step 1", compensation_handler=failing_compensation),
            WorkflowStep("step2", 2, failing_step, "Failing step")
        ]
        
        workflow = WorkflowDefinition("test", "Test", "1.0", "Test", steps)
        
        engine = WorkflowEngine()
        engine.register_workflow(workflow)
        
        result = engine.execute_workflow('test', {})
        
        assert result['status'] == 'failed'
        assert 'compensation' in result
        
        compensation_steps = result['compensation']['compensation_steps']
        assert len(compensation_steps) == 1
        assert compensation_steps[0]['status'] == 'compensation_failed'
        assert 'Compensation failed' in compensation_steps[0]['error']

