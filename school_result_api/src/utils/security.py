"""
Security utilities for the Nigerian School Result Portal
Includes password hashing, input validation, rate limiting, and security headers
"""

import re
import hashlib
import secrets
import time
from functools import wraps
from datetime import datetime, timedelta
from flask import request, jsonify, current_app
from werkzeug.security import check_password_hash, generate_password_hash
import bcrypt

class SecurityManager:
    """Centralized security management class"""
    
    @staticmethod
    def hash_password(password):
        """Hash password using bcrypt"""
        return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    
    @staticmethod
    def verify_password(password, hashed):
        """Verify password against hash"""
        return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))
    
    @staticmethod
    def generate_secure_token(length=32):
        """Generate cryptographically secure random token"""
        return secrets.token_urlsafe(length)
    
    @staticmethod
    def validate_password_strength(password):
        """Validate password meets security requirements"""
        if len(password) < 8:
            return False, "Password must be at least 8 characters long"
        
        if not re.search(r"[A-Z]", password):
            return False, "Password must contain at least one uppercase letter"
        
        if not re.search(r"[a-z]", password):
            return False, "Password must contain at least one lowercase letter"
        
        if not re.search(r"\d", password):
            return False, "Password must contain at least one digit"
        
        return True, "Password is strong"
    
    @staticmethod
    def sanitize_input(input_string):
        """Sanitize user input to prevent XSS and injection attacks"""
        if not isinstance(input_string, str):
            return input_string
        
        # Remove potentially dangerous characters
        sanitized = re.sub(r'[<>"\']', '', input_string)
        return sanitized.strip()
    
    @staticmethod
    def validate_email(email):
        """Validate email format"""
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return re.match(pattern, email) is not None
    
    @staticmethod
    def validate_phone(phone):
        """Validate Nigerian phone number format"""
        # Remove spaces and special characters
        clean_phone = re.sub(r'[\s\-\(\)]', '', phone)
        
        # Check for Nigerian phone number patterns
        patterns = [
            r'^\+234[789]\d{9}$',  # +234 format
            r'^234[789]\d{9}$',    # 234 format
            r'^0[789]\d{9}$',      # 0 format
            r'^[789]\d{9}$'        # Direct format
        ]
        
        return any(re.match(pattern, clean_phone) for pattern in patterns)

# Rate limiting storage (in production, use Redis)
rate_limit_storage = {}

def rate_limit(max_requests=5, window_minutes=15):
    """Rate limiting decorator"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # Get client IP
            client_ip = request.environ.get('HTTP_X_FORWARDED_FOR', request.remote_addr)
            
            # Create key for this IP and endpoint
            key = f"{client_ip}:{request.endpoint}"
            current_time = time.time()
            window_start = current_time - (window_minutes * 60)
            
            # Clean old entries
            if key in rate_limit_storage:
                rate_limit_storage[key] = [
                    timestamp for timestamp in rate_limit_storage[key] 
                    if timestamp > window_start
                ]
            else:
                rate_limit_storage[key] = []
            
            # Check if limit exceeded
            if len(rate_limit_storage[key]) >= max_requests:
                return jsonify({
                    'success': False,
                    'message': 'Rate limit exceeded. Please try again later.',
                    'error': 'Too Many Requests'
                }), 429
            
            # Add current request
            rate_limit_storage[key].append(current_time)
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def validate_input(**validators):
    """Input validation decorator"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            data = request.get_json() or {}
            errors = []
            
            for field, rules in validators.items():
                value = data.get(field)
                
                # Check required fields
                if 'required' in rules and rules['required'] and not value:
                    errors.append(f"{field} is required")
                    continue
                
                if value is not None:
                    # Check type
                    if 'type' in rules and not isinstance(value, rules['type']):
                        errors.append(f"{field} must be of type {rules['type'].__name__}")
                    
                    # Check length
                    if 'min_length' in rules and len(str(value)) < rules['min_length']:
                        errors.append(f"{field} must be at least {rules['min_length']} characters")
                    
                    if 'max_length' in rules and len(str(value)) > rules['max_length']:
                        errors.append(f"{field} must be at most {rules['max_length']} characters")
                    
                    # Check pattern
                    if 'pattern' in rules and not re.match(rules['pattern'], str(value)):
                        errors.append(f"{field} format is invalid")
                    
                    # Custom validation
                    if 'validator' in rules:
                        is_valid, message = rules['validator'](value)
                        if not is_valid:
                            errors.append(f"{field}: {message}")
            
            if errors:
                return jsonify({
                    'success': False,
                    'message': 'Validation failed',
                    'errors': errors
                }), 400
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def add_security_headers(response):
    """Add security headers to response"""
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
    response.headers['Content-Security-Policy'] = "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'"
    return response

def log_security_event(event_type, user_id=None, details=None):
    """Log security-related events"""
    timestamp = datetime.utcnow().isoformat()
    client_ip = request.environ.get('HTTP_X_FORWARDED_FOR', request.remote_addr)
    user_agent = request.headers.get('User-Agent', 'Unknown')
    
    log_entry = {
        'timestamp': timestamp,
        'event_type': event_type,
        'user_id': user_id,
        'client_ip': client_ip,
        'user_agent': user_agent,
        'details': details or {}
    }
    
    # In production, send to proper logging system
    current_app.logger.warning(f"Security Event: {log_entry}")

def require_permissions(*required_permissions):
    """Decorator to check user permissions"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            from flask_jwt_extended import get_jwt_identity, verify_jwt_in_request
            from src.models.models import User
            
            try:
                verify_jwt_in_request()
                current_user_id = get_jwt_identity()
                
                user = User.query.get(int(current_user_id))
                if not user:
                    return jsonify({
                        'success': False,
                        'message': 'User not found',
                        'error': 'Unauthorized'
                    }), 401
                
                # Check if user has required permissions
                user_permissions = get_user_permissions(user.role.value)
                
                if not all(perm in user_permissions for perm in required_permissions):
                    log_security_event('unauthorized_access_attempt', user.id, {
                        'required_permissions': required_permissions,
                        'user_permissions': user_permissions
                    })
                    
                    return jsonify({
                        'success': False,
                        'message': 'Insufficient permissions',
                        'error': 'Forbidden'
                    }), 403
                
                return f(*args, **kwargs)
                
            except Exception as e:
                return jsonify({
                    'success': False,
                    'message': 'Authorization failed',
                    'error': str(e)
                }), 401
                
        return decorated_function
    return decorator

def get_user_permissions(role):
    """Get permissions for a user role"""
    permissions = {
        'super_admin': [
            'manage_schools', 'manage_users', 'manage_classes', 'manage_subjects',
            'view_all_results', 'manage_sessions', 'system_settings', 'view_reports',
            'view_security_logs', 'system_maintenance'
        ],
        'school_admin': [
            'manage_users', 'manage_classes', 'manage_subjects', 'view_all_results',
            'manage_sessions', 'school_settings', 'view_reports'
        ],
        'teacher': [
            'view_assigned_classes', 'enter_results', 'view_student_results',
            'manage_class_students', 'generate_class_reports'
        ],
        'student': [
            'view_own_results', 'view_own_profile', 'download_own_reports'
        ],
        'parent': [
            'view_children_results', 'view_children_profiles', 'download_children_reports'
        ]
    }
    
    return permissions.get(role, [])

# Password reset functionality
password_reset_tokens = {}

def generate_password_reset_token(user_id):
    """Generate password reset token"""
    token = SecurityManager.generate_secure_token()
    expiry = datetime.utcnow() + timedelta(hours=1)  # 1 hour expiry
    
    password_reset_tokens[token] = {
        'user_id': user_id,
        'expiry': expiry
    }
    
    return token

def validate_password_reset_token(token):
    """Validate password reset token"""
    if token not in password_reset_tokens:
        return False, None
    
    token_data = password_reset_tokens[token]
    if datetime.utcnow() > token_data['expiry']:
        del password_reset_tokens[token]
        return False, None
    
    return True, token_data['user_id']

def cleanup_expired_reset_tokens():
    """Clean up expired password reset tokens"""
    current_time = datetime.utcnow()
    expired_tokens = [
        token for token, data in password_reset_tokens.items()
        if current_time > data['expiry']
    ]
    
    for token in expired_tokens:
        del password_reset_tokens[token]

