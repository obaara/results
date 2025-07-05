from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity, get_jwt
from datetime import datetime, timedelta
from src.models.models import db, User
from src.utils.security import (
    SecurityManager, rate_limit, validate_input, log_security_event,
    generate_password_reset_token, validate_password_reset_token,
    cleanup_expired_reset_tokens, require_permissions
)

security_bp = Blueprint('security', __name__)

@security_bp.route('/change-password', methods=['POST'])
@jwt_required()
@rate_limit(max_requests=3, window_minutes=15)
@validate_input(
    current_password={'required': True, 'type': str, 'min_length': 1},
    new_password={'required': True, 'type': str, 'min_length': 8},
    confirm_password={'required': True, 'type': str, 'min_length': 8}
)
def change_password():
    """Change user password"""
    try:
        current_user_id = get_jwt_identity()
        data = request.get_json()
        
        user = User.query.get(current_user_id)
        if not user:
            return jsonify({
                'success': False,
                'message': 'User not found'
            }), 404
        
        # Verify current password
        if not user.check_password(data['current_password']):
            log_security_event('password_change_failed', user.id, {
                'reason': 'incorrect_current_password'
            })
            return jsonify({
                'success': False,
                'message': 'Current password is incorrect'
            }), 400
        
        # Validate new password
        if data['new_password'] != data['confirm_password']:
            return jsonify({
                'success': False,
                'message': 'New passwords do not match'
            }), 400
        
        # Check password strength
        is_strong, message = SecurityManager.validate_password_strength(data['new_password'])
        if not is_strong:
            return jsonify({
                'success': False,
                'message': message
            }), 400
        
        # Update password
        user.set_password(data['new_password'])
        user.updated_at = datetime.utcnow()
        db.session.commit()
        
        log_security_event('password_changed', user.id)
        
        return jsonify({
            'success': True,
            'message': 'Password changed successfully'
        })
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Password change error: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'Failed to change password'
        }), 500

@security_bp.route('/request-password-reset', methods=['POST'])
@rate_limit(max_requests=3, window_minutes=60)
@validate_input(
    email={'required': True, 'type': str, 'validator': lambda x: (SecurityManager.validate_email(x), 'Invalid email format')}
)
def request_password_reset():
    """Request password reset token"""
    try:
        data = request.get_json()
        email = data['email'].lower().strip()
        
        user = User.query.filter_by(email=email, is_active=True).first()
        
        # Always return success to prevent email enumeration
        response = {
            'success': True,
            'message': 'If an account with this email exists, a password reset link has been sent.'
        }
        
        if user:
            # Generate reset token
            reset_token = generate_password_reset_token(user.id)
            
            # In production, send email with reset link
            reset_link = f"{request.host_url}reset-password?token={reset_token}"
            
            log_security_event('password_reset_requested', user.id, {
                'email': email,
                'reset_token': reset_token[:8] + '...'  # Log partial token for tracking
            })
            
            # TODO: Send email with reset_link
            current_app.logger.info(f"Password reset requested for {email}. Reset link: {reset_link}")
        
        return jsonify(response)
        
    except Exception as e:
        current_app.logger.error(f"Password reset request error: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'Failed to process password reset request'
        }), 500

@security_bp.route('/reset-password', methods=['POST'])
@rate_limit(max_requests=5, window_minutes=60)
@validate_input(
    token={'required': True, 'type': str, 'min_length': 10},
    new_password={'required': True, 'type': str, 'min_length': 8},
    confirm_password={'required': True, 'type': str, 'min_length': 8}
)
def reset_password():
    """Reset password using token"""
    try:
        data = request.get_json()
        
        # Validate token
        is_valid, user_id = validate_password_reset_token(data['token'])
        if not is_valid:
            return jsonify({
                'success': False,
                'message': 'Invalid or expired reset token'
            }), 400
        
        # Validate passwords match
        if data['new_password'] != data['confirm_password']:
            return jsonify({
                'success': False,
                'message': 'Passwords do not match'
            }), 400
        
        # Check password strength
        is_strong, message = SecurityManager.validate_password_strength(data['new_password'])
        if not is_strong:
            return jsonify({
                'success': False,
                'message': message
            }), 400
        
        # Get user and update password
        user = User.query.get(user_id)
        if not user or not user.is_active:
            return jsonify({
                'success': False,
                'message': 'User not found or inactive'
            }), 404
        
        user.set_password(data['new_password'])
        user.updated_at = datetime.utcnow()
        db.session.commit()
        
        # Invalidate the reset token
        from src.utils.security import password_reset_tokens
        if data['token'] in password_reset_tokens:
            del password_reset_tokens[data['token']]
        
        log_security_event('password_reset_completed', user.id)
        
        return jsonify({
            'success': True,
            'message': 'Password reset successfully'
        })
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Password reset error: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'Failed to reset password'
        }), 500

@security_bp.route('/update-profile', methods=['PUT'])
@jwt_required()
@rate_limit(max_requests=10, window_minutes=60)
def update_profile():
    """Update user profile information"""
    try:
        current_user_id = get_jwt_identity()
        data = request.get_json()
        
        user = User.query.get(current_user_id)
        if not user:
            return jsonify({
                'success': False,
                'message': 'User not found'
            }), 404
        
        # Validate and update allowed fields
        allowed_fields = ['first_name', 'last_name', 'middle_name', 'phone', 'address']
        updated_fields = []
        
        for field in allowed_fields:
            if field in data:
                value = SecurityManager.sanitize_input(data[field])
                if value != getattr(user, field):
                    setattr(user, field, value)
                    updated_fields.append(field)
        
        # Validate phone if provided
        if 'phone' in data and data['phone']:
            if not SecurityManager.validate_phone(data['phone']):
                return jsonify({
                    'success': False,
                    'message': 'Invalid phone number format'
                }), 400
        
        if updated_fields:
            user.updated_at = datetime.utcnow()
            db.session.commit()
            
            log_security_event('profile_updated', user.id, {
                'updated_fields': updated_fields
            })
        
        return jsonify({
            'success': True,
            'message': 'Profile updated successfully',
            'data': {
                'updated_fields': updated_fields
            }
        })
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Profile update error: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'Failed to update profile'
        }), 500

@security_bp.route('/security-log', methods=['GET'])
@jwt_required()
@require_permissions('view_security_logs')
def get_security_log():
    """Get security event logs (admin only)"""
    try:
        # In production, this would query a proper security log table
        # For now, return a placeholder response
        
        return jsonify({
            'success': True,
            'message': 'Security logs retrieved',
            'data': {
                'logs': [],
                'total': 0,
                'note': 'Security logging is configured but logs are stored in application logs'
            }
        })
        
    except Exception as e:
        current_app.logger.error(f"Security log error: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'Failed to retrieve security logs'
        }), 500

@security_bp.route('/session-info', methods=['GET'])
@jwt_required()
def get_session_info():
    """Get current session information"""
    try:
        current_user_id = get_jwt_identity()
        jwt_data = get_jwt()
        
        user = User.query.get(current_user_id)
        if not user:
            return jsonify({
                'success': False,
                'message': 'User not found'
            }), 404
        
        return jsonify({
            'success': True,
            'data': {
                'user_id': user.id,
                'username': user.username,
                'role': user.role.value,
                'school_id': user.school_id,
                'token_issued_at': datetime.fromtimestamp(jwt_data['iat']).isoformat(),
                'token_expires_at': datetime.fromtimestamp(jwt_data['exp']).isoformat(),
                'last_login': user.updated_at.isoformat() if user.updated_at else None
            }
        })
        
    except Exception as e:
        current_app.logger.error(f"Session info error: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'Failed to retrieve session information'
        }), 500

@security_bp.route('/validate-token', methods=['POST'])
@jwt_required()
def validate_token():
    """Validate JWT token"""
    try:
        current_user_id = get_jwt_identity()
        user = User.query.get(current_user_id)
        
        if not user or not user.is_active:
            return jsonify({
                'success': False,
                'message': 'Invalid or inactive user'
            }), 401
        
        return jsonify({
            'success': True,
            'message': 'Token is valid',
            'data': {
                'user_id': user.id,
                'role': user.role.value,
                'is_active': user.is_active
            }
        })
        
    except Exception as e:
        current_app.logger.error(f"Token validation error: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'Token validation failed'
        }), 401

# Cleanup task (should be run periodically)
@security_bp.route('/cleanup-tokens', methods=['POST'])
@jwt_required()
@require_permissions('system_maintenance')
def cleanup_security_tokens():
    """Clean up expired security tokens (admin only)"""
    try:
        cleanup_expired_reset_tokens()
        
        return jsonify({
            'success': True,
            'message': 'Security tokens cleaned up successfully'
        })
        
    except Exception as e:
        current_app.logger.error(f"Token cleanup error: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'Failed to clean up tokens'
        }), 500

