"""
Report sheet generation utilities for the Nigerian School Result Portal
Handles PDF generation, report formatting, and document templates
"""

import os
import io
from datetime import datetime
from decimal import Decimal
from typing import Dict, List, Optional
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch, cm
from reportlab.platypus import (
    SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, 
    Image, PageBreak, Frame, PageTemplate
)
from reportlab.platypus.tableofcontents import TableOfContents
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT, TA_JUSTIFY
from reportlab.pdfgen import canvas
from reportlab.graphics.shapes import Drawing, Rect
from reportlab.graphics.charts.barcharts import VerticalBarChart
from reportlab.graphics.charts.linecharts import HorizontalLineChart

from src.models.models import (
    db, Student, User, School, Class, Term, AcademicSession,
    Result, Subject, TermResultSummary
)
from src.utils.result_computation import ResultComputation, RankingSystem

class ReportCardTemplate:
    """Nigerian school report card template generator"""
    
    def __init__(self, school_id: int):
        self.school = School.query.get(school_id)
        self.styles = getSampleStyleSheet()
        self.setup_custom_styles()
        
    def setup_custom_styles(self):
        """Setup custom paragraph styles for the report"""
        # School name style
        self.styles.add(ParagraphStyle(
            name='SchoolName',
            parent=self.styles['Title'],
            fontSize=16,
            spaceAfter=6,
            alignment=TA_CENTER,
            textColor=colors.darkblue,
            fontName='Helvetica-Bold'
        ))
        
        # School address style
        self.styles.add(ParagraphStyle(
            name='SchoolAddress',
            parent=self.styles['Normal'],
            fontSize=10,
            spaceAfter=12,
            alignment=TA_CENTER,
            textColor=colors.grey
        ))
        
        # Report title style
        self.styles.add(ParagraphStyle(
            name='ReportTitle',
            parent=self.styles['Heading1'],
            fontSize=14,
            spaceAfter=12,
            alignment=TA_CENTER,
            textColor=colors.darkred,
            fontName='Helvetica-Bold'
        ))
        
        # Student info style
        self.styles.add(ParagraphStyle(
            name='StudentInfo',
            parent=self.styles['Normal'],
            fontSize=10,
            spaceAfter=6,
            alignment=TA_LEFT
        ))
        
        # Comment style
        self.styles.add(ParagraphStyle(
            name='Comment',
            parent=self.styles['Normal'],
            fontSize=9,
            spaceAfter=6,
            alignment=TA_JUSTIFY,
            leftIndent=12,
            rightIndent=12
        ))
        
        # Signature style
        self.styles.add(ParagraphStyle(
            name='Signature',
            parent=self.styles['Normal'],
            fontSize=9,
            spaceAfter=6,
            alignment=TA_CENTER
        ))

class ReportGenerator:
    """Main report generation engine"""
    
    def __init__(self):
        self.page_width = A4[0]
        self.page_height = A4[1]
        self.margin = 0.75 * inch
        
    def generate_student_report(self, student_id: int, term_id: int, output_path: str) -> Dict:
        """Generate comprehensive student report card"""
        try:
            # Get student and related data
            student = Student.query.get(student_id)
            if not student:
                return {'success': False, 'message': 'Student not found'}
            
            user = User.query.get(student.user_id)
            term = Term.query.get(term_id)
            session = term.session if term else None
            class_obj = student.current_class
            school = School.query.get(student.user.school_id)
            
            # Get results
            results = Result.query.filter_by(
                student_id=student_id,
                term_id=term_id,
                is_submitted=True
            ).join(Subject).order_by(Subject.subject_name).all()
            
            if not results:
                return {'success': False, 'message': 'No results found for this student and term'}
            
            # Create PDF document
            doc = SimpleDocTemplate(
                output_path,
                pagesize=A4,
                rightMargin=self.margin,
                leftMargin=self.margin,
                topMargin=self.margin,
                bottomMargin=self.margin
            )
            
            # Build report content
            story = []
            template = ReportCardTemplate(school.id)
            
            # Add header
            story.extend(self._build_header(template, school, term, session))
            
            # Add student information
            story.extend(self._build_student_info(template, student, user, class_obj))
            
            # Add results table
            story.extend(self._build_results_table(template, results, student_id, term_id, class_obj.id))
            
            # Add summary and statistics
            story.extend(self._build_summary_section(template, results, student_id, term_id, class_obj.id))
            
            # Add comments and remarks
            story.extend(self._build_comments_section(template, results, student_id, term_id))
            
            # Add signatures section
            story.extend(self._build_signatures_section(template))
            
            # Build PDF
            doc.build(story)
            
            return {
                'success': True,
                'message': 'Report generated successfully',
                'file_path': output_path,
                'student_name': f"{user.first_name} {user.last_name}",
                'term_name': term.term_name,
                'session_name': session.session_name if session else None
            }
            
        except Exception as e:
            return {'success': False, 'message': f'Error generating report: {str(e)}'}
    
    def _build_header(self, template, school, term, session):
        """Build report header with school information"""
        story = []
        
        # School logo placeholder (if available)
        if school.logo_url:
            try:
                # In production, this would load the actual logo
                # For now, we'll add a placeholder
                story.append(Spacer(1, 12))
            except:
                pass
        
        # School name
        story.append(Paragraph(school.school_name, template.styles['SchoolName']))
        
        # School address
        if school.address:
            story.append(Paragraph(school.address, template.styles['SchoolAddress']))
        
        # Contact information
        contact_info = []
        if school.phone:
            contact_info.append(f"Tel: {school.phone}")
        if school.email:
            contact_info.append(f"Email: {school.email}")
        
        if contact_info:
            story.append(Paragraph(" | ".join(contact_info), template.styles['SchoolAddress']))
        
        # Report title
        report_title = f"STUDENT REPORT CARD - {term.term_name.upper()}"
        if session:
            report_title += f" {session.session_name}"
        
        story.append(Paragraph(report_title, template.styles['ReportTitle']))
        story.append(Spacer(1, 20))
        
        return story
    
    def _build_student_info(self, template, student, user, class_obj):
        """Build student information section"""
        story = []
        
        # Student information table
        student_data = [
            ['Student Name:', f"{user.first_name} {user.last_name}"],
            ['Student ID:', student.student_id],
            ['Class:', class_obj.class_name if class_obj else 'N/A'],
            ['Gender:', user.gender.value.title()],
            ['Date of Birth:', user.date_of_birth.strftime('%d/%m/%Y') if user.date_of_birth else 'N/A']
        ]
        
        if student.admission_number:
            student_data.insert(2, ['Admission No:', student.admission_number])
        
        student_table = Table(student_data, colWidths=[2*inch, 3*inch])
        student_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('ALIGN', (0, 0), (0, -1), 'RIGHT'),
            ('ALIGN', (1, 0), (1, -1), 'LEFT'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('LEFTPADDING', (0, 0), (-1, -1), 6),
            ('RIGHTPADDING', (0, 0), (-1, -1), 6),
            ('TOPPADDING', (0, 0), (-1, -1), 3),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
        ]))
        
        story.append(student_table)
        story.append(Spacer(1, 20))
        
        return story
    
    def _build_results_table(self, template, results, student_id, term_id, class_id):
        """Build the main results table"""
        story = []
        
        # Table headers
        headers = [
            'Subject', 'CA1\n(10)', 'CA2\n(10)', 'Exam\n(80)', 'Total\n(100)', 
            'Grade', 'Position', 'Class\nAverage', 'Remark'
        ]
        
        # Table data
        table_data = [headers]
        
        for result in results:
            # Get subject position
            position_data = RankingSystem.calculate_subject_position(
                student_id, result.subject_id, class_id, term_id
            )
            
            # Get class average
            class_avg = ResultComputation.calculate_class_average(
                class_id, result.subject_id, term_id
            )
            
            # Determine remark based on grade
            remark = self._get_grade_remark(result.grade)
            
            row_data = [
                result.subject.subject_name,
                f"{float(result.ca1_score or 0):.1f}",
                f"{float(result.ca2_score or 0):.1f}",
                f"{float(result.exam_score or 0):.1f}",
                f"{float(result.total_score or 0):.1f}",
                result.grade or 'F9',
                f"{position_data.get('position', '-')}/{position_data.get('total_students', '-')}",
                f"{float(class_avg):.1f}",
                remark
            ]
            
            table_data.append(row_data)
        
        # Create table
        col_widths = [2.2*inch, 0.6*inch, 0.6*inch, 0.6*inch, 0.6*inch, 0.5*inch, 0.7*inch, 0.7*inch, 0.8*inch]
        results_table = Table(table_data, colWidths=col_widths)
        
        # Table styling
        table_style = [
            # Header styling
            ('BACKGROUND', (0, 0), (-1, 0), colors.darkblue),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 9),
            ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
            
            # Data styling
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 8),
            ('ALIGN', (1, 1), (-2, -1), 'CENTER'),  # Numeric columns
            ('ALIGN', (0, 1), (0, -1), 'LEFT'),     # Subject names
            ('ALIGN', (-1, 1), (-1, -1), 'CENTER'), # Remarks
            
            # Grid and borders
            ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            
            # Padding
            ('LEFTPADDING', (0, 0), (-1, -1), 4),
            ('RIGHTPADDING', (0, 0), (-1, -1), 4),
            ('TOPPADDING', (0, 0), (-1, -1), 3),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
        ]
        
        # Add alternating row colors
        for i in range(1, len(table_data)):
            if i % 2 == 0:
                table_style.append(('BACKGROUND', (0, i), (-1, i), colors.lightgrey))
        
        results_table.setStyle(TableStyle(table_style))
        
        story.append(results_table)
        story.append(Spacer(1, 15))
        
        return story
    
    def _build_summary_section(self, template, results, student_id, term_id, class_id):
        """Build summary statistics section"""
        story = []
        
        # Calculate summary statistics
        total_subjects = len(results)
        total_score = sum(float(r.total_score or 0) for r in results)
        average_score = total_score / total_subjects if total_subjects > 0 else 0
        highest_score = max(float(r.total_score or 0) for r in results) if results else 0
        lowest_score = min(float(r.total_score or 0) for r in results) if results else 0
        
        # Get class position
        position_data = RankingSystem.get_student_position(student_id, class_id, term_id)
        
        # Grade distribution
        grade_counts = {}
        for result in results:
            grade = result.grade or 'F9'
            grade_counts[grade] = grade_counts.get(grade, 0) + 1
        
        # Summary table
        summary_data = [
            ['PERFORMANCE SUMMARY', ''],
            ['Total Subjects Offered:', str(total_subjects)],
            ['Total Score:', f"{total_score:.1f}"],
            ['Average Score:', f"{average_score:.1f}%"],
            ['Highest Score:', f"{highest_score:.1f}%"],
            ['Lowest Score:', f"{lowest_score:.1f}%"],
            ['Class Position:', f"{position_data.get('position', '-')} out of {position_data.get('total_students', '-')}"],
        ]
        
        summary_table = Table(summary_data, colWidths=[3*inch, 2*inch])
        summary_table.setStyle(TableStyle([
            # Header
            ('BACKGROUND', (0, 0), (-1, 0), colors.darkgreen),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 11),
            ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
            ('SPAN', (0, 0), (-1, 0)),
            
            # Data
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 10),
            ('FONTNAME', (0, 1), (0, -1), 'Helvetica-Bold'),
            ('ALIGN', (0, 1), (0, -1), 'RIGHT'),
            ('ALIGN', (1, 1), (1, -1), 'LEFT'),
            
            # Borders
            ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            
            # Padding
            ('LEFTPADDING', (0, 0), (-1, -1), 6),
            ('RIGHTPADDING', (0, 0), (-1, -1), 6),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ]))
        
        story.append(summary_table)
        story.append(Spacer(1, 15))
        
        return story
    
    def _build_comments_section(self, template, results, student_id, term_id):
        """Build comments and remarks section"""
        story = []
        
        # Class teacher's comment
        story.append(Paragraph("<b>CLASS TEACHER'S COMMENT:</b>", template.styles['Normal']))
        
        # Generate automatic comment based on performance
        average_score = sum(float(r.total_score or 0) for r in results) / len(results) if results else 0
        auto_comment = self._generate_teacher_comment(average_score, len(results))
        
        story.append(Paragraph(auto_comment, template.styles['Comment']))
        story.append(Spacer(1, 10))
        
        # Principal's comment
        story.append(Paragraph("<b>PRINCIPAL'S COMMENT:</b>", template.styles['Normal']))
        principal_comment = self._generate_principal_comment(average_score)
        story.append(Paragraph(principal_comment, template.styles['Comment']))
        story.append(Spacer(1, 15))
        
        # Grading system explanation
        story.append(Paragraph("<b>GRADING SYSTEM:</b>", template.styles['Normal']))
        grading_info = """
        A1 (80-100): Excellent | B2 (70-79): Very Good | B3 (65-69): Good | 
        C4 (60-64): Credit | C5 (55-59): Credit | C6 (50-54): Credit | 
        D7 (45-49): Pass | E8 (40-44): Pass | F9 (0-39): Fail
        """
        story.append(Paragraph(grading_info, template.styles['Comment']))
        story.append(Spacer(1, 15))
        
        return story
    
    def _build_signatures_section(self, template):
        """Build signatures section"""
        story = []
        
        # Signature table
        signature_data = [
            ['Class Teacher:', '_' * 25, 'Date:', '_' * 15],
            ['', '', '', ''],
            ['Principal:', '_' * 25, 'Date:', '_' * 15],
            ['', '', '', ''],
            ['Parent/Guardian:', '_' * 25, 'Date:', '_' * 15],
        ]
        
        signature_table = Table(signature_data, colWidths=[1.5*inch, 2*inch, 0.8*inch, 1.2*inch])
        signature_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTNAME', (2, 0), (2, -1), 'Helvetica-Bold'),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('VALIGN', (0, 0), (-1, -1), 'BOTTOM'),
            ('LEFTPADDING', (0, 0), (-1, -1), 0),
            ('RIGHTPADDING', (0, 0), (-1, -1), 0),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
        ]))
        
        story.append(signature_table)
        
        return story
    
    def _get_grade_remark(self, grade):
        """Get remark based on grade"""
        remarks = {
            'A1': 'Excellent',
            'B2': 'Very Good',
            'B3': 'Good',
            'C4': 'Credit',
            'C5': 'Credit',
            'C6': 'Credit',
            'D7': 'Pass',
            'E8': 'Pass',
            'F9': 'Fail'
        }
        return remarks.get(grade, 'Fail')
    
    def _generate_teacher_comment(self, average_score, subject_count):
        """Generate automatic teacher comment based on performance"""
        if average_score >= 80:
            return f"Excellent performance! {subject_count} subjects completed with outstanding results. Keep up the excellent work and continue to strive for academic excellence."
        elif average_score >= 70:
            return f"Very good performance in {subject_count} subjects. Shows consistent effort and good understanding. Continue working hard to maintain this standard."
        elif average_score >= 60:
            return f"Good performance overall. {subject_count} subjects completed satisfactorily. Focus on improving weaker areas to achieve better results."
        elif average_score >= 50:
            return f"Fair performance in {subject_count} subjects. There is room for improvement. More effort and dedication needed in studies."
        else:
            return f"Performance needs significant improvement. {subject_count} subjects require more attention. Seek help from teachers and increase study time."
    
    def _generate_principal_comment(self, average_score):
        """Generate automatic principal comment"""
        if average_score >= 75:
            return "An exemplary student who demonstrates academic excellence. Promoted to the next class."
        elif average_score >= 60:
            return "A good student with satisfactory performance. Promoted to the next class."
        elif average_score >= 50:
            return "Fair performance. Promoted to the next class with the expectation of improved performance."
        else:
            return "Performance requires significant improvement. Consider remedial classes and extra support."

class BulkReportGenerator:
    """Generate reports for multiple students"""
    
    def __init__(self):
        self.report_generator = ReportGenerator()
    
    def generate_class_reports(self, class_id: int, term_id: int, output_dir: str) -> Dict:
        """Generate reports for all students in a class"""
        try:
            # Get all students in the class
            students = Student.query.filter_by(current_class_id=class_id).all()
            
            if not students:
                return {'success': False, 'message': 'No students found in this class'}
            
            # Create output directory if it doesn't exist
            os.makedirs(output_dir, exist_ok=True)
            
            generated_reports = []
            failed_reports = []
            
            for student in students:
                try:
                    user = User.query.get(student.user_id)
                    filename = f"report_{student.student_id}_{term_id}.pdf"
                    output_path = os.path.join(output_dir, filename)
                    
                    result = self.report_generator.generate_student_report(
                        student.id, term_id, output_path
                    )
                    
                    if result['success']:
                        generated_reports.append({
                            'student_id': student.id,
                            'student_name': f"{user.first_name} {user.last_name}",
                            'file_path': output_path,
                            'filename': filename
                        })
                    else:
                        failed_reports.append({
                            'student_id': student.id,
                            'student_name': f"{user.first_name} {user.last_name}",
                            'error': result['message']
                        })
                        
                except Exception as e:
                    failed_reports.append({
                        'student_id': student.id,
                        'student_name': f"{user.first_name} {user.last_name}" if 'user' in locals() else 'Unknown',
                        'error': str(e)
                    })
            
            return {
                'success': True,
                'message': f'Generated {len(generated_reports)} reports, {len(failed_reports)} failed',
                'generated_count': len(generated_reports),
                'failed_count': len(failed_reports),
                'generated_reports': generated_reports,
                'failed_reports': failed_reports,
                'output_directory': output_dir
            }
            
        except Exception as e:
            return {'success': False, 'message': f'Error generating class reports: {str(e)}'}

class ReportAnalytics:
    """Generate analytical reports and statistics"""
    
    @staticmethod
    def generate_class_performance_report(class_id: int, term_id: int) -> Dict:
        """Generate comprehensive class performance analysis"""
        try:
            # Get class and term information
            class_obj = Class.query.get(class_id)
            term = Term.query.get(term_id)
            
            if not class_obj or not term:
                return {'success': False, 'message': 'Class or term not found'}
            
            # Get all results for the class and term
            results = Result.query.filter_by(
                class_id=class_id,
                term_id=term_id,
                is_submitted=True
            ).all()
            
            if not results:
                return {'success': False, 'message': 'No results found'}
            
            # Calculate class statistics
            total_students = len(set(r.student_id for r in results))
            subjects = list(set(r.subject_id for r in results))
            
            # Subject-wise analysis
            subject_analysis = {}
            for subject_id in subjects:
                subject_results = [r for r in results if r.subject_id == subject_id]
                subject = Subject.query.get(subject_id)
                
                scores = [float(r.total_score or 0) for r in subject_results]
                subject_analysis[subject.subject_name] = {
                    'total_students': len(subject_results),
                    'average_score': sum(scores) / len(scores),
                    'highest_score': max(scores),
                    'lowest_score': min(scores),
                    'pass_rate': len([s for s in scores if s >= 50]) / len(scores) * 100
                }
            
            # Grade distribution
            grade_distribution = {}
            for result in results:
                grade = result.grade or 'F9'
                grade_distribution[grade] = grade_distribution.get(grade, 0) + 1
            
            # Overall class performance
            all_scores = [float(r.total_score or 0) for r in results]
            class_average = sum(all_scores) / len(all_scores)
            
            return {
                'success': True,
                'data': {
                    'class_info': {
                        'class_name': class_obj.class_name,
                        'term_name': term.term_name,
                        'total_students': total_students,
                        'total_subjects': len(subjects)
                    },
                    'overall_performance': {
                        'class_average': round(class_average, 2),
                        'highest_score': max(all_scores),
                        'lowest_score': min(all_scores),
                        'pass_rate': len([s for s in all_scores if s >= 50]) / len(all_scores) * 100
                    },
                    'subject_analysis': subject_analysis,
                    'grade_distribution': grade_distribution
                }
            }
            
        except Exception as e:
            return {'success': False, 'message': f'Error generating performance report: {str(e)}'}

