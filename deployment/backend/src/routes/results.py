from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity
from datetime import datetime
from decimal import Decimal
from src.models.models import (
    db, Result, Student, Subject, Class, Term, AcademicSession,
    GradingSystem, GradeScale, TermResultSummary, User, ClassSubject
)
from src.utils.security import require_permissions, rate_limit, validate_input, log_security_event
from src.utils.result_computation import (
    ResultComputation, RankingSystem, PerformanceAnalytics, ResultProcessor
)

results_bp = Blueprint('results', __name__)

@results_bp.route('/enter-scores', methods=['POST'])
@jwt_required()
@require_permissions('enter_results')
@rate_limit(max_requests=50, window_minutes=60)
@validate_input(
    class_id={'required': True, 'type': int},
    subject_id={'required': True, 'type': int},
    term_id={'required': True, 'type': int},
    results={'required': True, 'type': list}
)
def enter_scores():
    """Enter or update student scores for a class and subject"""
    try:
        current_user_id = get_jwt_identity()
        data = request.get_json()
        
        # Verify teacher has permission to enter results for this class/subject
        class_subject = ClassSubject.query.filter_by(
            class_id=data['class_id'],
            subject_id=data['subject_id'],
            teacher_id=int(current_user_id),
            is_active=True
        ).first()
        
        if not class_subject:
            return jsonify({
                'success': False,
                'message': 'You are not authorized to enter results for this class and subject'
            }), 403
        
        # Get grading system
        class_obj = Class.query.get(data['class_id'])
        grading_system = GradingSystem.query.filter_by(
            school_id=class_obj.school_id,
            is_default=True
        ).first()
        
        if not grading_system:
            return jsonify({
                'success': False,
                'message': 'No grading system found for this school'
            }), 400
        
        # Process results
        processed = ResultProcessor.batch_process_results(data['results'], grading_system.id)
        
        if not processed['success']:
            return jsonify({
                'success': False,
                'message': 'Some results have errors',
                'data': processed
            }), 400
        
        # Save results to database
        saved_results = []
        for result_data in processed['results']:
            # Check if result already exists
            existing_result = Result.query.filter_by(
                student_id=result_data['student_id'],
                subject_id=data['subject_id'],
                term_id=data['term_id']
            ).first()
            
            if existing_result:
                # Update existing result
                existing_result.ca1_score = result_data['ca1_score']
                existing_result.ca2_score = result_data['ca2_score']
                existing_result.exam_score = result_data['exam_score']
                existing_result.total_score = result_data['total_score']
                existing_result.grade = result_data['grade']
                existing_result.grade_point = result_data['grade_point']
                existing_result.is_submitted = True
                existing_result.submitted_at = datetime.utcnow()
                existing_result.submitted_by = int(current_user_id)
                existing_result.updated_at = datetime.utcnow()
                
                saved_results.append(existing_result)
            else:
                # Create new result
                new_result = Result(
                    student_id=result_data['student_id'],
                    class_id=data['class_id'],
                    subject_id=data['subject_id'],
                    term_id=data['term_id'],
                    ca1_score=result_data['ca1_score'],
                    ca2_score=result_data['ca2_score'],
                    exam_score=result_data['exam_score'],
                    total_score=result_data['total_score'],
                    grade=result_data['grade'],
                    grade_point=result_data['grade_point'],
                    is_submitted=True,
                    submitted_at=datetime.utcnow(),
                    submitted_by=int(current_user_id)
                )
                
                db.session.add(new_result)
                saved_results.append(new_result)
        
        db.session.commit()
        
        # Update term summaries for affected students
        for result_data in processed['results']:
            try:
                ResultProcessor.update_term_summary(result_data['student_id'], data['term_id'])
            except Exception as e:
                current_app.logger.warning(f"Failed to update term summary for student {result_data['student_id']}: {str(e)}")
        
        log_security_event('results_entered', int(current_user_id), {
            'class_id': data['class_id'],
            'subject_id': data['subject_id'],
            'term_id': data['term_id'],
            'results_count': len(saved_results)
        })
        
        return jsonify({
            'success': True,
            'message': f'Successfully saved {len(saved_results)} results',
            'data': {
                'saved_count': len(saved_results),
                'class_id': data['class_id'],
                'subject_id': data['subject_id'],
                'term_id': data['term_id']
            }
        })
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error entering scores: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'Failed to save results'
        }), 500

@results_bp.route('/class-results/<int:class_id>/<int:subject_id>/<int:term_id>', methods=['GET'])
@jwt_required()
@require_permissions('view_student_results', 'view_all_results')
def get_class_results(class_id, subject_id, term_id):
    """Get all results for a specific class, subject, and term"""
    try:
        # Get results with student information
        results_query = db.session.query(
            Result,
            Student,
            User.first_name,
            User.last_name,
            User.gender
        ).join(
            Student, Result.student_id == Student.id
        ).join(
            User, Student.user_id == User.id
        ).filter(
            Result.class_id == class_id,
            Result.subject_id == subject_id,
            Result.term_id == term_id
        ).order_by(User.first_name, User.last_name).all()
        
        results_data = []
        for result, student, first_name, last_name, gender in results_query:
            results_data.append({
                'result_id': result.id,
                'student_id': student.id,
                'student_name': f"{first_name} {last_name}",
                'student_number': student.student_id,
                'gender': gender.value,
                'ca1_score': float(result.ca1_score or 0),
                'ca2_score': float(result.ca2_score or 0),
                'exam_score': float(result.exam_score or 0),
                'total_score': float(result.total_score or 0),
                'grade': result.grade,
                'grade_point': float(result.grade_point or 0),
                'is_submitted': result.is_submitted,
                'teacher_comment': result.teacher_comment,
                'submitted_at': result.submitted_at.isoformat() if result.submitted_at else None
            })
        
        # Calculate class statistics
        if results_data:
            scores = [r['total_score'] for r in results_data if r['is_submitted']]
            class_average = sum(scores) / len(scores) if scores else 0
            highest_score = max(scores) if scores else 0
            lowest_score = min(scores) if scores else 0
        else:
            class_average = highest_score = lowest_score = 0
        
        # Get subject and class information
        subject = Subject.query.get(subject_id)
        class_obj = Class.query.get(class_id)
        term = Term.query.get(term_id)
        
        return jsonify({
            'success': True,
            'data': {
                'results': results_data,
                'statistics': {
                    'total_students': len(results_data),
                    'submitted_count': len([r for r in results_data if r['is_submitted']]),
                    'class_average': round(class_average, 2),
                    'highest_score': highest_score,
                    'lowest_score': lowest_score
                },
                'metadata': {
                    'subject_name': subject.subject_name if subject else None,
                    'class_name': class_obj.class_name if class_obj else None,
                    'term_name': term.term_name if term else None
                }
            }
        })
        
    except Exception as e:
        current_app.logger.error(f"Error getting class results: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'Failed to retrieve class results'
        }), 500

@results_bp.route('/student-results/<int:student_id>/<int:term_id>', methods=['GET'])
@jwt_required()
@require_permissions('view_own_results', 'view_student_results', 'view_all_results')
def get_student_results(student_id, term_id):
    """Get all results for a specific student and term"""
    try:
        current_user_id = get_jwt_identity()
        user = User.query.get(int(current_user_id))
        
        # Check if user can view these results
        if user.role.value == 'student':
            # Students can only view their own results
            student = Student.query.filter_by(user_id=int(current_user_id)).first()
            if not student or student.id != student_id:
                return jsonify({
                    'success': False,
                    'message': 'You can only view your own results'
                }), 403
        
        # Get results with subject information
        results_query = db.session.query(
            Result,
            Subject.subject_name,
            Subject.subject_code,
            Subject.is_core
        ).join(
            Subject, Result.subject_id == Subject.id
        ).filter(
            Result.student_id == student_id,
            Result.term_id == term_id,
            Result.is_submitted == True
        ).order_by(Subject.subject_name).all()
        
        results_data = []
        subject_positions = []
        
        for result, subject_name, subject_code, is_core in results_query:
            # Get subject position
            position_data = RankingSystem.calculate_subject_position(
                student_id, result.subject_id, result.class_id, term_id
            )
            
            results_data.append({
                'subject_id': result.subject_id,
                'subject_name': subject_name,
                'subject_code': subject_code,
                'is_core': is_core,
                'ca1_score': float(result.ca1_score or 0),
                'ca2_score': float(result.ca2_score or 0),
                'exam_score': float(result.exam_score or 0),
                'total_score': float(result.total_score or 0),
                'grade': result.grade,
                'grade_point': float(result.grade_point or 0),
                'teacher_comment': result.teacher_comment,
                'subject_position': position_data.get('position'),
                'total_students': position_data.get('total_students'),
                'class_average': float(ResultComputation.calculate_class_average(
                    result.class_id, result.subject_id, term_id
                ))
            })
            
            subject_positions.append(position_data.get('position', 0))
        
        # Calculate student statistics
        if results_data:
            total_score = sum(r['total_score'] for r in results_data)
            average_score = total_score / len(results_data)
            highest_score = max(r['total_score'] for r in results_data)
            lowest_score = min(r['total_score'] for r in results_data)
            gpa = sum(r['grade_point'] for r in results_data) / len(results_data)
        else:
            average_score = highest_score = lowest_score = gpa = 0
        
        # Get class position
        student = Student.query.get(student_id)
        class_position_data = RankingSystem.get_student_position(
            student_id, student.current_class_id, term_id
        )
        
        # Get term and class information
        term = Term.query.get(term_id)
        class_obj = Class.query.get(student.current_class_id)
        
        return jsonify({
            'success': True,
            'data': {
                'student_id': student_id,
                'results': results_data,
                'summary': {
                    'total_subjects': len(results_data),
                    'total_score': round(total_score, 2) if results_data else 0,
                    'average_score': round(average_score, 2),
                    'highest_score': highest_score,
                    'lowest_score': lowest_score,
                    'gpa': round(gpa, 2),
                    'class_position': class_position_data.get('position'),
                    'total_students': class_position_data.get('total_students')
                },
                'metadata': {
                    'term_name': term.term_name if term else None,
                    'class_name': class_obj.class_name if class_obj else None,
                    'session_name': term.session.session_name if term and term.session else None
                }
            }
        })
        
    except Exception as e:
        current_app.logger.error(f"Error getting student results: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'Failed to retrieve student results'
        }), 500

@results_bp.route('/class-ranking/<int:class_id>/<int:term_id>', methods=['GET'])
@jwt_required()
@require_permissions('view_student_results', 'view_all_results')
def get_class_ranking(class_id, term_id):
    """Get class ranking for a specific term"""
    try:
        ranking = RankingSystem.calculate_class_ranking(class_id, term_id)
        
        # Get class and term information
        class_obj = Class.query.get(class_id)
        term = Term.query.get(term_id)
        
        return jsonify({
            'success': True,
            'data': {
                'ranking': ranking,
                'metadata': {
                    'class_name': class_obj.class_name if class_obj else None,
                    'term_name': term.term_name if term else None,
                    'total_students': len(ranking)
                }
            }
        })
        
    except Exception as e:
        current_app.logger.error(f"Error getting class ranking: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'Failed to retrieve class ranking'
        }), 500

@results_bp.route('/performance-analysis/<int:student_id>/<int:session_id>', methods=['GET'])
@jwt_required()
@require_permissions('view_own_results', 'view_student_results', 'view_all_results')
def get_performance_analysis(student_id, session_id):
    """Get comprehensive performance analysis for a student"""
    try:
        current_user_id = get_jwt_identity()
        user = User.query.get(int(current_user_id))
        
        # Check permissions
        if user.role.value == 'student':
            student = Student.query.filter_by(user_id=int(current_user_id)).first()
            if not student or student.id != student_id:
                return jsonify({
                    'success': False,
                    'message': 'You can only view your own performance analysis'
                }), 403
        
        # Get performance analysis
        analysis = PerformanceAnalytics.analyze_student_performance(student_id, session_id)
        
        # Get student and session information
        student = Student.query.get(student_id)
        session = AcademicSession.query.get(session_id)
        
        if student:
            user_info = User.query.get(student.user_id)
            analysis['student_info'] = {
                'name': f"{user_info.first_name} {user_info.last_name}",
                'student_id': student.student_id,
                'class': student.current_class.class_name if student.current_class else None
            }
        
        if session:
            analysis['session_info'] = {
                'session_name': session.session_name,
                'start_date': session.start_date.isoformat(),
                'end_date': session.end_date.isoformat()
            }
        
        return jsonify({
            'success': True,
            'data': analysis
        })
        
    except Exception as e:
        current_app.logger.error(f"Error getting performance analysis: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'Failed to retrieve performance analysis'
        }), 500

@results_bp.route('/grade-distribution/<int:class_id>/<int:term_id>', methods=['GET'])
@jwt_required()
@require_permissions('view_student_results', 'view_all_results')
def get_grade_distribution(class_id, term_id):
    """Get grade distribution for a class and term"""
    try:
        # Get all results for the class and term
        results = Result.query.filter_by(
            class_id=class_id,
            term_id=term_id,
            is_submitted=True
        ).all()
        
        # Count grades
        grade_counts = {}
        total_results = len(results)
        
        for result in results:
            grade = result.grade or 'F9'
            grade_counts[grade] = grade_counts.get(grade, 0) + 1
        
        # Calculate percentages
        grade_distribution = []
        for grade, count in grade_counts.items():
            percentage = (count / total_results * 100) if total_results > 0 else 0
            grade_distribution.append({
                'grade': grade,
                'count': count,
                'percentage': round(percentage, 1)
            })
        
        # Sort by grade
        grade_order = ['A1', 'B2', 'B3', 'C4', 'C5', 'C6', 'D7', 'E8', 'F9']
        grade_distribution.sort(key=lambda x: grade_order.index(x['grade']) if x['grade'] in grade_order else 999)
        
        # Get class and term information
        class_obj = Class.query.get(class_id)
        term = Term.query.get(term_id)
        
        return jsonify({
            'success': True,
            'data': {
                'distribution': grade_distribution,
                'total_results': total_results,
                'metadata': {
                    'class_name': class_obj.class_name if class_obj else None,
                    'term_name': term.term_name if term else None
                }
            }
        })
        
    except Exception as e:
        current_app.logger.error(f"Error getting grade distribution: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'Failed to retrieve grade distribution'
        }), 500

@results_bp.route('/subject-statistics/<int:subject_id>/<int:class_id>/<int:term_id>', methods=['GET'])
@jwt_required()
@require_permissions('view_student_results', 'view_all_results')
def get_subject_statistics(subject_id, class_id, term_id):
    """Get detailed statistics for a subject"""
    try:
        # Get all results for the subject
        results = Result.query.filter_by(
            subject_id=subject_id,
            class_id=class_id,
            term_id=term_id,
            is_submitted=True
        ).all()
        
        if not results:
            return jsonify({
                'success': True,
                'data': {
                    'statistics': {},
                    'message': 'No results found for this subject'
                }
            })
        
        # Calculate statistics
        total_scores = [float(r.total_score or 0) for r in results]
        ca1_scores = [float(r.ca1_score or 0) for r in results]
        ca2_scores = [float(r.ca2_score or 0) for r in results]
        exam_scores = [float(r.exam_score or 0) for r in results]
        
        statistics = {
            'total_students': len(results),
            'total_score': {
                'average': round(sum(total_scores) / len(total_scores), 2),
                'highest': max(total_scores),
                'lowest': min(total_scores),
                'median': round(sorted(total_scores)[len(total_scores)//2], 2)
            },
            'ca1_score': {
                'average': round(sum(ca1_scores) / len(ca1_scores), 2),
                'highest': max(ca1_scores),
                'lowest': min(ca1_scores)
            },
            'ca2_score': {
                'average': round(sum(ca2_scores) / len(ca2_scores), 2),
                'highest': max(ca2_scores),
                'lowest': min(ca2_scores)
            },
            'exam_score': {
                'average': round(sum(exam_scores) / len(exam_scores), 2),
                'highest': max(exam_scores),
                'lowest': min(exam_scores)
            }
        }
        
        # Grade distribution
        grade_counts = {}
        for result in results:
            grade = result.grade or 'F9'
            grade_counts[grade] = grade_counts.get(grade, 0) + 1
        
        # Get subject information
        subject = Subject.query.get(subject_id)
        class_obj = Class.query.get(class_id)
        term = Term.query.get(term_id)
        
        return jsonify({
            'success': True,
            'data': {
                'statistics': statistics,
                'grade_distribution': grade_counts,
                'metadata': {
                    'subject_name': subject.subject_name if subject else None,
                    'class_name': class_obj.class_name if class_obj else None,
                    'term_name': term.term_name if term else None
                }
            }
        })
        
    except Exception as e:
        current_app.logger.error(f"Error getting subject statistics: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'Failed to retrieve subject statistics'
        }), 500

