from flask import Blueprint, request, jsonify
from flask_jwt_extended import get_jwt_identity
from src.models.models import (
    db, User, Student, Class, Subject, ClassSubject, Result, Term,
    AcademicSession, ClassEnrollment, TermResultSummary, UserRole,
    GradingSystem, GradeScale
)
from src.utils.auth import (
    role_required, format_response, validate_input, PermissionChecker
)
from datetime import datetime
from sqlalchemy import func, and_, or_

teacher_bp = Blueprint('teacher', __name__)

@teacher_bp.route('/dashboard', methods=['GET'])
@role_required(UserRole.TEACHER, UserRole.SCHOOL_ADMIN, UserRole.SUPER_ADMIN)
def get_dashboard(current_user):
    """Get teacher dashboard statistics"""
    try:
        stats = {}
        
        if current_user.role == UserRole.TEACHER:
            # Get teacher's assigned classes and subjects
            teacher_assignments = ClassSubject.query.filter_by(
                teacher_id=current_user.id,
                is_active=True
            ).all()
            
            class_ids = list(set([cs.class_id for cs in teacher_assignments]))
            subject_ids = list(set([cs.subject_id for cs in teacher_assignments]))
            
            stats['assigned_classes'] = len(class_ids)
            stats['assigned_subjects'] = len(subject_ids)
            
            # Count students in assigned classes
            if class_ids:
                stats['total_students'] = ClassEnrollment.query.filter(
                    ClassEnrollment.class_id.in_(class_ids),
                    ClassEnrollment.is_active == True
                ).count()
            else:
                stats['total_students'] = 0
            
            # Get current active term
            active_term = Term.query.join(AcademicSession).filter(
                AcademicSession.school_id == current_user.school_id,
                Term.is_active == True
            ).first()
            
            if active_term:
                stats['current_term'] = {
                    'id': active_term.id,
                    'name': active_term.term_name,
                    'session': active_term.session.session_name
                }
                
                # Count submitted and pending results
                if class_ids and subject_ids:
                    total_results = Result.query.filter(
                        Result.term_id == active_term.id,
                        Result.class_id.in_(class_ids),
                        Result.subject_id.in_(subject_ids)
                    ).count()
                    
                    submitted_results = Result.query.filter(
                        Result.term_id == active_term.id,
                        Result.class_id.in_(class_ids),
                        Result.subject_id.in_(subject_ids),
                        Result.is_submitted == True
                    ).count()
                    
                    stats['results_submitted'] = submitted_results
                    stats['results_pending'] = total_results - submitted_results
            
            # Recent activities
            recent_results = Result.query.filter(
                Result.submitted_by == current_user.id,
                Result.is_submitted == True
            ).order_by(Result.submitted_at.desc()).limit(5).all()
            
            stats['recent_submissions'] = [{
                'student_name': r.student.user.full_name,
                'subject_name': r.subject.subject_name,
                'class_name': r.class_obj.class_name,
                'total_score': float(r.total_score) if r.total_score else 0,
                'submitted_at': r.submitted_at.isoformat() if r.submitted_at else None
            } for r in recent_results]
        
        else:
            # For admin users, show school-wide teacher statistics
            school_id = current_user.school_id
            stats['total_teachers'] = User.query.filter_by(
                school_id=school_id,
                role=UserRole.TEACHER
            ).count()
            
            # Get active term results submission stats
            active_term = Term.query.join(AcademicSession).filter(
                AcademicSession.school_id == school_id,
                Term.is_active == True
            ).first()
            
            if active_term:
                stats['current_term'] = {
                    'id': active_term.id,
                    'name': active_term.term_name,
                    'session': active_term.session.session_name
                }
        
        return format_response(True, "Dashboard data retrieved successfully", stats)
        
    except Exception as e:
        return format_response(False, f"Failed to get dashboard data: {str(e)}", status_code=500)

@teacher_bp.route('/classes', methods=['GET'])
@role_required(UserRole.TEACHER, UserRole.SCHOOL_ADMIN, UserRole.SUPER_ADMIN)
def get_classes(current_user):
    """Get teacher's assigned classes"""
    try:
        if current_user.role == UserRole.TEACHER:
            # Get classes assigned to this teacher
            assignments = ClassSubject.query.filter_by(
                teacher_id=current_user.id,
                is_active=True
            ).all()
            
            class_ids = list(set([cs.class_id for cs in assignments]))
            classes = Class.query.filter(Class.id.in_(class_ids)).all() if class_ids else []
        else:
            # For admin users, get all classes in their school
            classes = Class.query.filter_by(school_id=current_user.school_id).all()
        
        classes_data = []
        for cls in classes:
            # Get subjects taught by this teacher in this class
            if current_user.role == UserRole.TEACHER:
                teacher_subjects = ClassSubject.query.filter_by(
                    class_id=cls.id,
                    teacher_id=current_user.id,
                    is_active=True
                ).all()
            else:
                teacher_subjects = ClassSubject.query.filter_by(
                    class_id=cls.id,
                    is_active=True
                ).all()
            
            # Get current enrollment count
            current_students = ClassEnrollment.query.filter_by(
                class_id=cls.id,
                is_active=True
            ).count()
            
            class_data = {
                'id': cls.id,
                'class_name': cls.class_name,
                'class_level': cls.class_level.value,
                'arm': cls.arm,
                'capacity': cls.capacity,
                'current_students': current_students,
                'subjects': [{
                    'id': cs.subject.id,
                    'name': cs.subject.subject_name,
                    'code': cs.subject.subject_code,
                    'is_core': cs.subject.is_core,
                    'teacher_name': cs.teacher.full_name if cs.teacher else None
                } for cs in teacher_subjects]
            }
            classes_data.append(class_data)
        
        return format_response(True, "Classes retrieved successfully", classes_data)
        
    except Exception as e:
        return format_response(False, f"Failed to get classes: {str(e)}", status_code=500)

@teacher_bp.route('/classes/<int:class_id>/students', methods=['GET'])
@role_required(UserRole.TEACHER, UserRole.SCHOOL_ADMIN, UserRole.SUPER_ADMIN)
def get_class_students(current_user, class_id):
    """Get students in a specific class"""
    try:
        # Verify access to this class
        if current_user.role == UserRole.TEACHER:
            assignment = ClassSubject.query.filter_by(
                class_id=class_id,
                teacher_id=current_user.id,
                is_active=True
            ).first()
            
            if not assignment:
                return format_response(False, "Access denied to this class", status_code=403)
        
        # Get current active session
        active_session = AcademicSession.query.filter_by(
            school_id=current_user.school_id,
            is_active=True
        ).first()
        
        if not active_session:
            return format_response(False, "No active academic session found", status_code=404)
        
        # Get enrolled students
        enrollments = ClassEnrollment.query.filter_by(
            class_id=class_id,
            session_id=active_session.id,
            is_active=True
        ).join(Student).join(User).order_by(User.first_name, User.last_name).all()
        
        students_data = []
        for enrollment in enrollments:
            student = enrollment.student
            user = student.user
            
            student_data = {
                'id': student.id,
                'student_id': student.student_id,
                'admission_number': student.admission_number,
                'full_name': user.full_name,
                'first_name': user.first_name,
                'last_name': user.last_name,
                'gender': user.gender.value,
                'phone': user.phone,
                'guardian_name': student.guardian_name,
                'guardian_phone': student.guardian_phone,
                'enrollment_date': enrollment.enrollment_date.isoformat()
            }
            students_data.append(student_data)
        
        return format_response(True, "Students retrieved successfully", {
            'class_id': class_id,
            'students': students_data,
            'total_students': len(students_data)
        })
        
    except Exception as e:
        return format_response(False, f"Failed to get students: {str(e)}", status_code=500)

@teacher_bp.route('/results', methods=['GET'])
@role_required(UserRole.TEACHER, UserRole.SCHOOL_ADMIN, UserRole.SUPER_ADMIN)
def get_results(current_user):
    """Get results for teacher's classes and subjects"""
    try:
        class_id = request.args.get('class_id', type=int)
        subject_id = request.args.get('subject_id', type=int)
        term_id = request.args.get('term_id', type=int)
        
        # Build query based on user role
        query = Result.query
        
        if current_user.role == UserRole.TEACHER:
            # Teachers can only see results for their assigned subjects
            teacher_assignments = ClassSubject.query.filter_by(
                teacher_id=current_user.id,
                is_active=True
            ).all()
            
            if not teacher_assignments:
                return format_response(True, "No results found", [])
            
            class_subject_pairs = [(cs.class_id, cs.subject_id) for cs in teacher_assignments]
            
            # Filter by teacher's assignments
            conditions = []
            for class_id_filter, subject_id_filter in class_subject_pairs:
                conditions.append(and_(
                    Result.class_id == class_id_filter,
                    Result.subject_id == subject_id_filter
                ))
            
            query = query.filter(or_(*conditions))
        else:
            # Admin users can see all results in their school
            query = query.join(Student).join(User).filter(User.school_id == current_user.school_id)
        
        # Apply additional filters
        if class_id:
            query = query.filter(Result.class_id == class_id)
        if subject_id:
            query = query.filter(Result.subject_id == subject_id)
        if term_id:
            query = query.filter(Result.term_id == term_id)
        else:
            # Default to current active term
            active_term = Term.query.join(AcademicSession).filter(
                AcademicSession.school_id == current_user.school_id,
                Term.is_active == True
            ).first()
            if active_term:
                query = query.filter(Result.term_id == active_term.id)
        
        results = query.order_by(Result.student_id, Result.subject_id).all()
        
        results_data = []
        for result in results:
            result_data = {
                'id': result.id,
                'student_id': result.student.id,
                'student_name': result.student.user.full_name,
                'student_number': result.student.student_id,
                'class_name': result.class_obj.class_name,
                'subject_name': result.subject.subject_name,
                'term_name': result.term.term_name,
                'ca1_score': float(result.ca1_score) if result.ca1_score else 0,
                'ca2_score': float(result.ca2_score) if result.ca2_score else 0,
                'exam_score': float(result.exam_score) if result.exam_score else 0,
                'total_score': float(result.total_score) if result.total_score else 0,
                'grade': result.grade,
                'grade_point': float(result.grade_point) if result.grade_point else 0,
                'subject_position': result.subject_position,
                'class_average': float(result.class_average) if result.class_average else 0,
                'teacher_comment': result.teacher_comment,
                'is_submitted': result.is_submitted,
                'submitted_at': result.submitted_at.isoformat() if result.submitted_at else None
            }
            results_data.append(result_data)
        
        return format_response(True, "Results retrieved successfully", results_data)
        
    except Exception as e:
        return format_response(False, f"Failed to get results: {str(e)}", status_code=500)

@teacher_bp.route('/results/batch', methods=['POST'])
@role_required(UserRole.TEACHER, UserRole.SCHOOL_ADMIN, UserRole.SUPER_ADMIN)
def create_batch_results(current_user):
    """Create or update multiple results at once"""
    try:
        data = request.get_json()
        
        errors = validate_input(data, ['class_id', 'subject_id', 'term_id', 'results'])
        if errors:
            return format_response(False, "Validation failed", errors=errors, status_code=400)
        
        class_id = data['class_id']
        subject_id = data['subject_id']
        term_id = data['term_id']
        results_data = data['results']
        
        # Verify teacher has permission to enter results for this class/subject
        if current_user.role == UserRole.TEACHER:
            if not PermissionChecker.can_enter_results(current_user, class_id, subject_id):
                return format_response(False, "Access denied to enter results for this class/subject", status_code=403)
        
        # Verify term is not locked
        term = Term.query.get(term_id)
        if not term:
            return format_response(False, "Term not found", status_code=404)
        
        if term.is_locked:
            return format_response(False, "Cannot modify results for locked term", status_code=403)
        
        # Get grading system for the school
        grading_system = GradingSystem.query.filter_by(
            school_id=current_user.school_id,
            is_default=True
        ).first()
        
        if not grading_system:
            grading_system = GradingSystem.query.filter_by(
                school_id=current_user.school_id
            ).first()
        
        created_count = 0
        updated_count = 0
        errors_list = []
        
        for result_data in results_data:
            try:
                student_id = result_data.get('student_id')
                ca1_score = result_data.get('ca1_score', 0)
                ca2_score = result_data.get('ca2_score', 0)
                exam_score = result_data.get('exam_score', 0)
                teacher_comment = result_data.get('teacher_comment', '')
                
                if not student_id:
                    errors_list.append(f"Student ID is required for result entry")
                    continue
                
                # Validate scores
                if not (0 <= ca1_score <= 10):
                    errors_list.append(f"CA1 score for student {student_id} must be between 0 and 10")
                    continue
                
                if not (0 <= ca2_score <= 10):
                    errors_list.append(f"CA2 score for student {student_id} must be between 0 and 10")
                    continue
                
                if not (0 <= exam_score <= 80):
                    errors_list.append(f"Exam score for student {student_id} must be between 0 and 80")
                    continue
                
                # Check if result already exists
                existing_result = Result.query.filter_by(
                    student_id=student_id,
                    class_id=class_id,
                    subject_id=subject_id,
                    term_id=term_id
                ).first()
                
                if existing_result:
                    # Update existing result
                    existing_result.ca1_score = ca1_score
                    existing_result.ca2_score = ca2_score
                    existing_result.exam_score = exam_score
                    existing_result.teacher_comment = teacher_comment
                    existing_result.calculate_total_score()
                    
                    # Calculate grade
                    if grading_system:
                        grade_scale = GradeScale.query.filter(
                            GradeScale.grading_system_id == grading_system.id,
                            GradeScale.min_score <= existing_result.total_score,
                            GradeScale.max_score >= existing_result.total_score
                        ).first()
                        
                        if grade_scale:
                            existing_result.grade = grade_scale.grade
                            existing_result.grade_point = grade_scale.grade_point
                    
                    updated_count += 1
                else:
                    # Create new result
                    new_result = Result(
                        student_id=student_id,
                        class_id=class_id,
                        subject_id=subject_id,
                        term_id=term_id,
                        ca1_score=ca1_score,
                        ca2_score=ca2_score,
                        exam_score=exam_score,
                        teacher_comment=teacher_comment
                    )
                    
                    new_result.calculate_total_score()
                    
                    # Calculate grade
                    if grading_system:
                        grade_scale = GradeScale.query.filter(
                            GradeScale.grading_system_id == grading_system.id,
                            GradeScale.min_score <= new_result.total_score,
                            GradeScale.max_score >= new_result.total_score
                        ).first()
                        
                        if grade_scale:
                            new_result.grade = grade_scale.grade
                            new_result.grade_point = grade_scale.grade_point
                    
                    db.session.add(new_result)
                    created_count += 1
                    
            except Exception as e:
                errors_list.append(f"Error processing result for student {student_id}: {str(e)}")
        
        db.session.commit()
        
        response_data = {
            'created': created_count,
            'updated': updated_count,
            'errors': errors_list
        }
        
        message = f"Results processed: {created_count} created, {updated_count} updated"
        if errors_list:
            message += f", {len(errors_list)} errors"
        
        return format_response(True, message, response_data)
        
    except Exception as e:
        db.session.rollback()
        return format_response(False, f"Failed to process results: {str(e)}", status_code=500)

@teacher_bp.route('/results/submit', methods=['POST'])
@role_required(UserRole.TEACHER, UserRole.SCHOOL_ADMIN, UserRole.SUPER_ADMIN)
def submit_results(current_user):
    """Submit results for a class/subject/term"""
    try:
        data = request.get_json()
        
        errors = validate_input(data, ['class_id', 'subject_id', 'term_id'])
        if errors:
            return format_response(False, "Validation failed", errors=errors, status_code=400)
        
        class_id = data['class_id']
        subject_id = data['subject_id']
        term_id = data['term_id']
        
        # Verify teacher has permission
        if current_user.role == UserRole.TEACHER:
            if not PermissionChecker.can_enter_results(current_user, class_id, subject_id):
                return format_response(False, "Access denied", status_code=403)
        
        # Verify term is not locked
        term = Term.query.get(term_id)
        if not term or term.is_locked:
            return format_response(False, "Cannot submit results for locked term", status_code=403)
        
        # Get all results for this class/subject/term
        results = Result.query.filter_by(
            class_id=class_id,
            subject_id=subject_id,
            term_id=term_id
        ).all()
        
        if not results:
            return format_response(False, "No results found to submit", status_code=404)
        
        # Calculate class average and positions
        total_scores = [float(r.total_score) for r in results if r.total_score]
        if total_scores:
            class_average = sum(total_scores) / len(total_scores)
            
            # Sort results by total score for position calculation
            sorted_results = sorted(results, key=lambda x: float(x.total_score or 0), reverse=True)
            
            for position, result in enumerate(sorted_results, 1):
                result.subject_position = position
                result.class_average = class_average
                result.is_submitted = True
                result.submitted_at = datetime.utcnow()
                result.submitted_by = current_user.id
        
        db.session.commit()
        
        return format_response(True, f"Results submitted successfully for {len(results)} students", {
            'submitted_count': len(results),
            'class_average': round(class_average, 2) if total_scores else 0
        })
        
    except Exception as e:
        db.session.rollback()
        return format_response(False, f"Failed to submit results: {str(e)}", status_code=500)

@teacher_bp.route('/students/<int:student_id>/history', methods=['GET'])
@role_required(UserRole.TEACHER, UserRole.SCHOOL_ADMIN, UserRole.SUPER_ADMIN)
def get_student_history(current_user, student_id):
    """Get student's academic history"""
    try:
        # Verify access to this student
        student = Student.query.get(student_id)
        if not student:
            return format_response(False, "Student not found", status_code=404)
        
        if current_user.role == UserRole.TEACHER:
            # Teachers can only view students in their classes
            teacher_classes = [cs.class_id for cs in ClassSubject.query.filter_by(
                teacher_id=current_user.id,
                is_active=True
            ).all()]
            
            student_classes = [e.class_id for e in student.class_enrollments if e.is_active]
            
            if not any(cls in teacher_classes for cls in student_classes):
                return format_response(False, "Access denied to this student", status_code=403)
        
        # Get student's results history
        results = Result.query.filter_by(student_id=student_id).join(Term).join(AcademicSession).order_by(
            AcademicSession.start_date.desc(),
            Term.term_number.desc()
        ).all()
        
        # Group results by term
        terms_data = {}
        for result in results:
            term_key = f"{result.term.session.session_name}_{result.term.term_name}"
            
            if term_key not in terms_data:
                terms_data[term_key] = {
                    'session_name': result.term.session.session_name,
                    'term_name': result.term.term_name,
                    'term_id': result.term.id,
                    'results': []
                }
            
            terms_data[term_key]['results'].append({
                'subject_name': result.subject.subject_name,
                'ca1_score': float(result.ca1_score) if result.ca1_score else 0,
                'ca2_score': float(result.ca2_score) if result.ca2_score else 0,
                'exam_score': float(result.exam_score) if result.exam_score else 0,
                'total_score': float(result.total_score) if result.total_score else 0,
                'grade': result.grade,
                'subject_position': result.subject_position,
                'class_average': float(result.class_average) if result.class_average else 0,
                'teacher_comment': result.teacher_comment
            })
        
        # Get term summaries
        summaries = TermResultSummary.query.filter_by(student_id=student_id).join(Term).join(AcademicSession).order_by(
            AcademicSession.start_date.desc(),
            Term.term_number.desc()
        ).all()
        
        summaries_data = [{
            'session_name': summary.term.session.session_name,
            'term_name': summary.term.term_name,
            'total_subjects': summary.total_subjects,
            'total_score': float(summary.total_score),
            'average_score': float(summary.average_score),
            'class_position': summary.class_position,
            'total_students': summary.total_students,
            'attendance_present': summary.attendance_present,
            'attendance_absent': summary.attendance_absent,
            'promotion_status': summary.promotion_status.value if summary.promotion_status else None
        } for summary in summaries]
        
        return format_response(True, "Student history retrieved successfully", {
            'student': {
                'id': student.id,
                'student_id': student.student_id,
                'full_name': student.user.full_name,
                'current_class': student.current_class.class_name if student.current_class else None
            },
            'terms': list(terms_data.values()),
            'summaries': summaries_data
        })
        
    except Exception as e:
        return format_response(False, f"Failed to get student history: {str(e)}", status_code=500)

@teacher_bp.route('/comments', methods=['POST'])
@role_required(UserRole.TEACHER, UserRole.SCHOOL_ADMIN, UserRole.SUPER_ADMIN)
def add_comments(current_user):
    """Add or update teacher comments for results"""
    try:
        data = request.get_json()
        
        errors = validate_input(data, ['comments'])
        if errors:
            return format_response(False, "Validation failed", errors=errors, status_code=400)
        
        comments_data = data['comments']
        updated_count = 0
        errors_list = []
        
        for comment_data in comments_data:
            try:
                result_id = comment_data.get('result_id')
                comment = comment_data.get('comment', '')
                
                if not result_id:
                    errors_list.append("Result ID is required")
                    continue
                
                result = Result.query.get(result_id)
                if not result:
                    errors_list.append(f"Result {result_id} not found")
                    continue
                
                # Verify teacher has permission to comment on this result
                if current_user.role == UserRole.TEACHER:
                    assignment = ClassSubject.query.filter_by(
                        class_id=result.class_id,
                        subject_id=result.subject_id,
                        teacher_id=current_user.id,
                        is_active=True
                    ).first()
                    
                    if not assignment:
                        errors_list.append(f"Access denied to result {result_id}")
                        continue
                
                result.teacher_comment = comment
                updated_count += 1
                
            except Exception as e:
                errors_list.append(f"Error updating comment for result {result_id}: {str(e)}")
        
        db.session.commit()
        
        return format_response(True, f"Comments updated for {updated_count} results", {
            'updated_count': updated_count,
            'errors': errors_list
        })
        
    except Exception as e:
        db.session.rollback()
        return format_response(False, f"Failed to update comments: {str(e)}", status_code=500)

