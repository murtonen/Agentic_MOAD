#!/usr/bin/env python
"""Run script for the MOAD AI Query Application."""

import os
from dotenv import load_dotenv
from app import create_app

# Load environment variables
load_dotenv()

# Create Flask application
app = create_app()

if __name__ == '__main__':
    # Get configuration from environment
    host = os.environ.get('FLASK_HOST', '127.0.0.1')
    port = int(os.environ.get('FLASK_PORT', 5000))
    debug = os.environ.get('FLASK_DEBUG', 'False').lower() == 'true'
    
    # Output server information
    print(f"Starting MOAD AI Query Server on {host}:{port}")
    print(f"Debug mode: {'ON' if debug else 'OFF'}")
    print("Press CTRL+C to quit")
    
    # Run the application
    app.run(host=host, port=port, debug=debug) 