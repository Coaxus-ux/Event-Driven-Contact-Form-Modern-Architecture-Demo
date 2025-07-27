"""
Unit tests for template engine in the Mailer service.
"""

import pytest
import tempfile
import os
from pathlib import Path
from unittest.mock import Mock, patch

import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from template_engine import TemplateEngine


class TestTemplateEngine:
    """Test template engine functionality."""
    
    @pytest.fixture
    def temp_templates_dir(self):
        """Create temporary templates directory."""
        with tempfile.TemporaryDirectory() as temp_dir:
            templates_dir = Path(temp_dir)
            
            # Create sample templates
            html_template = templates_dir / 'test_html.mustache'
            html_template.write_text("""
<html>
<body>
    <h1>Hello {{name}}!</h1>
    <p>Your email is {{email}}</p>
    <p>Company: {{company}}</p>
</body>
</html>
""")
            
            text_template = templates_dir / 'test_text.mustache'
            text_template.write_text("""
Hello {{name}}!

Your email is {{email}}
Company: {{company}}

Best regards,
The Team
""")
            
            yield str(templates_dir)
    
    def test_template_engine_initialization(self, temp_templates_dir):
        """Test template engine initialization."""
        engine = TemplateEngine(temp_templates_dir)
        
        assert engine.templates_dir == Path(temp_templates_dir)
        assert engine.renderer is not None
        assert engine._template_cache == {}
    
    def test_template_engine_default_directory(self):
        """Test template engine with default directory."""
        engine = TemplateEngine()
        
        # Should create templates directory relative to the engine file
        expected_dir = Path(__file__).parent.parent / 'templates'
        assert engine.templates_dir.name == 'templates'
    
    def test_render_html_template_success(self, temp_templates_dir):
        """Test successful HTML template rendering."""
        engine = TemplateEngine(temp_templates_dir)
        
        template_data = {
            'name': 'John Doe',
            'email': 'john@example.com',
            'company': 'Acme Corp'
        }
        
        result = engine.render_html_template('test', template_data)
        
        assert 'Hello John Doe!' in result
        assert 'john@example.com' in result
        assert 'Acme Corp' in result
        assert '<html>' in result
        assert '<body>' in result
    
    def test_render_text_template_success(self, temp_templates_dir):
        """Test successful text template rendering."""
        engine = TemplateEngine(temp_templates_dir)
        
        template_data = {
            'name': 'John Doe',
            'email': 'john@example.com',
            'company': 'Acme Corp'
        }
        
        result = engine.render_text_template('test', template_data)
        
        assert 'Hello John Doe!' in result
        assert 'john@example.com' in result
        assert 'Acme Corp' in result
        assert 'Best regards' in result
    
    def test_template_caching(self, temp_templates_dir):
        """Test template caching functionality."""
        engine = TemplateEngine(temp_templates_dir)
        
        template_data = {'name': 'John', 'email': 'john@example.com', 'company': 'Test'}
        
        # First render should load from file
        result1 = engine.render_html_template('test', template_data)
        assert 'test_html' in engine._template_cache
        
        # Second render should use cache
        result2 = engine.render_html_template('test', template_data)
        assert result1 == result2
    
    def test_render_nonexistent_template_uses_default(self, temp_templates_dir):
        """Test rendering nonexistent template uses default."""
        engine = TemplateEngine(temp_templates_dir)
        
        template_data = {
            'name': 'John Doe',
            'email': 'john@example.com',
            'company': 'Acme Corp'
        }
        
        # Should use default contact_confirmation template
        result = engine.render_html_template('contact_confirmation', template_data)
        
        assert 'John Doe' in result
        assert 'john@example.com' in result
        assert '<html>' in result
    
    def test_render_template_with_missing_data(self, temp_templates_dir):
        """Test rendering template with missing data."""
        engine = TemplateEngine(temp_templates_dir)
        
        # Missing 'company' field
        template_data = {
            'name': 'John Doe',
            'email': 'john@example.com'
        }
        
        result = engine.render_html_template('test', template_data)
        
        # Should render with empty company field
        assert 'John Doe' in result
        assert 'john@example.com' in result
    
    def test_clear_cache(self, temp_templates_dir):
        """Test clearing template cache."""
        engine = TemplateEngine(temp_templates_dir)
        
        # Load a template to populate cache
        template_data = {'name': 'John', 'email': 'john@example.com', 'company': 'Test'}
        engine.render_html_template('test', template_data)
        
        assert len(engine._template_cache) > 0
        
        engine.clear_cache()
        
        assert len(engine._template_cache) == 0
    
    def test_list_templates(self, temp_templates_dir):
        """Test listing available templates."""
        engine = TemplateEngine(temp_templates_dir)
        
        templates = engine.list_templates()
        
        assert 'html' in templates
        assert 'text' in templates
        assert 'test' in templates['html']
        assert 'test' in templates['text']
    
    def test_validate_template_success(self, temp_templates_dir):
        """Test successful template validation."""
        engine = TemplateEngine(temp_templates_dir)
        
        sample_data = {
            'name': 'John Doe',
            'email': 'john@example.com',
            'company': 'Acme Corp'
        }
        
        result = engine.validate_template('test', 'html', sample_data)
        
        assert result['valid'] is True
        assert 'rendered_length' in result
        assert 'sample_output' in result
    
    def test_validate_template_failure(self, temp_templates_dir):
        """Test template validation failure."""
        engine = TemplateEngine(temp_templates_dir)
        
        # Create invalid template
        invalid_template = Path(temp_templates_dir) / 'invalid_html.mustache'
        invalid_template.write_text('{{#invalid_section}}{{/wrong_section}}')
        
        sample_data = {'name': 'John'}
        
        result = engine.validate_template('invalid', 'html', sample_data)
        
        assert result['valid'] is False
        assert 'error' in result


class TestDefaultTemplates:
    """Test default template functionality."""
    
    def test_default_contact_confirmation_html(self):
        """Test default contact confirmation HTML template."""
        engine = TemplateEngine()
        
        template_data = {
            'name': 'John',
            'full_name': 'John Doe',
            'email': 'john@example.com',
            'company': 'Acme Corp',
            'phone': '+1-555-0123',
            'message': 'I am interested in your solutions.',
            'preferred_contact_method': 'email',
            'submission_date': 'January 15, 2025',
            'submission_time': '2:30 PM',
            'correlation_id': 'test-correlation-id'
        }
        
        result = engine.render_html_template('contact_confirmation', template_data)
        
        assert 'Thank You, John!' in result
        assert 'John Doe' in result
        assert 'john@example.com' in result
        assert 'Acme Corp' in result
        assert 'I am interested in your solutions.' in result
        assert 'test-correlation-id' in result
        assert '<html>' in result
        assert 'DOCTYPE html' in result
    
    def test_default_contact_confirmation_text(self):
        """Test default contact confirmation text template."""
        engine = TemplateEngine()
        
        template_data = {
            'name': 'John',
            'full_name': 'John Doe',
            'email': 'john@example.com',
            'company': 'Acme Corp',
            'phone': '+1-555-0123',
            'message': 'I am interested in your solutions.',
            'preferred_contact_method': 'email',
            'submission_date': 'January 15, 2025',
            'submission_time': '2:30 PM',
            'correlation_id': 'test-correlation-id'
        }
        
        result = engine.render_text_template('contact_confirmation', template_data)
        
        assert 'Thank You, John!' in result
        assert 'John Doe' in result
        assert 'john@example.com' in result
        assert 'Acme Corp' in result
        assert 'I am interested in your solutions.' in result
        assert 'test-correlation-id' in result
        assert 'Event-Driven Architecture Team' in result
    
    def test_default_fallback_template(self):
        """Test default fallback template for unknown templates."""
        engine = TemplateEngine()
        
        template_data = {
            'title': 'Test Title',
            'message': 'Test Message'
        }
        
        # Request unknown template
        result = engine.render_html_template('unknown_template', template_data)
        
        # Should use fallback template
        assert 'Test Title' in result
        assert 'Test Message' in result
        assert '<html>' in result


class TestTemplateErrorHandling:
    """Test template error handling."""
    
    def test_render_with_exception_returns_fallback(self):
        """Test that rendering exceptions return fallback content."""
        engine = TemplateEngine()
        
        # Mock renderer to raise exception
        with patch.object(engine.renderer, 'render', side_effect=Exception("Render failed")):
            result = engine.render_html_template('test', {'name': 'John'})
            
            assert 'Error rendering template' in result
            assert '<html>' in result
    
    def test_render_text_with_exception_returns_fallback(self):
        """Test that text rendering exceptions return fallback content."""
        engine = TemplateEngine()
        
        # Mock renderer to raise exception
        with patch.object(engine.renderer, 'render', side_effect=Exception("Render failed")):
            result = engine.render_text_template('test', {'name': 'John'})
            
            assert 'Error rendering template' in result
    
    def test_list_templates_with_exception(self):
        """Test listing templates when exception occurs."""
        engine = TemplateEngine()
        
        # Mock glob to raise exception
        with patch.object(engine.templates_dir, 'glob', side_effect=Exception("Glob failed")):
            templates = engine.list_templates()
            
            assert templates == {'html': [], 'text': []}

