from flask import Blueprint, request, jsonify
from flask_jwt_extended import get_jwt_identity
from src.models.models import (
    db, School, AcademicSession, Term, Class, Subject, ClassSubject,
    User, Student, GradingSystem, GradeScale, UserRole, SchoolType,
    ClassLevel, Gender
)
from src.utils.auth import (
    role_required, format_response, validate_input, PermissionChecker
)
from datetime import datetime, date
from sqlalchemy import func

admin_bp = Blueprint('admin', __name__)

# Dashboard
@admin_bp.route('/dashboard', methods=['GET'])
@role_required(UserRole.SUPER_ADMIN, UserRole.SCHOOL_ADMIN)
def get_dashboard(current_user):
    """Get admin dashboard statistics"""
    try:
        stats = {}
        
        if current_user.role == UserRole.SUPER_ADMIN:
            # Super admin sees all schools
            stats['total_schools'] = School.query.count()
            stats['total_students'] = Student.query.count()
            stats['total_teachers'] = User.query.filter_by(role=UserRole.TEACHER).count()
            stats['active_sessions'] = AcademicSession.query.filter_by(is_active=True).count()
        else:
            # School admin sees only their school
            school_id = current_user.school_id
            stats['total_classes'] = Class.query.filter_by(school_id=school_id).count()
            stats['total_subjects'] = Subject.query.filter_by(school_id=school_id).count()
            stats['total_students'] = Student.query.join(User).filter(User.school_id == school_id).count()
            stats['total_teachers'] = User.query.filter_by(school_id=school_id, role=UserRole.TEACHER).count()
            
            # Recent activities
            recent_students = Student.query.join(User).filter(
                User.school_id == school_id
            ).order_by(Student.created_at.desc()).limit(5).all()
            
            stats['recent_students'] = [{
                'id': s.id,
                'name': s.user.full_name,
                'student_id': s.student_id,
                'class': s.current_class.class_name if s.current_class else None,
                'created_at': s.created_at.isoformat()
            } for s in recent_students]
        
        return format_response(True, "Dashboard data retrieved successfully", stats)
        
    except Exception as e:
        return format_response(False, f"Failed to get dashboard data: {str(e)}", status_code=500)

# School Management
@admin_bp.route('/schools', methods=['GET'])
@role_required(UserRole.SUPER_ADMIN)
def get_schools(current_user):
    """Get all schools (Super admin only)"""
    try:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        
        schools = School.query.paginate(
            page=page, per_page=per_page, error_out=False
        )
        
        schools_data = [{
            'id': school.id,
            'name': school.name,
            'address': school.address,
            'phone': school.phone,
            'email': school.email,
            'school_type': school.school_type.value,
            'principal_name': school.principal_name,
            'created_at': school.created_at.isoformat()
        } for school in schools.items]
        
        return format_response(True, "Schools retrieved successfully", {
            'schools': schools_data,
            'pagination': {
                'page': schools.page,
                'pages': schools.pages,
                'per_page': schools.per_page,
                'total': schools.total
            }
        })
        
    except Exception as e:
        return format_response(False, f"Failed to get schools: {str(e)}", status_code=500)

@admin_bp.route('/schools', methods=['POST'])
@role_required(UserRole.SUPER_ADMIN)
def create_school(current_user):
    """Create new school"""
    try:
        data = request.get_json()
        
        errors = validate_input(data, ['name', 'school_type'])
        if errors:
            return format_response(False, "Validation failed", errors=errors, status_code=400)
        
        # Validate school type
        try:
            school_type = SchoolType(data['school_type'])
        except ValueError:
            return format_response(False, "Invalid school type", status_code=400)
        
        school = School(
            name=data['name'],
            address=data.get('address'),
            phone=data.get('phone'),
            email=data.get('email'),
            motto=data.get('motto'),
            principal_name=data.get('principal_name'),
            school_type=school_type
        )
        
        db.session.add(school)
        db.session.commit()
        
        return format_response(True, "School created successfully", {
            'id': school.id,
            'name': school.name
        })
        
    except Exception as e:
        db.session.rollback()
        return format_response(False, f"Failed to create school: {str(e)}", status_code=500)

# Academic Session Management
@admin_bp.route('/sessions', methods=['GET'])
@role_required(UserRole.SUPER_ADMIN, UserRole.SCHOOL_ADMIN)
def get_sessions(current_user):
    """Get academic sessions"""
    try:
        school_id = current_user.school_id if current_user.role != UserRole.SUPER_ADMIN else request.args.get('school_id', type=int)
        
        query = AcademicSession.query
        if school_id:
            query = query.filter_by(school_id=school_id)
        
        sessions = query.order_by(AcademicSession.start_date.desc()).all()
        
        sessions_data = [{
            'id': session.id,
            'session_name': session.session_name,
            'start_date': session.start_date.isoformat(),
            'end_date': session.end_date.isoformat(),
            'is_active': session.is_active,
            'school_name': session.school.name,
            'terms_count': len(session.terms)
        } for session in sessions]
        
        return format_response(True, "Sessions retrieved successfully", sessions_data)
        
    except Exception as e:
        return format_response(False, f"Failed to get sessions: {str(e)}", status_code=500)

@admin_bp.route('/sessions', methods=['POST'])
@role_required(UserRole.SUPER_ADMIN, UserRole.SCHOOL_ADMIN)
def create_session(current_user):
    """Create new academic session"""
    try:
        data = request.get_json()
        
        errors = validate_input(data, ['session_name', 'start_date', 'end_date'])
        if errors:
            return format_response(False, "Validation failed", errors=errors, status_code=400)
        
        school_id = current_user.school_id if current_user.role != UserRole.SUPER_ADMIN else data.get('school_id')
        if not school_id:
            return format_response(False, "School ID is required", status_code=400)
        
        # Parse dates
        try:
            start_date = datetime.strptime(data['start_date'], '%Y-%m-%d').date()
            end_date = datetime.strptime(data['end_date'], '%Y-%m-%d').date()
        except ValueError:
            return format_response(False, "Invalid date format. Use YYYY-MM-DD", status_code=400)
        
        if start_date >= end_date:
            return format_response(False, "Start date must be before end date", status_code=400)
        
        # Check for duplicate session name in the same school
        existing = AcademicSession.query.filter_by(
            school_id=school_id,
            session_name=data['session_name']
        ).first()
        
        if existing:
            return format_response(False, "Session with this name already exists", status_code=400)
        
        # If this is set as active, deactivate other sessions
        if data.get('is_active', False):
            AcademicSession.query.filter_by(school_id=school_id, is_active=True).update({'is_active': False})
        
        session = AcademicSession(
            school_id=school_id,
            session_name=data['session_name'],
            start_date=start_date,
            end_date=end_date,
            is_active=data.get('is_active', False)
        )
        
        db.session.add(session)
        db.session.commit()
        
        return format_response(True, "Academic session created successfully", {
            'id': session.id,
            'session_name': session.session_name
        })
        
    except Exception as e:
        db.session.rollback()
        return format_response(False, f"Failed to create session: {str(e)}", status_code=500)

# Term Management
@admin_bp.route('/terms', methods=['GET'])
@role_required(UserRole.SUPER_ADMIN, UserRole.SCHOOL_ADMIN)
def get_terms(current_user):
    """Get terms"""
    try:
        session_id = request.args.get('session_id', type=int)
        
        query = Term.query
        if session_id:
            query = query.filter_by(session_id=session_id)
        elif current_user.role != UserRole.SUPER_ADMIN:
            # Filter by school for school admins
            query = query.join(AcademicSession).filter(AcademicSession.school_id == current_user.school_id)
        
        terms = query.order_by(Term.term_number).all()
        
        terms_data = [{
            'id': term.id,
            'term_number': term.term_number,
            'term_name': term.term_name,
            'start_date': term.start_date.isoformat(),
            'end_date': term.end_date.isoformat(),
            'is_active': term.is_active,
            'is_locked': term.is_locked,
            'session_name': term.session.session_name,
            'school_name': term.session.school.name
        } for term in terms]
        
        return format_response(True, "Terms retrieved successfully", terms_data)
        
    except Exception as e:
        return format_response(False, f"Failed to get terms: {str(e)}", status_code=500)

@admin_bp.route('/terms', methods=['POST'])
@role_required(UserRole.SUPER_ADMIN, UserRole.SCHOOL_ADMIN)
def create_term(current_user):
    """Create new term"""
    try:
        data = request.get_json()
        
        errors = validate_input(data, ['session_id', 'term_number', 'term_name', 'start_date', 'end_date'])
        if errors:
            return format_response(False, "Validation failed", errors=errors, status_code=400)
        
        session_id = data['session_id']
        session = AcademicSession.query.get(session_id)
        
        if not session:
            return format_response(False, "Academic session not found", status_code=404)
        
        # Check permission for school admin
        if current_user.role == UserRole.SCHOOL_ADMIN and session.school_id != current_user.school_id:
            return format_response(False, "Access denied to this session", status_code=403)
        
        # Validate term number
        if data['term_number'] not in [1, 2, 3]:
            return format_response(False, "Term number must be 1, 2, or 3", status_code=400)
        
        # Parse dates
        try:
            start_date = datetime.strptime(data['start_date'], '%Y-%m-%d').date()
            end_date = datetime.strptime(data['end_date'], '%Y-%m-%d').date()
        except ValueError:
            return format_response(False, "Invalid date format. Use YYYY-MM-DD", status_code=400)
        
        # Check for duplicate term in the same session
        existing = Term.query.filter_by(
            session_id=session_id,
            term_number=data['term_number']
        ).first()
        
        if existing:
            return format_response(False, "Term already exists for this session", status_code=400)
        
        # If this is set as active, deactivate other terms in the same session
        if data.get('is_active', False):
            Term.query.filter_by(session_id=session_id, is_active=True).update({'is_active': False})
        
        term = Term(
            session_id=session_id,
            term_number=data['term_number'],
            term_name=data['term_name'],
            start_date=start_date,
            end_date=end_date,
            is_active=data.get('is_active', False),
            is_locked=data.get('is_locked', False)
        )
        
        db.session.add(term)
        db.session.commit()
        
        return format_response(True, "Term created successfully", {
            'id': term.id,
            'term_name': term.term_name
        })
        
    except Exception as e:
        db.session.rollback()
        return format_response(False, f"Failed to create term: {str(e)}", status_code=500)

# Class Management
@admin_bp.route('/classes', methods=['GET'])
@role_required(UserRole.SUPER_ADMIN, UserRole.SCHOOL_ADMIN)
def get_classes(current_user):
    """Get classes"""
    try:
        school_id = current_user.school_id if current_user.role != UserRole.SUPER_ADMIN else request.args.get('school_id', type=int)
        
        query = Class.query
        if school_id:
            query = query.filter_by(school_id=school_id)
        
        classes = query.order_by(Class.class_level, Class.class_number, Class.arm).all()
        
        classes_data = [{
            'id': cls.id,
            'class_name': cls.class_name,
            'class_level': cls.class_level.value,
            'class_number': cls.class_number,
            'arm': cls.arm,
            'capacity': cls.capacity,
            'current_students': len([e for e in cls.class_enrollments if e.is_active]),
            'subjects_count': len([cs for cs in cls.class_subjects if cs.is_active]),
            'school_name': cls.school.name
        } for cls in classes]
        
        return format_response(True, "Classes retrieved successfully", classes_data)
        
    except Exception as e:
        return format_response(False, f"Failed to get classes: {str(e)}", status_code=500)

@admin_bp.route('/classes', methods=['POST'])
@role_required(UserRole.SUPER_ADMIN, UserRole.SCHOOL_ADMIN)
def create_class(current_user):
    """Create new class"""
    try:
        data = request.get_json()
        
        errors = validate_input(data, ['class_name', 'class_level', 'class_number'])
        if errors:
            return format_response(False, "Validation failed", errors=errors, status_code=400)
        
        school_id = current_user.school_id if current_user.role != UserRole.SUPER_ADMIN else data.get('school_id')
        if not school_id:
            return format_response(False, "School ID is required", status_code=400)
        
        # Validate class level
        try:
            class_level = ClassLevel(data['class_level'])
        except ValueError:
            return format_response(False, "Invalid class level", status_code=400)
        
        # Check for duplicate class
        existing = Class.query.filter_by(
            school_id=school_id,
            class_level=class_level,
            class_number=data['class_number'],
            arm=data.get('arm')
        ).first()
        
        if existing:
            return format_response(False, "Class already exists", status_code=400)
        
        class_obj = Class(
            school_id=school_id,
            class_name=data['class_name'],
            class_level=class_level,
            class_number=data['class_number'],
            arm=data.get('arm'),
            capacity=data.get('capacity', 40)
        )
        
        db.session.add(class_obj)
        db.session.commit()
        
        return format_response(True, "Class created successfully", {
            'id': class_obj.id,
            'class_name': class_obj.class_name
        })
        
    except Exception as e:
        db.session.rollback()
        return format_response(False, f"Failed to create class: {str(e)}", status_code=500)

# Subject Management
@admin_bp.route('/subjects', methods=['GET'])
@role_required(UserRole.SUPER_ADMIN, UserRole.SCHOOL_ADMIN)
def get_subjects(current_user):
    """Get subjects"""
    try:
        school_id = current_user.school_id if current_user.role != UserRole.SUPER_ADMIN else request.args.get('school_id', type=int)
        class_level = request.args.get('class_level')
        
        query = Subject.query
        if school_id:
            query = query.filter_by(school_id=school_id)
        if class_level:
            try:
                level_enum = ClassLevel(class_level)
                query = query.filter_by(class_level=level_enum)
            except ValueError:
                return format_response(False, "Invalid class level", status_code=400)
        
        subjects = query.order_by(Subject.subject_name).all()
        
        subjects_data = [{
            'id': subject.id,
            'subject_name': subject.subject_name,
            'subject_code': subject.subject_code,
            'is_core': subject.is_core,
            'class_level': subject.class_level.value,
            'school_name': subject.school.name,
            'classes_count': len([cs for cs in subject.class_subjects if cs.is_active])
        } for subject in subjects]
        
        return format_response(True, "Subjects retrieved successfully", subjects_data)
        
    except Exception as e:
        return format_response(False, f"Failed to get subjects: {str(e)}", status_code=500)

@admin_bp.route('/subjects', methods=['POST'])
@role_required(UserRole.SUPER_ADMIN, UserRole.SCHOOL_ADMIN)
def create_subject(current_user):
    """Create new subject"""
    try:
        data = request.get_json()
        
        errors = validate_input(data, ['subject_name', 'class_level'])
        if errors:
            return format_response(False, "Validation failed", errors=errors, status_code=400)
        
        school_id = current_user.school_id if current_user.role != UserRole.SUPER_ADMIN else data.get('school_id')
        if not school_id:
            return format_response(False, "School ID is required", status_code=400)
        
        # Validate class level
        try:
            class_level = ClassLevel(data['class_level'])
        except ValueError:
            return format_response(False, "Invalid class level", status_code=400)
        
        # Check for duplicate subject
        existing = Subject.query.filter_by(
            school_id=school_id,
            subject_name=data['subject_name'],
            class_level=class_level
        ).first()
        
        if existing:
            return format_response(False, "Subject already exists for this class level", status_code=400)
        
        subject = Subject(
            school_id=school_id,
            subject_name=data['subject_name'],
            subject_code=data.get('subject_code'),
            is_core=data.get('is_core', True),
            class_level=class_level
        )
        
        db.session.add(subject)
        db.session.commit()
        
        return format_response(True, "Subject created successfully", {
            'id': subject.id,
            'subject_name': subject.subject_name
        })
        
    except Exception as e:
        db.session.rollback()
        return format_response(False, f"Failed to create subject: {str(e)}", status_code=500)

# User Management
@admin_bp.route('/users', methods=['GET'])
@role_required(UserRole.SUPER_ADMIN, UserRole.SCHOOL_ADMIN)
def get_users(current_user):
    """Get users"""
    try:
        school_id = current_user.school_id if current_user.role != UserRole.SUPER_ADMIN else request.args.get('school_id', type=int)
        role = request.args.get('role')
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        
        query = User.query
        if school_id:
            query = query.filter_by(school_id=school_id)
        if role:
            try:
                role_enum = UserRole(role)
                query = query.filter_by(role=role_enum)
            except ValueError:
                return format_response(False, "Invalid role", status_code=400)
        
        users = query.order_by(User.created_at.desc()).paginate(
            page=page, per_page=per_page, error_out=False
        )
        
        users_data = [{
            'id': user.id,
            'username': user.username,
            'email': user.email,
            'full_name': user.full_name,
            'phone': user.phone,
            'role': user.role.value,
            'is_active': user.is_active,
            'school_name': user.school.name,
            'created_at': user.created_at.isoformat()
        } for user in users.items]
        
        return format_response(True, "Users retrieved successfully", {
            'users': users_data,
            'pagination': {
                'page': users.page,
                'pages': users.pages,
                'per_page': users.per_page,
                'total': users.total
            }
        })
        
    except Exception as e:
        return format_response(False, f"Failed to get users: {str(e)}", status_code=500)

@admin_bp.route('/users', methods=['POST'])
@role_required(UserRole.SUPER_ADMIN, UserRole.SCHOOL_ADMIN)
def create_user(current_user):
    """Create new user"""
    try:
        data = request.get_json()
        
        errors = validate_input(data, ['username', 'password', 'first_name', 'last_name', 'gender', 'role'])
        if errors:
            return format_response(False, "Validation failed", errors=errors, status_code=400)
        
        school_id = current_user.school_id if current_user.role != UserRole.SUPER_ADMIN else data.get('school_id')
        if not school_id:
            return format_response(False, "School ID is required", status_code=400)
        
        # Validate role and permissions
        try:
            role = UserRole(data['role'])
        except ValueError:
            return format_response(False, "Invalid role", status_code=400)
        
        # Check if current user can create this role
        if not PermissionChecker.can_manage_users(current_user):
            return format_response(False, "Access denied", status_code=403)
        
        # School admin cannot create super admin or other school admins
        if current_user.role == UserRole.SCHOOL_ADMIN and role in [UserRole.SUPER_ADMIN, UserRole.SCHOOL_ADMIN]:
            return format_response(False, "Cannot create admin users", status_code=403)
        
        # Validate gender
        try:
            gender = Gender(data['gender'])
        except ValueError:
            return format_response(False, "Invalid gender", status_code=400)
        
        # Check for duplicate username
        if User.query.filter_by(username=data['username']).first():
            return format_response(False, "Username already exists", status_code=400)
        
        # Check for duplicate email if provided
        if data.get('email') and User.query.filter_by(email=data['email']).first():
            return format_response(False, "Email already exists", status_code=400)
        
        user = User(
            school_id=school_id,
            username=data['username'],
            email=data.get('email'),
            first_name=data['first_name'],
            last_name=data['last_name'],
            middle_name=data.get('middle_name'),
            phone=data.get('phone'),
            address=data.get('address'),
            gender=gender,
            role=role,
            is_active=data.get('is_active', True)
        )
        
        user.set_password(data['password'])
        
        # Handle date of birth
        if data.get('date_of_birth'):
            try:
                user.date_of_birth = datetime.strptime(data['date_of_birth'], '%Y-%m-%d').date()
            except ValueError:
                return format_response(False, "Invalid date format. Use YYYY-MM-DD", status_code=400)
        
        db.session.add(user)
        db.session.flush()  # Get the user ID
        
        # Create student profile if role is student
        if role == UserRole.STUDENT:
            student_data = data.get('student_info', {})
            student = Student(
                user_id=user.id,
                student_id=student_data.get('student_id') or f"STU{user.id:06d}",
                admission_number=student_data.get('admission_number'),
                guardian_name=student_data.get('guardian_name'),
                guardian_phone=student_data.get('guardian_phone'),
                guardian_email=student_data.get('guardian_email'),
                guardian_address=student_data.get('guardian_address')
            )
            
            if student_data.get('admission_date'):
                try:
                    student.admission_date = datetime.strptime(student_data['admission_date'], '%Y-%m-%d').date()
                except ValueError:
                    pass
            
            db.session.add(student)
        
        db.session.commit()
        
        return format_response(True, "User created successfully", {
            'id': user.id,
            'username': user.username,
            'role': user.role.value
        })
        
    except Exception as e:
        db.session.rollback()
        return format_response(False, f"Failed to create user: {str(e)}", status_code=500)

# Grading System Management
@admin_bp.route('/grading-systems', methods=['GET'])
@role_required(UserRole.SUPER_ADMIN, UserRole.SCHOOL_ADMIN)
def get_grading_systems(current_user):
    """Get grading systems"""
    try:
        school_id = current_user.school_id if current_user.role != UserRole.SUPER_ADMIN else request.args.get('school_id', type=int)
        
        query = GradingSystem.query
        if school_id:
            query = query.filter_by(school_id=school_id)
        
        systems = query.all()
        
        systems_data = [{
            'id': system.id,
            'system_name': system.system_name,
            'is_default': system.is_default,
            'school_name': system.school.name,
            'grade_scales': [{
                'grade': scale.grade,
                'min_score': float(scale.min_score),
                'max_score': float(scale.max_score),
                'grade_point': float(scale.grade_point),
                'description': scale.description
            } for scale in system.grade_scales]
        } for system in systems]
        
        return format_response(True, "Grading systems retrieved successfully", systems_data)
        
    except Exception as e:
        return format_response(False, f"Failed to get grading systems: {str(e)}", status_code=500)

@admin_bp.route('/grading-systems', methods=['POST'])
@role_required(UserRole.SUPER_ADMIN, UserRole.SCHOOL_ADMIN)
def create_grading_system(current_user):
    """Create new grading system"""
    try:
        data = request.get_json()
        
        errors = validate_input(data, ['system_name', 'grade_scales'])
        if errors:
            return format_response(False, "Validation failed", errors=errors, status_code=400)
        
        school_id = current_user.school_id if current_user.role != UserRole.SUPER_ADMIN else data.get('school_id')
        if not school_id:
            return format_response(False, "School ID is required", status_code=400)
        
        # If this is set as default, remove default from others
        if data.get('is_default', False):
            GradingSystem.query.filter_by(school_id=school_id, is_default=True).update({'is_default': False})
        
        grading_system = GradingSystem(
            school_id=school_id,
            system_name=data['system_name'],
            is_default=data.get('is_default', False)
        )
        
        db.session.add(grading_system)
        db.session.flush()
        
        # Add grade scales
        for scale_data in data['grade_scales']:
            scale = GradeScale(
                grading_system_id=grading_system.id,
                grade=scale_data['grade'],
                min_score=scale_data['min_score'],
                max_score=scale_data['max_score'],
                grade_point=scale_data['grade_point'],
                description=scale_data.get('description')
            )
            db.session.add(scale)
        
        db.session.commit()
        
        return format_response(True, "Grading system created successfully", {
            'id': grading_system.id,
            'system_name': grading_system.system_name
        })
        
    except Exception as e:
        db.session.rollback()
        return format_response(False, f"Failed to create grading system: {str(e)}", status_code=500)

