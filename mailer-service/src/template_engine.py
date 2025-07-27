"""
Template engine for the Mailer service.
Handles Mustache template rendering for HTML and text emails.
"""

import os
import logging
from typing import Dict, Any, Optional
import pystache
from pathlib import Path


class TemplateEngine:
    """
    Template engine for rendering email templates using Mustache.
    """
    
    def __init__(self, templates_dir: Optional[str] = None):
        """
        Initialize the template engine.
        
        Args:
            templates_dir: Directory containing email templates
        """
        self.logger = logging.getLogger(__name__)
        
        # Set templates directory
        if templates_dir:
            self.templates_dir = Path(templates_dir)
        else:
            # Default to templates directory relative to this file
            current_dir = Path(__file__).parent
            self.templates_dir = current_dir.parent / 'templates'
        
        self.templates_dir.mkdir(exist_ok=True)
        
        # Initialize Mustache renderer
        self.renderer = pystache.Renderer(
            file_extension='mustache',
            string_encoding='utf-8',
            decode_errors='strict',
            search_dirs=[str(self.templates_dir)]
        )
        
        # Template cache
        self._template_cache = {}
        
        self.logger.info(f"Template engine initialized with directory: {self.templates_dir}")
    
    def _load_template(self, template_name: str, template_type: str) -> str:
        """
        Load a template from file.
        
        Args:
            template_name: Name of the template (without extension)
            template_type: Type of template ('html' or 'text')
            
        Returns:
            str: Template content
        """
        cache_key = f"{template_name}_{template_type}"
        
        # Check cache first
        if cache_key in self._template_cache:
            return self._template_cache[cache_key]
        
        # Construct template file path
        template_file = self.templates_dir / f"{template_name}_{template_type}.mustache"
        
        try:
            if template_file.exists():
                with open(template_file, 'r', encoding='utf-8') as f:
                    template_content = f.read()
                
                # Cache the template
                self._template_cache[cache_key] = template_content
                self.logger.debug(f"Loaded template: {template_file}")
                
                return template_content
            else:
                # Return default template if file doesn't exist
                self.logger.warning(f"Template file not found: {template_file}, using default")
                return self._get_default_template(template_name, template_type)
                
        except Exception as e:
            self.logger.error(f"Error loading template {template_file}: {e}")
            return self._get_default_template(template_name, template_type)
    
    def _get_default_template(self, template_name: str, template_type: str) -> str:
        """
        Get default template content when template file is not found.
        
        Args:
            template_name: Name of the template
            template_type: Type of template ('html' or 'text')
            
        Returns:
            str: Default template content
        """
        if template_name == 'contact_confirmation':
            if template_type == 'html':
                return """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Thank You for Your Interest</title>
    <style>
        body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; padding: 20px; }
        .header { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 30px; text-align: center; border-radius: 8px 8px 0 0; }
        .content { background: #f9f9f9; padding: 30px; border-radius: 0 0 8px 8px; }
        .highlight { background: #e3f2fd; padding: 15px; border-left: 4px solid #2196f3; margin: 20px 0; }
        .footer { text-align: center; margin-top: 30px; padding-top: 20px; border-top: 1px solid #ddd; color: #666; font-size: 14px; }
        .button { display: inline-block; background: #2196f3; color: white; padding: 12px 24px; text-decoration: none; border-radius: 4px; margin: 10px 0; }
    </style>
</head>
<body>
    <div class="header">
        <h1>Thank You, {{name}}!</h1>
        <p>We've received your message and will get back to you soon.</p>
    </div>
    
    <div class="content">
        <p>Dear {{full_name}},</p>
        
        <p>Thank you for reaching out to us through our contact form. We appreciate your interest in our event-driven architecture solutions.</p>
        
        <div class="highlight">
            <h3>Your Submission Details:</h3>
            <ul>
                <li><strong>Company:</strong> {{company}}</li>
                <li><strong>Email:</strong> {{email}}</li>
                <li><strong>Phone:</strong> {{phone}}</li>
                <li><strong>Preferred Contact:</strong> {{preferred_contact_method}}</li>
                <li><strong>Submitted:</strong> {{submission_date}} at {{submission_time}}</li>
            </ul>
        </div>
        
        <p><strong>Your Message:</strong></p>
        <p style="background: white; padding: 15px; border-radius: 4px; border: 1px solid #ddd;">{{message}}</p>
        
        <p>Our team will review your inquiry and respond within 24 hours. In the meantime, feel free to explore our documentation and examples.</p>
        
        <p>This email was generated automatically by our event-driven system with correlation ID: <code>{{correlation_id}}</code></p>
    </div>
    
    <div class="footer">
        <p>Best regards,<br>The Event-Driven Architecture Team</p>
        <p><small>This is an automated message. Please do not reply to this email.</small></p>
    </div>
</body>
</html>
"""
            else:  # text
                return """
Thank You, {{name}}!

Dear {{full_name}},

Thank you for reaching out to us through our contact form. We appreciate your interest in our event-driven architecture solutions.

Your Submission Details:
- Company: {{company}}
- Email: {{email}}
- Phone: {{phone}}
- Preferred Contact: {{preferred_contact_method}}
- Submitted: {{submission_date}} at {{submission_time}}

Your Message:
{{message}}

Our team will review your inquiry and respond within 24 hours. In the meantime, feel free to explore our documentation and examples.

This email was generated automatically by our event-driven system with correlation ID: {{correlation_id}}

Best regards,
The Event-Driven Architecture Team

---
This is an automated message. Please do not reply to this email.
"""
        
        # Default fallback template
        if template_type == 'html':
            return "<html><body><h1>{{title}}</h1><p>{{message}}</p></body></html>"
        else:
            return "{{title}}\n\n{{message}}"
    
    def render_html_template(self, template_name: str, data: Dict[str, Any]) -> str:
        """
        Render an HTML email template.
        
        Args:
            template_name: Name of the template to render
            data: Data to populate the template
            
        Returns:
            str: Rendered HTML content
        """
        try:
            template_content = self._load_template(template_name, 'html')
            rendered = self.renderer.render(template_content, data)
            
            self.logger.debug(f"Rendered HTML template: {template_name}")
            return rendered
            
        except Exception as e:
            self.logger.error(f"Error rendering HTML template {template_name}: {e}")
            # Return a basic fallback
            return f"<html><body><h1>Email</h1><p>Error rendering template: {e}</p></body></html>"
    
    def render_text_template(self, template_name: str, data: Dict[str, Any]) -> str:
        """
        Render a text email template.
        
        Args:
            template_name: Name of the template to render
            data: Data to populate the template
            
        Returns:
            str: Rendered text content
        """
        try:
            template_content = self._load_template(template_name, 'text')
            rendered = self.renderer.render(template_content, data)
            
            self.logger.debug(f"Rendered text template: {template_name}")
            return rendered
            
        except Exception as e:
            self.logger.error(f"Error rendering text template {template_name}: {e}")
            # Return a basic fallback
            return f"Email\n\nError rendering template: {e}"
    
    def clear_cache(self):
        """Clear the template cache."""
        self._template_cache.clear()
        self.logger.info("Template cache cleared")
    
    def list_templates(self) -> Dict[str, list]:
        """
        List available templates.
        
        Returns:
            Dict with 'html' and 'text' keys containing lists of template names
        """
        templates = {'html': [], 'text': []}
        
        try:
            for template_file in self.templates_dir.glob('*.mustache'):
                name_parts = template_file.stem.split('_')
                if len(name_parts) >= 2:
                    template_type = name_parts[-1]
                    template_name = '_'.join(name_parts[:-1])
                    
                    if template_type in templates:
                        templates[template_type].append(template_name)
            
        except Exception as e:
            self.logger.error(f"Error listing templates: {e}")
        
        return templates
    
    def validate_template(self, template_name: str, template_type: str, 
                         sample_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate a template by rendering it with sample data.
        
        Args:
            template_name: Name of the template to validate
            template_type: Type of template ('html' or 'text')
            sample_data: Sample data for rendering
            
        Returns:
            Dict containing validation results
        """
        try:
            if template_type == 'html':
                rendered = self.render_html_template(template_name, sample_data)
            else:
                rendered = self.render_text_template(template_name, sample_data)
            
            return {
                'valid': True,
                'rendered_length': len(rendered),
                'sample_output': rendered[:200] + '...' if len(rendered) > 200 else rendered
            }
            
        except Exception as e:
            return {
                'valid': False,
                'error': str(e)
            }

