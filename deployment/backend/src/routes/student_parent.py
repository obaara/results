from flask import Blueprint, request, jsonify
from flask_jwt_extended import get_jwt_identity
from src.models.models import (
    db, User, Student, Result, Term, AcademicSession, TermResultSummary,
    ParentChild, UserRole, ClassEnrollment
)
from src.utils.auth import (
    role_required, format_response, validate_input, PermissionChecker
)
from datetime import datetime
from sqlalchemy import func, desc

student_bp = Blueprint('student', __name__)
parent_bp = Blueprint('parent', __name__)

# Student Portal Routes
@student_bp.route('/dashboard', methods=['GET'])
@role_required(UserRole.STUDENT)
def get_student_dashboard(current_user):
    """Get student dashboard statistics"""
    try:
        student = current_user.student_profile
        if not student:
            return format_response(False, "Student profile not found", status_code=404)
        
        stats = {}
        
        # Basic student info
        stats['student_info'] = {
            'student_id': student.student_id,
            'admission_number': student.admission_number,
            'full_name': current_user.full_name,
            'current_class': student.current_class.class_name if student.current_class else None,
            'school_name': current_user.school.name
        }
        
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
            
            # Get current term results
            current_results = Result.query.filter_by(
                student_id=student.id,
                term_id=active_term.id
            ).all()
            
            stats['current_term_subjects'] = len(current_results)
            stats['submitted_results'] = len([r for r in current_results if r.is_submitted])
            
            if current_results:
                submitted_results = [r for r in current_results if r.is_submitted and r.total_score]
                if submitted_results:
                    total_score = sum(float(r.total_score) for r in submitted_results)
                    stats['current_average'] = round(total_score / len(submitted_results), 2)
                else:
                    stats['current_average'] = 0
            
            # Get term summary if available
            term_summary = TermResultSummary.query.filter_by(
                student_id=student.id,
                term_id=active_term.id
            ).first()
            
            if term_summary:
                stats['class_position'] = term_summary.class_position
                stats['total_students'] = term_summary.total_students
                stats['attendance'] = {
                    'present': term_summary.attendance_present,
                    'absent': term_summary.attendance_absent
                }
        
        # Recent performance (last 3 terms)
        recent_summaries = TermResultSummary.query.filter_by(
            student_id=student.id
        ).join(Term).join(AcademicSession).order_by(
            AcademicSession.start_date.desc(),
            Term.term_number.desc()
        ).limit(3).all()
        
        stats['recent_performance'] = [{
            'term_name': summary.term.term_name,
            'session_name': summary.term.session.session_name,
            'average_score': float(summary.average_score),
            'class_position': summary.class_position,
            'total_students': summary.total_students
        } for summary in recent_summaries]
        
        return format_response(True, "Dashboard data retrieved successfully", stats)
        
    except Exception as e:
        return format_response(False, f"Failed to get dashboard data: {str(e)}", status_code=500)

@student_bp.route('/results', methods=['GET'])
@role_required(UserRole.STUDENT)
def get_student_results(current_user):
    """Get student's results"""
    try:
        student = current_user.student_profile
        if not student:
            return format_response(False, "Student profile not found", status_code=404)
        
        term_id = request.args.get('term_id', type=int)
        
        # Get results query
        query = Result.query.filter_by(student_id=student.id)
        
        if term_id:
            query = query.filter_by(term_id=term_id)
        else:
            # Default to current active term
            active_term = Term.query.join(AcademicSession).filter(
                AcademicSession.school_id == current_user.school_id,
                Term.is_active == True
            ).first()
            if active_term:
                query = query.filter_by(term_id=active_term.id)
        
        results = query.join(Term).join(AcademicSession).order_by(
            AcademicSession.start_date.desc(),
            Term.term_number.desc(),
            Result.subject_id
        ).all()
        
        results_data = []
        for result in results:
            result_data = {
                'id': result.id,
                'subject_name': result.subject.subject_name,
                'subject_code': result.subject.subject_code,
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
                'term_name': result.term.term_name,
                'session_name': result.term.session.session_name
            }
            results_data.append(result_data)
        
        return format_response(True, "Results retrieved successfully", results_data)
        
    except Exception as e:
        return format_response(False, f"Failed to get results: {str(e)}", status_code=500)

@student_bp.route('/results/<int:term_id>', methods=['GET'])
@role_required(UserRole.STUDENT)
def get_student_term_results(current_user, term_id):
    """Get student's results for a specific term"""
    try:
        student = current_user.student_profile
        if not student:
            return format_response(False, "Student profile not found", status_code=404)
        
        # Get term info
        term = Term.query.get(term_id)
        if not term:
            return format_response(False, "Term not found", status_code=404)
        
        # Get results for the term
        results = Result.query.filter_by(
            student_id=student.id,
            term_id=term_id
        ).all()
        
        # Get term summary
        term_summary = TermResultSummary.query.filter_by(
            student_id=student.id,
            term_id=term_id
        ).first()
        
        results_data = [{
            'subject_name': result.subject.subject_name,
            'subject_code': result.subject.subject_code,
            'ca1_score': float(result.ca1_score) if result.ca1_score else 0,
            'ca2_score': float(result.ca2_score) if result.ca2_score else 0,
            'exam_score': float(result.exam_score) if result.exam_score else 0,
            'total_score': float(result.total_score) if result.total_score else 0,
            'grade': result.grade,
            'subject_position': result.subject_position,
            'class_average': float(result.class_average) if result.class_average else 0,
            'teacher_comment': result.teacher_comment
        } for result in results if result.is_submitted]
        
        summary_data = None
        if term_summary:
            summary_data = {
                'total_subjects': term_summary.total_subjects,
                'total_score': float(term_summary.total_score),
                'average_score': float(term_summary.average_score),
                'class_position': term_summary.class_position,
                'total_students': term_summary.total_students,
                'attendance_present': term_summary.attendance_present,
                'attendance_absent': term_summary.attendance_absent,
                'class_teacher_comment': term_summary.class_teacher_comment,
                'principal_comment': term_summary.principal_comment,
                'promotion_status': term_summary.promotion_status.value if term_summary.promotion_status else None,
                'next_term_begins': term_summary.next_term_begins.isoformat() if term_summary.next_term_begins else None
            }
        
        return format_response(True, "Term results retrieved successfully", {
            'term': {
                'id': term.id,
                'name': term.term_name,
                'session': term.session.session_name
            },
            'results': results_data,
            'summary': summary_data
        })
        
    except Exception as e:
        return format_response(False, f"Failed to get term results: {str(e)}", status_code=500)

@student_bp.route('/results/history', methods=['GET'])
@role_required(UserRole.STUDENT)
def get_student_history(current_user):
    """Get student's complete academic history"""
    try:
        student = current_user.student_profile
        if not student:
            return format_response(False, "Student profile not found", status_code=404)
        
        # Get all term summaries
        summaries = TermResultSummary.query.filter_by(
            student_id=student.id
        ).join(Term).join(AcademicSession).order_by(
            AcademicSession.start_date.desc(),
            Term.term_number.desc()
        ).all()
        
        history_data = []
        for summary in summaries:
            # Get results for this term
            results = Result.query.filter_by(
                student_id=student.id,
                term_id=summary.term_id,
                is_submitted=True
            ).all()
            
            term_data = {
                'term': {
                    'id': summary.term.id,
                    'name': summary.term.term_name,
                    'session': summary.term.session.session_name
                },
                'summary': {
                    'total_subjects': summary.total_subjects,
                    'average_score': float(summary.average_score),
                    'class_position': summary.class_position,
                    'total_students': summary.total_students,
                    'promotion_status': summary.promotion_status.value if summary.promotion_status else None
                },
                'subjects': [{
                    'name': result.subject.subject_name,
                    'total_score': float(result.total_score) if result.total_score else 0,
                    'grade': result.grade,
                    'position': result.subject_position
                } for result in results]
            }
            history_data.append(term_data)
        
        return format_response(True, "Academic history retrieved successfully", history_data)
        
    except Exception as e:
        return format_response(False, f"Failed to get academic history: {str(e)}", status_code=500)

@student_bp.route('/performance-chart', methods=['GET'])
@role_required(UserRole.STUDENT)
def get_performance_chart(current_user):
    """Get student's performance chart data"""
    try:
        student = current_user.student_profile
        if not student:
            return format_response(False, "Student profile not found", status_code=404)
        
        # Get last 6 terms performance
        summaries = TermResultSummary.query.filter_by(
            student_id=student.id
        ).join(Term).join(AcademicSession).order_by(
            AcademicSession.start_date.asc(),
            Term.term_number.asc()
        ).limit(6).all()
        
        chart_data = {
            'labels': [],
            'average_scores': [],
            'positions': [],
            'total_students': []
        }
        
        for summary in summaries:
            chart_data['labels'].append(f"{summary.term.term_name} {summary.term.session.session_name}")
            chart_data['average_scores'].append(float(summary.average_score))
            chart_data['positions'].append(summary.class_position or 0)
            chart_data['total_students'].append(summary.total_students or 0)
        
        return format_response(True, "Performance chart data retrieved successfully", chart_data)
        
    except Exception as e:
        return format_response(False, f"Failed to get performance chart: {str(e)}", status_code=500)

# Parent Portal Routes
@parent_bp.route('/dashboard', methods=['GET'])
@role_required(UserRole.PARENT)
def get_parent_dashboard(current_user):
    """Get parent dashboard with children's information"""
    try:
        # Get parent's children
        parent_children = ParentChild.query.filter_by(parent_id=current_user.id).all()
        
        if not parent_children:
            return format_response(True, "No children found", {
                'children': [],
                'total_children': 0
            })
        
        children_data = []
        for pc in parent_children:
            child = pc.child
            
            # Get current active term
            active_term = Term.query.join(AcademicSession).filter(
                AcademicSession.school_id == current_user.school_id,
                Term.is_active == True
            ).first()
            
            child_info = {
                'id': child.id,
                'student_id': child.student_id,
                'full_name': child.user.full_name,
                'current_class': child.current_class.class_name if child.current_class else None,
                'relationship': pc.relationship
            }
            
            if active_term:
                # Get current term summary
                term_summary = TermResultSummary.query.filter_by(
                    student_id=child.id,
                    term_id=active_term.id
                ).first()
                
                if term_summary:
                    child_info['current_performance'] = {
                        'average_score': float(term_summary.average_score),
                        'class_position': term_summary.class_position,
                        'total_students': term_summary.total_students,
                        'attendance_present': term_summary.attendance_present,
                        'attendance_absent': term_summary.attendance_absent
                    }
            
            children_data.append(child_info)
        
        return format_response(True, "Parent dashboard retrieved successfully", {
            'children': children_data,
            'total_children': len(children_data)
        })
        
    except Exception as e:
        return format_response(False, f"Failed to get parent dashboard: {str(e)}", status_code=500)

@parent_bp.route('/children', methods=['GET'])
@role_required(UserRole.PARENT)
def get_children(current_user):
    """Get list of parent's children"""
    try:
        parent_children = ParentChild.query.filter_by(parent_id=current_user.id).all()
        
        children_data = []
        for pc in parent_children:
            child = pc.child
            child_data = {
                'id': child.id,
                'student_id': child.student_id,
                'admission_number': child.admission_number,
                'full_name': child.user.full_name,
                'current_class': child.current_class.class_name if child.current_class else None,
                'relationship': pc.relationship,
                'guardian_phone': child.guardian_phone,
                'guardian_email': child.guardian_email
            }
            children_data.append(child_data)
        
        return format_response(True, "Children retrieved successfully", children_data)
        
    except Exception as e:
        return format_response(False, f"Failed to get children: {str(e)}", status_code=500)

@parent_bp.route('/children/<int:child_id>/results', methods=['GET'])
@role_required(UserRole.PARENT)
def get_child_results(current_user, child_id):
    """Get specific child's results"""
    try:
        # Verify parent-child relationship
        relationship = ParentChild.query.filter_by(
            parent_id=current_user.id,
            child_id=child_id
        ).first()
        
        if not relationship:
            return format_response(False, "Access denied to this child's records", status_code=403)
        
        term_id = request.args.get('term_id', type=int)
        
        # Get results
        query = Result.query.filter_by(student_id=child_id, is_submitted=True)
        
        if term_id:
            query = query.filter_by(term_id=term_id)
        else:
            # Default to current active term
            active_term = Term.query.join(AcademicSession).filter(
                AcademicSession.school_id == current_user.school_id,
                Term.is_active == True
            ).first()
            if active_term:
                query = query.filter_by(term_id=active_term.id)
        
        results = query.order_by(Result.subject_id).all()
        
        results_data = [{
            'subject_name': result.subject.subject_name,
            'ca1_score': float(result.ca1_score) if result.ca1_score else 0,
            'ca2_score': float(result.ca2_score) if result.ca2_score else 0,
            'exam_score': float(result.exam_score) if result.exam_score else 0,
            'total_score': float(result.total_score) if result.total_score else 0,
            'grade': result.grade,
            'subject_position': result.subject_position,
            'class_average': float(result.class_average) if result.class_average else 0,
            'teacher_comment': result.teacher_comment,
            'term_name': result.term.term_name,
            'session_name': result.term.session.session_name
        } for result in results]
        
        return format_response(True, "Child's results retrieved successfully", results_data)
        
    except Exception as e:
        return format_response(False, f"Failed to get child's results: {str(e)}", status_code=500)

@parent_bp.route('/children/<int:child_id>/results/<int:term_id>', methods=['GET'])
@role_required(UserRole.PARENT)
def get_child_term_results(current_user, child_id, term_id):
    """Get child's results for specific term"""
    try:
        # Verify parent-child relationship
        relationship = ParentChild.query.filter_by(
            parent_id=current_user.id,
            child_id=child_id
        ).first()
        
        if not relationship:
            return format_response(False, "Access denied to this child's records", status_code=403)
        
        # Get term info
        term = Term.query.get(term_id)
        if not term:
            return format_response(False, "Term not found", status_code=404)
        
        # Get results
        results = Result.query.filter_by(
            student_id=child_id,
            term_id=term_id,
            is_submitted=True
        ).all()
        
        # Get term summary
        term_summary = TermResultSummary.query.filter_by(
            student_id=child_id,
            term_id=term_id
        ).first()
        
        child = Student.query.get(child_id)
        
        response_data = {
            'child': {
                'id': child.id,
                'student_id': child.student_id,
                'full_name': child.user.full_name,
                'current_class': child.current_class.class_name if child.current_class else None
            },
            'term': {
                'id': term.id,
                'name': term.term_name,
                'session': term.session.session_name
            },
            'results': [{
                'subject_name': result.subject.subject_name,
                'ca1_score': float(result.ca1_score) if result.ca1_score else 0,
                'ca2_score': float(result.ca2_score) if result.ca2_score else 0,
                'exam_score': float(result.exam_score) if result.exam_score else 0,
                'total_score': float(result.total_score) if result.total_score else 0,
                'grade': result.grade,
                'subject_position': result.subject_position,
                'class_average': float(result.class_average) if result.class_average else 0,
                'teacher_comment': result.teacher_comment
            } for result in results],
            'summary': None
        }
        
        if term_summary:
            response_data['summary'] = {
                'total_subjects': term_summary.total_subjects,
                'average_score': float(term_summary.average_score),
                'class_position': term_summary.class_position,
                'total_students': term_summary.total_students,
                'attendance_present': term_summary.attendance_present,
                'attendance_absent': term_summary.attendance_absent,
                'class_teacher_comment': term_summary.class_teacher_comment,
                'principal_comment': term_summary.principal_comment,
                'promotion_status': term_summary.promotion_status.value if term_summary.promotion_status else None
            }
        
        return format_response(True, "Child's term results retrieved successfully", response_data)
        
    except Exception as e:
        return format_response(False, f"Failed to get child's term results: {str(e)}", status_code=500)

@parent_bp.route('/children/<int:child_id>/performance-chart', methods=['GET'])
@role_required(UserRole.PARENT)
def get_child_performance_chart(current_user, child_id):
    """Get child's performance chart data"""
    try:
        # Verify parent-child relationship
        relationship = ParentChild.query.filter_by(
            parent_id=current_user.id,
            child_id=child_id
        ).first()
        
        if not relationship:
            return format_response(False, "Access denied to this child's records", status_code=403)
        
        # Get performance data
        summaries = TermResultSummary.query.filter_by(
            student_id=child_id
        ).join(Term).join(AcademicSession).order_by(
            AcademicSession.start_date.asc(),
            Term.term_number.asc()
        ).limit(6).all()
        
        chart_data = {
            'labels': [],
            'average_scores': [],
            'positions': []
        }
        
        for summary in summaries:
            chart_data['labels'].append(f"{summary.term.term_name} {summary.term.session.session_name}")
            chart_data['average_scores'].append(float(summary.average_score))
            chart_data['positions'].append(summary.class_position or 0)
        
        return format_response(True, "Child's performance chart retrieved successfully", chart_data)
        
    except Exception as e:
        return format_response(False, f"Failed to get child's performance chart: {str(e)}", status_code=500)

@parent_bp.route('/notifications', methods=['GET'])
@role_required(UserRole.PARENT)
def get_notifications(current_user):
    """Get parent notifications"""
    try:
        # This is a placeholder for notifications system
        # In a real implementation, you would have a notifications table
        notifications = [
            {
                'id': 1,
                'title': 'Results Available',
                'message': 'Your child\'s First Term results are now available',
                'type': 'results',
                'created_at': datetime.utcnow().isoformat(),
                'is_read': False
            }
        ]
        
        return format_response(True, "Notifications retrieved successfully", notifications)
        
    except Exception as e:
        return format_response(False, f"Failed to get notifications: {str(e)}", status_code=500)

