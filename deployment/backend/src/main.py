import os
import sys
# DON'T CHANGE THIS !!!
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from flask import Flask, send_from_directory, jsonify
from flask_jwt_extended import JWTManager
from flask_cors import CORS
from flask_mail import Mail
from src.config import config
from src.models.models import db, User
from src.utils.auth import is_token_revoked, cleanup_expired_tokens

# Import all route blueprints
from src.routes.auth import auth_bp
from src.routes.admin import admin_bp
from src.routes.teacher import teacher_bp
from src.routes.student_parent import student_bp, parent_bp
from src.routes.security import security_bp
from src.routes.results import results_bp
from src.routes.reports import reports_bp

def create_app(config_name='development'):
    """Application factory pattern"""
    app = Flask(__name__, static_folder=os.path.join(os.path.dirname(__file__), 'static'))
    
    # Load configuration
    app.config.from_object(config[config_name])
    
    # Initialize extensions
    db.init_app(app)
    
    # Initialize JWT
    jwt = JWTManager(app)
    jwt.token_in_blocklist_loader(is_token_revoked)
    
    # JWT configuration for proper user ID handling
    @jwt.user_identity_loader
    def user_identity_lookup(user):
        return str(user)  # Ensure user ID is always a string
    
    @jwt.user_lookup_loader
    def user_lookup_callback(_jwt_header, jwt_data):
        identity = jwt_data["sub"]
        return User.query.filter_by(id=int(identity)).one_or_none()
    
    # Initialize CORS
    CORS(app, origins="*", allow_headers=["Content-Type", "Authorization"])
    
    # Initialize Mail
    mail = Mail(app)
    
    # Register blueprints
    app.register_blueprint(auth_bp, url_prefix='/api/auth')
    app.register_blueprint(admin_bp, url_prefix='/api/admin')
    app.register_blueprint(teacher_bp, url_prefix='/api/teacher')
    app.register_blueprint(student_bp, url_prefix='/api/student')
    app.register_blueprint(parent_bp, url_prefix='/api/parent')
    app.register_blueprint(security_bp, url_prefix='/api/security')
    app.register_blueprint(results_bp, url_prefix='/api/results')
    app.register_blueprint(reports_bp, url_prefix='/api/reports')
    
    # Add security middleware
    @app.after_request
    def add_security_headers(response):
        from src.utils.security import add_security_headers
        return add_security_headers(response)
    
    # Error handlers
    @app.errorhandler(404)
    def not_found(error):
        return jsonify({
            'success': False,
            'message': 'Resource not found',
            'error': 'Not Found'
        }), 404
    
    @app.errorhandler(500)
    def internal_error(error):
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': 'Internal server error',
            'error': 'Internal Server Error'
        }), 500
    
    @app.errorhandler(400)
    def bad_request(error):
        return jsonify({
            'success': False,
            'message': 'Bad request',
            'error': 'Bad Request'
        }), 400
    
    @app.errorhandler(401)
    def unauthorized(error):
        return jsonify({
            'success': False,
            'message': 'Unauthorized access',
            'error': 'Unauthorized'
        }), 401
    
    @app.errorhandler(403)
    def forbidden(error):
        return jsonify({
            'success': False,
            'message': 'Access forbidden',
            'error': 'Forbidden'
        }), 403
    
    # JWT error handlers
    @jwt.expired_token_loader
    def expired_token_callback(jwt_header, jwt_payload):
        return jsonify({
            'success': False,
            'message': 'Token has expired',
            'error': 'Token Expired'
        }), 401
    
    @jwt.invalid_token_loader
    def invalid_token_callback(error):
        return jsonify({
            'success': False,
            'message': 'Invalid token',
            'error': 'Invalid Token'
        }), 401
    
    @jwt.unauthorized_loader
    def missing_token_callback(error):
        return jsonify({
            'success': False,
            'message': 'Authorization token is required',
            'error': 'Missing Token'
        }), 401
    
    @jwt.revoked_token_loader
    def revoked_token_callback(jwt_header, jwt_payload):
        return jsonify({
            'success': False,
            'message': 'Token has been revoked',
            'error': 'Revoked Token'
        }), 401
    
    # Health check endpoint
    @app.route('/api/health', methods=['GET'])
    def health_check():
        return jsonify({
            'success': True,
            'message': 'Nigerian School Result Portal API is running',
            'version': '1.0.0',
            'status': 'healthy'
        })
    
    # API info endpoint
    @app.route('/api/info', methods=['GET'])
    def api_info():
        return jsonify({
            'success': True,
            'data': {
                'name': 'Nigerian School Result Portal API',
                'version': '1.0.0',
                'description': 'Comprehensive result management system for Nigerian schools',
                'endpoints': {
                    'authentication': '/api/auth',
                    'admin': '/api/admin',
                    'teacher': '/api/teacher',
                    'student': '/api/student',
                    'parent': '/api/parent'
                },
                'features': [
                    'Role-based access control',
                    'Result entry and computation',
                    'Report card generation',
                    'Performance analytics',
                    'Multi-term management',
                    'WAEC grading system'
                ]
            }
        })
    
    # Serve frontend files
    @app.route('/', defaults={'path': ''})
    @app.route('/<path:path>')
    def serve(path):
        static_folder_path = app.static_folder
        if static_folder_path is None:
            return jsonify({
                'success': False,
                'message': 'Frontend not configured'
            }), 404

        if path != "" and os.path.exists(os.path.join(static_folder_path, path)):
            return send_from_directory(static_folder_path, path)
        else:
            index_path = os.path.join(static_folder_path, 'index.html')
            if os.path.exists(index_path):
                return send_from_directory(static_folder_path, 'index.html')
            else:
                return jsonify({
                    'success': True,
                    'message': 'Nigerian School Result Portal API',
                    'documentation': '/api/info'
                })
    
    # Initialize database
    with app.app_context():
        try:
            db.create_all()
            print("Database tables created successfully")
            
            # Clean up expired tokens on startup
            cleanup_expired_tokens()
            print("Expired tokens cleaned up")
            
        except Exception as e:
            print(f"Database initialization error: {str(e)}")
    
    return app

# Create the application instance
app = create_app(os.environ.get('FLASK_ENV', 'development'))

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('FLASK_ENV') == 'development'
    
    print("=" * 50)
    print("Nigerian School Result Portal API")
    print("=" * 50)
    print(f"Environment: {os.environ.get('FLASK_ENV', 'development')}")
    print(f"Port: {port}")
    print(f"Debug: {debug}")
    print("API Endpoints:")
    print("  - Health Check: /api/health")
    print("  - API Info: /api/info")
    print("  - Authentication: /api/auth/*")
    print("  - Admin Portal: /api/admin/*")
    print("  - Teacher Portal: /api/teacher/*")
    print("  - Student Portal: /api/student/*")
    print("  - Parent Portal: /api/parent/*")
    print("=" * 50)
    
    app.run(host='0.0.0.0', port=port, debug=debug)

