from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import (
    create_access_token, create_refresh_token, jwt_required,
    get_jwt_identity, get_jwt
)
from src.models.models import db, User, TokenBlacklist
from src.utils.auth import (
    add_token_to_blacklist, format_response, validate_input,
    token_required
)
from datetime import datetime, timedelta
import secrets
import string

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/login', methods=['POST'])
def login():
    """User login endpoint"""
    try:
        data = request.get_json()
        
        # Validate input
        errors = validate_input(data, ['username', 'password'])
        if errors:
            return format_response(False, "Validation failed", errors=errors, status_code=400)
        
        username = data.get('username')
        password = data.get('password')
        
        # Find user by username or email
        user = User.query.filter(
            (User.username == username) | (User.email == username)
        ).first()
        
        if not user or not user.check_password(password):
            return format_response(False, "Invalid username or password", status_code=401)
        
        if not user.is_active:
            return format_response(False, "Account is deactivated", status_code=403)
        
        # Create tokens
        access_token = create_access_token(identity=user.id)
        refresh_token = create_refresh_token(identity=user.id)
        
        # Prepare user data
        user_data = {
            'id': user.id,
            'username': user.username,
            'email': user.email,
            'full_name': user.full_name,
            'role': user.role.value,
            'school_id': user.school_id,
            'school_name': user.school.name if user.school else None
        }
        
        # Add role-specific data
        if user.role.value == 'student' and user.student_profile:
            user_data['student_id'] = user.student_profile.student_id
            user_data['current_class'] = user.student_profile.current_class.class_name if user.student_profile.current_class else None
        
        response_data = {
            'user': user_data,
            'access_token': access_token,
            'refresh_token': refresh_token
        }
        
        return format_response(True, "Login successful", response_data)
        
    except Exception as e:
        return format_response(False, f"Login failed: {str(e)}", status_code=500)

@auth_bp.route('/refresh', methods=['POST'])
@jwt_required(refresh=True)
def refresh():
    """Refresh access token"""
    try:
        current_user_id = get_jwt_identity()
        user = User.query.get(current_user_id)
        
        if not user or not user.is_active:
            return format_response(False, "User not found or inactive", status_code=404)
        
        new_access_token = create_access_token(identity=current_user_id)
        
        return format_response(True, "Token refreshed successfully", {
            'access_token': new_access_token
        })
        
    except Exception as e:
        return format_response(False, f"Token refresh failed: {str(e)}", status_code=500)

@auth_bp.route('/logout', methods=['POST'])
@jwt_required()
def logout():
    """User logout endpoint"""
    try:
        jti = get_jwt()['jti']
        token_type = get_jwt()['type']
        user_id = get_jwt_identity()
        expires = datetime.fromtimestamp(get_jwt()['exp'])
        
        add_token_to_blacklist(jti, token_type, user_id, expires)
        
        return format_response(True, "Successfully logged out")
        
    except Exception as e:
        return format_response(False, f"Logout failed: {str(e)}", status_code=500)

@auth_bp.route('/forgot-password', methods=['POST'])
def forgot_password():
    """Initiate password reset process"""
    try:
        data = request.get_json()
        
        errors = validate_input(data, ['email'])
        if errors:
            return format_response(False, "Validation failed", errors=errors, status_code=400)
        
        email = data.get('email')
        user = User.query.filter_by(email=email).first()
        
        if not user:
            # Don't reveal if email exists or not for security
            return format_response(True, "If the email exists, a reset link has been sent")
        
        # Generate reset token
        reset_token = ''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(32))
        
        # In a real application, you would:
        # 1. Store the reset token in database with expiration
        # 2. Send email with reset link
        # For now, we'll just return the token (remove in production)
        
        return format_response(True, "Password reset instructions sent to email", {
            'reset_token': reset_token  # Remove this in production
        })
        
    except Exception as e:
        return format_response(False, f"Password reset failed: {str(e)}", status_code=500)

@auth_bp.route('/reset-password', methods=['POST'])
def reset_password():
    """Reset password with token"""
    try:
        data = request.get_json()
        
        errors = validate_input(data, ['token', 'new_password'])
        if errors:
            return format_response(False, "Validation failed", errors=errors, status_code=400)
        
        token = data.get('token')
        new_password = data.get('new_password')
        
        # In a real application, you would validate the token from database
        # For now, we'll implement a basic validation
        
        if len(new_password) < 6:
            return format_response(False, "Password must be at least 6 characters long", status_code=400)
        
        # This is a placeholder - implement proper token validation
        return format_response(True, "Password reset successful")
        
    except Exception as e:
        return format_response(False, f"Password reset failed: {str(e)}", status_code=500)

@auth_bp.route('/change-password', methods=['POST'])
@token_required
def change_password():
    """Change password for authenticated user"""
    try:
        data = request.get_json()
        current_user_id = get_jwt_identity()
        
        errors = validate_input(data, ['current_password', 'new_password'])
        if errors:
            return format_response(False, "Validation failed", errors=errors, status_code=400)
        
        current_password = data.get('current_password')
        new_password = data.get('new_password')
        
        user = User.query.get(current_user_id)
        if not user:
            return format_response(False, "User not found", status_code=404)
        
        if not user.check_password(current_password):
            return format_response(False, "Current password is incorrect", status_code=400)
        
        if len(new_password) < 6:
            return format_response(False, "New password must be at least 6 characters long", status_code=400)
        
        user.set_password(new_password)
        db.session.commit()
        
        return format_response(True, "Password changed successfully")
        
    except Exception as e:
        db.session.rollback()
        return format_response(False, f"Password change failed: {str(e)}", status_code=500)

@auth_bp.route('/profile', methods=['GET'])
@token_required
def get_profile():
    """Get current user profile"""
    try:
        current_user_id = get_jwt_identity()
        user = User.query.get(current_user_id)
        
        if not user:
            return format_response(False, "User not found", status_code=404)
        
        user_data = {
            'id': user.id,
            'username': user.username,
            'email': user.email,
            'first_name': user.first_name,
            'last_name': user.last_name,
            'middle_name': user.middle_name,
            'phone': user.phone,
            'address': user.address,
            'date_of_birth': user.date_of_birth.isoformat() if user.date_of_birth else None,
            'gender': user.gender.value,
            'role': user.role.value,
            'school_id': user.school_id,
            'school_name': user.school.name if user.school else None,
            'profile_picture_url': user.profile_picture_url,
            'created_at': user.created_at.isoformat()
        }
        
        # Add role-specific data
        if user.role.value == 'student' and user.student_profile:
            student = user.student_profile
            user_data['student_info'] = {
                'student_id': student.student_id,
                'admission_number': student.admission_number,
                'admission_date': student.admission_date.isoformat() if student.admission_date else None,
                'current_class': student.current_class.class_name if student.current_class else None,
                'guardian_name': student.guardian_name,
                'guardian_phone': student.guardian_phone,
                'guardian_email': student.guardian_email
            }
        
        return format_response(True, "Profile retrieved successfully", user_data)
        
    except Exception as e:
        return format_response(False, f"Failed to get profile: {str(e)}", status_code=500)

@auth_bp.route('/profile', methods=['PUT'])
@token_required
def update_profile():
    """Update current user profile"""
    try:
        data = request.get_json()
        current_user_id = get_jwt_identity()
        user = User.query.get(current_user_id)
        
        if not user:
            return format_response(False, "User not found", status_code=404)
        
        # Update allowed fields
        allowed_fields = ['first_name', 'last_name', 'middle_name', 'phone', 'address', 'email']
        
        for field in allowed_fields:
            if field in data:
                setattr(user, field, data[field])
        
        # Handle date of birth
        if 'date_of_birth' in data and data['date_of_birth']:
            try:
                user.date_of_birth = datetime.strptime(data['date_of_birth'], '%Y-%m-%d').date()
            except ValueError:
                return format_response(False, "Invalid date format. Use YYYY-MM-DD", status_code=400)
        
        db.session.commit()
        
        return format_response(True, "Profile updated successfully")
        
    except Exception as e:
        db.session.rollback()
        return format_response(False, f"Profile update failed: {str(e)}", status_code=500)

@auth_bp.route('/verify-token', methods=['POST'])
@token_required
def verify_token():
    """Verify if token is valid"""
    try:
        current_user_id = get_jwt_identity()
        user = User.query.get(current_user_id)
        
        if not user or not user.is_active:
            return format_response(False, "Invalid or inactive user", status_code=401)
        
        return format_response(True, "Token is valid", {
            'user_id': user.id,
            'role': user.role.value,
            'school_id': user.school_id
        })
        
    except Exception as e:
        return format_response(False, f"Token verification failed: {str(e)}", status_code=401)

