#!/usr/bin/env python3
"""
Production Flask application for Nigerian School Result Portal
Serves both API and frontend static files
"""

import os
import sys
from pathlib import Path

# Add the backend src directory to Python path
current_dir = Path(__file__).parent
backend_src = current_dir / "backend" / "src"
sys.path.insert(0, str(backend_src))

# Change to backend directory for proper imports
os.chdir(current_dir / "backend")

from flask import Flask, send_from_directory, send_file
from src.main import create_app

# Create the Flask application
app = create_app('production')

# Configure static file serving for frontend
frontend_dir = current_dir / "frontend"

@app.route('/')
def serve_frontend():
    """Serve the main frontend application"""
    return send_file(frontend_dir / "index.html")

@app.route('/<path:path>')
def serve_static_files(path):
    """Serve static frontend files"""
    try:
        return send_from_directory(frontend_dir, path)
    except:
        # If file not found, serve index.html for client-side routing
        return send_file(frontend_dir / "index.html")

# Add a production info endpoint
@app.route('/api/production-info')
def production_info():
    """Get production deployment information"""
    return {
        'success': True,
        'data': {
            'application': 'Nigerian School Result Portal',
            'version': '1.0.0',
            'environment': 'production',
            'features': [
                'Admin Panel',
                'Teacher Portal', 
                'Student Portal',
                'Parent Portal',
                'Result Computation',
                'PDF Report Generation',
                'Security & Authentication',
                'Performance Analytics'
            ],
            'endpoints': {
                'frontend': '/',
                'api': '/api/*',
                'health': '/api/health',
                'documentation': '/api/info'
            }
        }
    }

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('FLASK_ENV') == 'development'
    
    print("=" * 60)
    print("🚀 Nigerian School Result Portal - Production Server")
    print("=" * 60)
    print(f"🌐 Server: http://0.0.0.0:{port}")
    print(f"📱 Frontend: http://localhost:{port}")
    print(f"🔧 API: http://localhost:{port}/api")
    print(f"💚 Health: http://localhost:{port}/api/health")
    print("=" * 60)
    
    app.run(host='0.0.0.0', port=port, debug=debug)

