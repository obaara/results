from functools import wraps
from flask import jsonify, current_app
from flask_jwt_extended import verify_jwt_in_request, get_jwt_identity, get_jwt
from src.models.models import User, TokenBlacklist, UserRole
import datetime

def token_required(f):
    """Decorator to require valid JWT token"""
    @wraps(f)
    def decorated(*args, **kwargs):
        try:
            verify_jwt_in_request()
            return f(*args, **kwargs)
        except Exception as e:
            return jsonify({
                'success': False,
                'message': 'Token is invalid or expired',
                'error': str(e)
            }), 401
    return decorated

def role_required(*allowed_roles):
    """Decorator to require specific user roles"""
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            try:
                verify_jwt_in_request()
                current_user_id = get_jwt_identity()
                user = User.query.get(current_user_id)
                
                if not user:
                    return jsonify({
                        'success': False,
                        'message': 'User not found'
                    }), 404
                
                if not user.is_active:
                    return jsonify({
                        'success': False,
                        'message': 'User account is deactivated'
                    }), 403
                
                user_role = user.role.value if hasattr(user.role, 'value') else user.role
                allowed_role_values = [role.value if hasattr(role, 'value') else role for role in allowed_roles]
                
                if user_role not in allowed_role_values:
                    return jsonify({
                        'success': False,
                        'message': f'Access denied. Required roles: {", ".join(allowed_role_values)}'
                    }), 403
                
                return f(current_user=user, *args, **kwargs)
            except Exception as e:
                return jsonify({
                    'success': False,
                    'message': 'Authorization failed',
                    'error': str(e)
                }), 401
        return decorated
    return decorator

def school_access_required(f):
    """Decorator to ensure user can only access their school's data"""
    @wraps(f)
    def decorated(*args, **kwargs):
        try:
            verify_jwt_in_request()
            current_user_id = get_jwt_identity()
            user = User.query.get(current_user_id)
            
            if not user:
                return jsonify({
                    'success': False,
                    'message': 'User not found'
                }), 404
            
            # Super admin can access all schools
            if user.role == UserRole.SUPER_ADMIN:
                return f(current_user=user, *args, **kwargs)
            
            # For other users, check school access
            school_id = kwargs.get('school_id') or args[0] if args else None
            if school_id and user.school_id != school_id:
                return jsonify({
                    'success': False,
                    'message': 'Access denied to this school'
                }), 403
            
            return f(current_user=user, *args, **kwargs)
        except Exception as e:
            return jsonify({
                'success': False,
                'message': 'School access validation failed',
                'error': str(e)
            }), 401
    return decorated

def get_current_user():
    """Get current authenticated user"""
    try:
        verify_jwt_in_request()
        current_user_id = get_jwt_identity()
        return User.query.get(current_user_id)
    except:
        return None

def is_token_revoked(jwt_header, jwt_payload):
    """Check if JWT token is revoked"""
    jti = jwt_payload['jti']
    token = TokenBlacklist.query.filter_by(jti=jti).first()
    return token is not None and token.revoked

def add_token_to_blacklist(jti, token_type, user_id, expires):
    """Add token to blacklist"""
    from src.models.models import db
    
    blacklisted_token = TokenBlacklist(
        jti=jti,
        token_type=token_type,
        user_id=user_id,
        expires=expires,
        revoked=True
    )
    db.session.add(blacklisted_token)
    db.session.commit()

def cleanup_expired_tokens():
    """Remove expired tokens from blacklist"""
    from src.models.models import db
    
    expired_tokens = TokenBlacklist.query.filter(
        TokenBlacklist.expires < datetime.datetime.utcnow()
    ).all()
    
    for token in expired_tokens:
        db.session.delete(token)
    
    db.session.commit()
    return len(expired_tokens)

class PermissionChecker:
    """Class to handle complex permission checks"""
    
    @staticmethod
    def can_manage_school(user, school_id=None):
        """Check if user can manage school settings"""
        if user.role == UserRole.SUPER_ADMIN:
            return True
        if user.role == UserRole.SCHOOL_ADMIN and (school_id is None or user.school_id == school_id):
            return True
        return False
    
    @staticmethod
    def can_manage_users(user, target_user=None):
        """Check if user can manage other users"""
        if user.role == UserRole.SUPER_ADMIN:
            return True
        if user.role == UserRole.SCHOOL_ADMIN:
            if target_user is None or target_user.school_id == user.school_id:
                # School admin cannot manage other school admins or super admins
                if target_user and target_user.role in [UserRole.SUPER_ADMIN, UserRole.SCHOOL_ADMIN]:
                    return target_user.id == user.id  # Can only manage themselves
                return True
        return False
    
    @staticmethod
    def can_enter_results(user, class_id=None, subject_id=None):
        """Check if user can enter results for specific class/subject"""
        if user.role in [UserRole.SUPER_ADMIN, UserRole.SCHOOL_ADMIN]:
            return True
        if user.role == UserRole.TEACHER:
            if class_id and subject_id:
                from src.models.models import ClassSubject
                assignment = ClassSubject.query.filter_by(
                    class_id=class_id,
                    subject_id=subject_id,
                    teacher_id=user.id,
                    is_active=True
                ).first()
                return assignment is not None
            return True  # General permission, specific check done elsewhere
        return False
    
    @staticmethod
    def can_view_results(user, student_id=None):
        """Check if user can view specific student results"""
        if user.role in [UserRole.SUPER_ADMIN, UserRole.SCHOOL_ADMIN]:
            return True
        if user.role == UserRole.TEACHER:
            # Teachers can view results for their classes
            return True  # Specific filtering done in queries
        if user.role == UserRole.STUDENT:
            if student_id:
                return user.student_profile and user.student_profile.id == student_id
            return True  # Can view own results
        if user.role == UserRole.PARENT:
            if student_id:
                from src.models.models import ParentChild
                relationship = ParentChild.query.filter_by(
                    parent_id=user.id,
                    child_id=student_id
                ).first()
                return relationship is not None
            return True  # Can view children's results
        return False

def validate_input(data, required_fields):
    """Validate required input fields"""
    errors = []
    for field in required_fields:
        if field not in data or not data[field]:
            errors.append(f"{field} is required")
    return errors

def format_response(success=True, message="", data=None, errors=None, status_code=200):
    """Format standardized API response"""
    response = {
        'success': success,
        'message': message,
        'meta': {
            'timestamp': datetime.datetime.utcnow().isoformat() + 'Z',
            'version': '1.0.0'
        }
    }
    
    if data is not None:
        response['data'] = data
    
    if errors:
        response['errors'] = errors
    
    return jsonify(response), status_code

