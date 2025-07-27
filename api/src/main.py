import os
import sys
import logging
import atexit
from datetime import datetime, timezone

# DON'T CHANGE THIS !!!
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from flask import Flask, send_from_directory, jsonify
from flask_cors import CORS
from src.models.user import db
from src.routes.user import user_bp
from src.routes.contact import contact_bp
from src.routes.crm import crm_bp
from src.services.event_publisher import close_event_publisher

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = Flask(__name__, static_folder=os.path.join(os.path.dirname(__file__), 'static'))

# Configuration
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'asdf#FGSgvasgf$5$WGT')
app.config['SQLALCHEMY_DATABASE_URI'] = f"sqlite:///{os.path.join(os.path.dirname(__file__), 'database', 'app.db')}"
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Enable CORS for all routes
CORS(app, origins="*", methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"])

# Register blueprints
app.register_blueprint(user_bp, url_prefix='/api')
app.register_blueprint(contact_bp, url_prefix='/api')
app.register_blueprint(crm_bp, url_prefix='/api')

# Initialize database
db.init_app(app)
with app.app_context():
    db.create_all()
    logger.info("Database initialized successfully")


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)


# Health check endpoint
@app.route('/health', methods=['GET'])
def health_check():
    """Global health check endpoint."""
    try:
        # Test database connection
        from sqlalchemy import text
        db.session.execute(text('SELECT 1'))
        
        return jsonify({
            'status': 'healthy',
            'service': 'event-driven-api',
            'version': '1.0.0',
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'components': {
                'database': 'connected',
                'event_publisher': 'available'
            }
        }), 200
        
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return jsonify({
            'status': 'unhealthy',
            'error': str(e),
            'timestamp': datetime.now(timezone.utc).isoformat()
        }), 503


# API info endpoint
@app.route('/api', methods=['GET'])
def api_info():
    """API information endpoint."""
    return jsonify({
        'name': 'Event-Driven Architecture API',
        'version': '1.0.0',
        'description': 'Proof of concept for event-driven architecture with contact forms and workflow automation',
        'endpoints': {
            'contact_form': '/api/contact',
            'crm_leads': '/api/internal/leads',
            'health': '/health',
        },
        'documentation': 'https://github.com/your-org/event-driven-poc',
        'timestamp': datetime.now(timezone.utc).isoformat()
    }), 200


# Error handlers
@app.errorhandler(404)
def not_found(error):
    """Handle 404 errors."""
    return jsonify({
        'error': 'Not found',
        'message': 'The requested resource was not found'
    }), 404


@app.errorhandler(500)
def internal_error(error):
    """Handle 500 errors."""
    logger.error(f"Internal server error: {error}")
    return jsonify({
        'error': 'Internal server error',
        'message': 'An unexpected error occurred'
    }), 500

if __name__ == '__main__':
    logger.info("Starting Event-Driven Architecture API...")
    logger.info(f"Environment: {os.getenv('FLASK_ENV', 'development')}")
    logger.info(f"Kafka Bootstrap Servers: {os.getenv('KAFKA_BOOTSTRAP_SERVERS', 'localhost:9092')}")
    
    app.run(host='0.0.0.0', port=5000, debug=True)

