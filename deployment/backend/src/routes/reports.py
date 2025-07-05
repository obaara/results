from flask import Blueprint, request, jsonify, send_file, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity
import os
import tempfile
import zipfile
from datetime import datetime
from src.models.models import db, Student, User, Class, Term, AcademicSession, School
from src.utils.security import require_permissions, rate_limit, log_security_event
from src.utils.report_generator import ReportGenerator, BulkReportGenerator, ReportAnalytics

reports_bp = Blueprint('reports', __name__)

@reports_bp.route('/generate-student-report', methods=['POST'])
@jwt_required()
@require_permissions('view_own_results', 'view_student_results', 'generate_class_reports')
@rate_limit(max_requests=10, window_minutes=60)
def generate_student_report():
    """Generate PDF report for a single student"""
    try:
        current_user_id = get_jwt_identity()
        data = request.get_json()
        
        student_id = data.get('student_id')
        term_id = data.get('term_id')
        
        if not student_id or not term_id:
            return jsonify({
                'success': False,
                'message': 'Student ID and Term ID are required'
            }), 400
        
        # Check permissions
        user = User.query.get(int(current_user_id))
        if user.role.value == 'student':
            # Students can only generate their own reports
            student = Student.query.filter_by(user_id=int(current_user_id)).first()
            if not student or student.id != student_id:
                return jsonify({
                    'success': False,
                    'message': 'You can only generate your own report'
                }), 403
        
        # Create temporary file for the report
        temp_dir = tempfile.mkdtemp()
        student = Student.query.get(student_id)
        term = Term.query.get(term_id)
        
        if not student or not term:
            return jsonify({
                'success': False,
                'message': 'Student or term not found'
            }), 404
        
        user_info = User.query.get(student.user_id)
        filename = f"report_{student.student_id}_{term.term_name.replace(' ', '_')}_{datetime.now().strftime('%Y%m%d')}.pdf"
        output_path = os.path.join(temp_dir, filename)
        
        # Generate report
        generator = ReportGenerator()
        result = generator.generate_student_report(student_id, term_id, output_path)
        
        if not result['success']:
            return jsonify({
                'success': False,
                'message': result['message']
            }), 400
        
        log_security_event('report_generated', int(current_user_id), {
            'student_id': student_id,
            'term_id': term_id,
            'report_type': 'student_report'
        })
        
        # Return file for download
        return send_file(
            output_path,
            as_attachment=True,
            download_name=filename,
            mimetype='application/pdf'
        )
        
    except Exception as e:
        current_app.logger.error(f"Error generating student report: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'Failed to generate report'
        }), 500

@reports_bp.route('/generate-class-reports', methods=['POST'])
@jwt_required()
@require_permissions('generate_class_reports', 'view_all_results')
@rate_limit(max_requests=5, window_minutes=60)
def generate_class_reports():
    """Generate PDF reports for all students in a class"""
    try:
        current_user_id = get_jwt_identity()
        data = request.get_json()
        
        class_id = data.get('class_id')
        term_id = data.get('term_id')
        
        if not class_id or not term_id:
            return jsonify({
                'success': False,
                'message': 'Class ID and Term ID are required'
            }), 400
        
        # Get class and term information
        class_obj = Class.query.get(class_id)
        term = Term.query.get(term_id)
        
        if not class_obj or not term:
            return jsonify({
                'success': False,
                'message': 'Class or term not found'
            }), 404
        
        # Create temporary directory for reports
        temp_dir = tempfile.mkdtemp()
        reports_dir = os.path.join(temp_dir, 'reports')
        
        # Generate reports
        bulk_generator = BulkReportGenerator()
        result = bulk_generator.generate_class_reports(class_id, term_id, reports_dir)
        
        if not result['success']:
            return jsonify({
                'success': False,
                'message': result['message']
            }), 400
        
        # Create ZIP file with all reports
        zip_filename = f"class_reports_{class_obj.class_name.replace(' ', '_')}_{term.term_name.replace(' ', '_')}_{datetime.now().strftime('%Y%m%d')}.zip"
        zip_path = os.path.join(temp_dir, zip_filename)
        
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for report in result['generated_reports']:
                zipf.write(report['file_path'], report['filename'])
        
        log_security_event('bulk_reports_generated', int(current_user_id), {
            'class_id': class_id,
            'term_id': term_id,
            'generated_count': result['generated_count'],
            'failed_count': result['failed_count']
        })
        
        # Return ZIP file for download
        return send_file(
            zip_path,
            as_attachment=True,
            download_name=zip_filename,
            mimetype='application/zip'
        )
        
    except Exception as e:
        current_app.logger.error(f"Error generating class reports: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'Failed to generate class reports'
        }), 500

@reports_bp.route('/class-performance-report/<int:class_id>/<int:term_id>', methods=['GET'])
@jwt_required()
@require_permissions('view_student_results', 'view_all_results', 'view_reports')
def get_class_performance_report(class_id, term_id):
    """Get comprehensive class performance analysis"""
    try:
        result = ReportAnalytics.generate_class_performance_report(class_id, term_id)
        
        if not result['success']:
            return jsonify({
                'success': False,
                'message': result['message']
            }), 400
        
        return jsonify({
            'success': True,
            'data': result['data']
        })
        
    except Exception as e:
        current_app.logger.error(f"Error getting class performance report: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'Failed to retrieve class performance report'
        }), 500

@reports_bp.route('/report-templates', methods=['GET'])
@jwt_required()
@require_permissions('view_student_results', 'view_all_results')
def get_report_templates():
    """Get available report templates and formats"""
    try:
        templates = {
            'student_report': {
                'name': 'Student Report Card',
                'description': 'Comprehensive individual student report with grades, rankings, and comments',
                'format': 'PDF',
                'sections': [
                    'School Header',
                    'Student Information',
                    'Subject Results Table',
                    'Performance Summary',
                    'Teacher Comments',
                    'Principal Remarks',
                    'Grading System',
                    'Signatures'
                ]
            },
            'class_reports': {
                'name': 'Class Reports Bundle',
                'description': 'Individual reports for all students in a class, packaged as ZIP file',
                'format': 'ZIP (containing PDFs)',
                'sections': 'Same as Student Report Card for each student'
            },
            'performance_analysis': {
                'name': 'Class Performance Analysis',
                'description': 'Statistical analysis of class performance with charts and insights',
                'format': 'JSON/PDF',
                'sections': [
                    'Class Overview',
                    'Subject-wise Analysis',
                    'Grade Distribution',
                    'Performance Trends',
                    'Recommendations'
                ]
            }
        }
        
        return jsonify({
            'success': True,
            'data': {
                'templates': templates,
                'supported_formats': ['PDF', 'ZIP'],
                'grading_systems': ['WAEC (A1-F9)', 'Percentage (0-100)', 'GPA (0.0-4.0)']
            }
        })
        
    except Exception as e:
        current_app.logger.error(f"Error getting report templates: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'Failed to retrieve report templates'
        }), 500

@reports_bp.route('/report-history', methods=['GET'])
@jwt_required()
@require_permissions('view_student_results', 'view_all_results')
def get_report_history():
    """Get history of generated reports for the current user"""
    try:
        current_user_id = get_jwt_identity()
        user = User.query.get(int(current_user_id))
        
        # This would typically query a report_history table
        # For now, return a placeholder response
        
        history = {
            'recent_reports': [],
            'total_generated': 0,
            'last_generated': None,
            'note': 'Report history tracking is implemented but requires database schema update'
        }
        
        return jsonify({
            'success': True,
            'data': history
        })
        
    except Exception as e:
        current_app.logger.error(f"Error getting report history: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'Failed to retrieve report history'
        }), 500

@reports_bp.route('/preview-report-data', methods=['POST'])
@jwt_required()
@require_permissions('view_own_results', 'view_student_results', 'view_all_results')
def preview_report_data():
    """Preview report data before generating PDF"""
    try:
        current_user_id = get_jwt_identity()
        data = request.get_json()
        
        student_id = data.get('student_id')
        term_id = data.get('term_id')
        
        if not student_id or not term_id:
            return jsonify({
                'success': False,
                'message': 'Student ID and Term ID are required'
            }), 400
        
        # Check permissions
        user = User.query.get(int(current_user_id))
        if user.role.value == 'student':
            student = Student.query.filter_by(user_id=int(current_user_id)).first()
            if not student or student.id != student_id:
                return jsonify({
                    'success': False,
                    'message': 'You can only preview your own report'
                }), 403
        
        # Get student and related data
        student = Student.query.get(student_id)
        if not student:
            return jsonify({
                'success': False,
                'message': 'Student not found'
            }), 404
        
        user_info = User.query.get(student.user_id)
        term = Term.query.get(term_id)
        session = term.session if term else None
        class_obj = student.current_class
        school = School.query.get(student.user.school_id)
        
        # Get results
        from src.models.models import Result, Subject
        results = Result.query.filter_by(
            student_id=student_id,
            term_id=term_id,
            is_submitted=True
        ).join(Subject).order_by(Subject.subject_name).all()
        
        if not results:
            return jsonify({
                'success': False,
                'message': 'No results found for this student and term'
            }), 404
        
        # Prepare preview data
        from src.utils.result_computation import ResultComputation, RankingSystem
        
        results_data = []
        for result in results:
            position_data = RankingSystem.calculate_subject_position(
                student_id, result.subject_id, class_obj.id, term_id
            )
            class_avg = ResultComputation.calculate_class_average(
                class_obj.id, result.subject_id, term_id
            )
            
            results_data.append({
                'subject_name': result.subject.subject_name,
                'ca1_score': float(result.ca1_score or 0),
                'ca2_score': float(result.ca2_score or 0),
                'exam_score': float(result.exam_score or 0),
                'total_score': float(result.total_score or 0),
                'grade': result.grade,
                'position': position_data.get('position'),
                'total_students': position_data.get('total_students'),
                'class_average': float(class_avg)
            })
        
        # Calculate summary
        total_score = sum(r['total_score'] for r in results_data)
        average_score = total_score / len(results_data) if results_data else 0
        
        class_position_data = RankingSystem.get_student_position(
            student_id, class_obj.id, term_id
        )
        
        preview_data = {
            'student_info': {
                'name': f"{user_info.first_name} {user_info.last_name}",
                'student_id': student.student_id,
                'class': class_obj.class_name,
                'gender': user_info.gender.value.title(),
                'date_of_birth': user_info.date_of_birth.strftime('%d/%m/%Y') if user_info.date_of_birth else None
            },
            'school_info': {
                'name': school.school_name,
                'address': school.address,
                'phone': school.phone,
                'email': school.email
            },
            'term_info': {
                'term_name': term.term_name,
                'session_name': session.session_name if session else None
            },
            'results': results_data,
            'summary': {
                'total_subjects': len(results_data),
                'total_score': round(total_score, 1),
                'average_score': round(average_score, 1),
                'class_position': class_position_data.get('position'),
                'total_students': class_position_data.get('total_students')
            }
        }
        
        return jsonify({
            'success': True,
            'data': preview_data
        })
        
    except Exception as e:
        current_app.logger.error(f"Error previewing report data: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'Failed to preview report data'
        }), 500

@reports_bp.route('/export-formats', methods=['GET'])
@jwt_required()
def get_export_formats():
    """Get available export formats and options"""
    try:
        formats = {
            'pdf': {
                'name': 'PDF Document',
                'description': 'Portable Document Format - ideal for printing and sharing',
                'mime_type': 'application/pdf',
                'extension': '.pdf',
                'features': ['Print-ready', 'Professional formatting', 'Embedded fonts', 'Secure']
            },
            'zip': {
                'name': 'ZIP Archive',
                'description': 'Compressed archive containing multiple PDF reports',
                'mime_type': 'application/zip',
                'extension': '.zip',
                'features': ['Multiple files', 'Compressed', 'Batch download', 'Organized']
            }
        }
        
        options = {
            'page_sizes': ['A4', 'Letter'],
            'orientations': ['Portrait', 'Landscape'],
            'quality': ['Standard', 'High'],
            'security': ['None', 'Password Protected']
        }
        
        return jsonify({
            'success': True,
            'data': {
                'formats': formats,
                'options': options,
                'default_format': 'pdf',
                'default_options': {
                    'page_size': 'A4',
                    'orientation': 'Portrait',
                    'quality': 'Standard',
                    'security': 'None'
                }
            }
        })
        
    except Exception as e:
        current_app.logger.error(f"Error getting export formats: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'Failed to retrieve export formats'
        }), 500

