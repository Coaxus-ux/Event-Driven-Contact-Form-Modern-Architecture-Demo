#!/usr/bin/env python3
"""
Main entry point for the Mailer Service.
"""

import os
import sys
from pathlib import Path

# Add src directory to Python path
src_dir = Path(__file__).parent / 'src'
sys.path.insert(0, str(src_dir))

from src.mailer_service import main

if __name__ == '__main__':
    # Set environment variables for development if not already set
    if not os.getenv('KAFKA_BOOTSTRAP_SERVERS'):
        os.environ['KAFKA_BOOTSTRAP_SERVERS'] = 'localhost:9092'
    
    if not os.getenv('KAFKA_TOPIC'):
        os.environ['KAFKA_TOPIC'] = 'events.contact_form'
    
    if not os.getenv('KAFKA_CONSUMER_GROUP'):
        os.environ['KAFKA_CONSUMER_GROUP'] = 'mailer-service'
    
    if not os.getenv('SMTP_HOST'):
        os.environ['SMTP_HOST'] = 'localhost'
    
    if not os.getenv('FROM_EMAIL'):
        os.environ['FROM_EMAIL'] = 'noreply@event-driven-poc.com'
    
    if not os.getenv('FROM_NAME'):
        os.environ['FROM_NAME'] = 'Event-Driven PoC Team'
    
    # Start the service
    sys.exit(main())

