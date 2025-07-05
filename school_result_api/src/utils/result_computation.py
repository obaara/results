"""
Result computation utilities for the Nigerian School Result Portal
Handles score calculations, grading, ranking, and performance analytics
"""

from decimal import Decimal, ROUND_HALF_UP
from typing import List, Dict, Tuple, Optional
from datetime import datetime
from sqlalchemy import func, desc, asc
from src.models.models import (
    db, Result, Student, Subject, Class, Term, AcademicSession,
    GradingSystem, GradeScale, TermResultSummary, User
)

class ResultComputation:
    """Core result computation engine"""
    
    @staticmethod
    def calculate_weighted_score(ca1_score: Decimal, ca2_score: Decimal, exam_score: Decimal) -> Decimal:
        """
        Calculate weighted total score using Nigerian standard:
        CA1: 10%, CA2: 10%, Exam: 80%
        """
        ca1_weighted = (ca1_score or Decimal('0')) * Decimal('0.1')
        ca2_weighted = (ca2_score or Decimal('0')) * Decimal('0.1')
        exam_weighted = (exam_score or Decimal('0')) * Decimal('0.8')
        
        total = ca1_weighted + ca2_weighted + exam_weighted
        return total.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    
    @staticmethod
    def get_grade_from_score(score: Decimal, grading_system_id: int) -> Tuple[str, Decimal, str]:
        """
        Get grade, grade point, and description from score using grading system
        Returns: (grade, grade_point, description)
        """
        grade_scales = GradeScale.query.filter_by(
            grading_system_id=grading_system_id
        ).order_by(desc(GradeScale.min_score)).all()
        
        for scale in grade_scales:
            if scale.min_score <= score <= scale.max_score:
                return scale.grade, scale.grade_point, scale.description
        
        # Default to lowest grade if no match found
        lowest_scale = grade_scales[-1] if grade_scales else None
        if lowest_scale:
            return lowest_scale.grade, lowest_scale.grade_point, lowest_scale.description
        
        return 'F9', Decimal('0.0'), 'Fail'
    
    @staticmethod
    def calculate_gpa(results: List[Result]) -> Decimal:
        """Calculate Grade Point Average from a list of results"""
        if not results:
            return Decimal('0.0')
        
        total_points = sum(result.grade_point or Decimal('0') for result in results)
        return (total_points / len(results)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    
    @staticmethod
    def calculate_class_average(class_id: int, subject_id: int, term_id: int) -> Decimal:
        """Calculate class average for a specific subject and term"""
        results = Result.query.filter_by(
            class_id=class_id,
            subject_id=subject_id,
            term_id=term_id,
            is_submitted=True
        ).all()
        
        if not results:
            return Decimal('0.0')
        
        total_score = sum(result.total_score or Decimal('0') for result in results)
        return (total_score / len(results)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    
    @staticmethod
    def calculate_student_term_average(student_id: int, term_id: int) -> Decimal:
        """Calculate student's average for a specific term"""
        results = Result.query.filter_by(
            student_id=student_id,
            term_id=term_id,
            is_submitted=True
        ).all()
        
        if not results:
            return Decimal('0.0')
        
        total_score = sum(result.total_score or Decimal('0') for result in results)
        return (total_score / len(results)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    
    @staticmethod
    def calculate_cumulative_average(student_id: int, session_id: int) -> Decimal:
        """Calculate student's cumulative average for an academic session"""
        # Get all terms in the session
        terms = Term.query.filter_by(session_id=session_id).all()
        term_ids = [term.id for term in terms]
        
        results = Result.query.filter(
            Result.student_id == student_id,
            Result.term_id.in_(term_ids),
            Result.is_submitted == True
        ).all()
        
        if not results:
            return Decimal('0.0')
        
        total_score = sum(result.total_score or Decimal('0') for result in results)
        return (total_score / len(results)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

class RankingSystem:
    """Handle student ranking and positioning"""
    
    @staticmethod
    def calculate_class_ranking(class_id: int, term_id: int) -> List[Dict]:
        """
        Calculate class ranking for a specific term
        Returns list of students with their positions
        """
        # Get all students in the class with their term averages
        students_query = db.session.query(
            Student.id,
            Student.user_id,
            User.first_name,
            User.last_name,
            func.avg(Result.total_score).label('average_score'),
            func.count(Result.id).label('subject_count')
        ).join(
            User, Student.user_id == User.id
        ).join(
            Result, Student.id == Result.student_id
        ).filter(
            Result.class_id == class_id,
            Result.term_id == term_id,
            Result.is_submitted == True
        ).group_by(
            Student.id, Student.user_id, User.first_name, User.last_name
        ).order_by(
            desc('average_score')
        ).all()
        
        ranking = []
        for position, student_data in enumerate(students_query, 1):
            ranking.append({
                'student_id': student_data.id,
                'user_id': student_data.user_id,
                'full_name': f"{student_data.first_name} {student_data.last_name}",
                'average_score': float(student_data.average_score or 0),
                'subject_count': student_data.subject_count,
                'position': position,
                'total_students': len(students_query)
            })
        
        return ranking
    
    @staticmethod
    def get_student_position(student_id: int, class_id: int, term_id: int) -> Dict:
        """Get specific student's position in class"""
        ranking = RankingSystem.calculate_class_ranking(class_id, term_id)
        
        for student_rank in ranking:
            if student_rank['student_id'] == student_id:
                return student_rank
        
        return {
            'student_id': student_id,
            'position': None,
            'total_students': len(ranking),
            'average_score': 0.0
        }
    
    @staticmethod
    def calculate_subject_position(student_id: int, subject_id: int, class_id: int, term_id: int) -> Dict:
        """Calculate student's position in a specific subject"""
        results_query = db.session.query(
            Result.student_id,
            Result.total_score,
            Student.user_id,
            User.first_name,
            User.last_name
        ).join(
            Student, Result.student_id == Student.id
        ).join(
            User, Student.user_id == User.id
        ).filter(
            Result.subject_id == subject_id,
            Result.class_id == class_id,
            Result.term_id == term_id,
            Result.is_submitted == True
        ).order_by(
            desc(Result.total_score)
        ).all()
        
        for position, result_data in enumerate(results_query, 1):
            if result_data.student_id == student_id:
                return {
                    'student_id': student_id,
                    'subject_id': subject_id,
                    'score': float(result_data.total_score or 0),
                    'position': position,
                    'total_students': len(results_query)
                }
        
        return {
            'student_id': student_id,
            'subject_id': subject_id,
            'position': None,
            'total_students': len(results_query),
            'score': 0.0
        }

class PerformanceAnalytics:
    """Advanced performance analytics and insights"""
    
    @staticmethod
    def analyze_student_performance(student_id: int, session_id: int) -> Dict:
        """Comprehensive performance analysis for a student"""
        # Get all terms in the session
        terms = Term.query.filter_by(session_id=session_id).order_by(Term.term_number).all()
        
        performance_data = {
            'student_id': student_id,
            'session_id': session_id,
            'term_performances': [],
            'subject_performances': {},
            'trends': {},
            'recommendations': []
        }
        
        # Analyze performance by term
        for term in terms:
            term_average = ResultComputation.calculate_student_term_average(student_id, term.id)
            term_results = Result.query.filter_by(
                student_id=student_id,
                term_id=term.id,
                is_submitted=True
            ).all()
            
            performance_data['term_performances'].append({
                'term_id': term.id,
                'term_name': term.term_name,
                'average_score': float(term_average),
                'subject_count': len(term_results),
                'highest_score': float(max([r.total_score for r in term_results], default=0)),
                'lowest_score': float(min([r.total_score for r in term_results], default=0))
            })
        
        # Analyze performance by subject
        all_results = Result.query.filter(
            Result.student_id == student_id,
            Result.term_id.in_([t.id for t in terms]),
            Result.is_submitted == True
        ).all()
        
        subject_scores = {}
        for result in all_results:
            subject_name = result.subject.subject_name
            if subject_name not in subject_scores:
                subject_scores[subject_name] = []
            subject_scores[subject_name].append(float(result.total_score or 0))
        
        for subject_name, scores in subject_scores.items():
            performance_data['subject_performances'][subject_name] = {
                'average_score': sum(scores) / len(scores),
                'highest_score': max(scores),
                'lowest_score': min(scores),
                'score_count': len(scores),
                'trend': PerformanceAnalytics._calculate_trend(scores)
            }
        
        # Calculate overall trends
        term_averages = [tp['average_score'] for tp in performance_data['term_performances']]
        if len(term_averages) > 1:
            performance_data['trends']['overall'] = PerformanceAnalytics._calculate_trend(term_averages)
        
        # Generate recommendations
        performance_data['recommendations'] = PerformanceAnalytics._generate_recommendations(performance_data)
        
        return performance_data
    
    @staticmethod
    def _calculate_trend(scores: List[float]) -> str:
        """Calculate performance trend from a list of scores"""
        if len(scores) < 2:
            return 'insufficient_data'
        
        # Simple trend calculation
        first_half = scores[:len(scores)//2]
        second_half = scores[len(scores)//2:]
        
        first_avg = sum(first_half) / len(first_half)
        second_avg = sum(second_half) / len(second_half)
        
        difference = second_avg - first_avg
        
        if difference > 5:
            return 'improving'
        elif difference < -5:
            return 'declining'
        else:
            return 'stable'
    
    @staticmethod
    def _generate_recommendations(performance_data: Dict) -> List[str]:
        """Generate performance recommendations based on analysis"""
        recommendations = []
        
        # Check overall performance
        if performance_data['term_performances']:
            latest_average = performance_data['term_performances'][-1]['average_score']
            
            if latest_average >= 75:
                recommendations.append("Excellent performance! Keep up the good work.")
            elif latest_average >= 60:
                recommendations.append("Good performance. Focus on improving weaker subjects.")
            elif latest_average >= 45:
                recommendations.append("Average performance. Consider additional study time.")
            else:
                recommendations.append("Performance needs improvement. Seek help from teachers.")
        
        # Check subject-specific recommendations
        weak_subjects = []
        strong_subjects = []
        
        for subject, data in performance_data['subject_performances'].items():
            if data['average_score'] < 50:
                weak_subjects.append(subject)
            elif data['average_score'] >= 75:
                strong_subjects.append(subject)
        
        if weak_subjects:
            recommendations.append(f"Focus more attention on: {', '.join(weak_subjects)}")
        
        if strong_subjects:
            recommendations.append(f"Continue excelling in: {', '.join(strong_subjects)}")
        
        # Check trends
        declining_subjects = [
            subject for subject, data in performance_data['subject_performances'].items()
            if data['trend'] == 'declining'
        ]
        
        if declining_subjects:
            recommendations.append(f"Address declining performance in: {', '.join(declining_subjects)}")
        
        return recommendations

class ResultProcessor:
    """Process and validate result entries"""
    
    @staticmethod
    def process_result_entry(result_data: Dict, grading_system_id: int) -> Dict:
        """
        Process a single result entry with validation and computation
        """
        try:
            # Extract scores
            ca1_score = Decimal(str(result_data.get('ca1_score', 0)))
            ca2_score = Decimal(str(result_data.get('ca2_score', 0)))
            exam_score = Decimal(str(result_data.get('exam_score', 0)))
            
            # Validate score ranges
            if not (0 <= ca1_score <= 10):
                return {'success': False, 'message': 'CA1 score must be between 0 and 10'}
            
            if not (0 <= ca2_score <= 10):
                return {'success': False, 'message': 'CA2 score must be between 0 and 10'}
            
            if not (0 <= exam_score <= 80):
                return {'success': False, 'message': 'Exam score must be between 0 and 80'}
            
            # Calculate total score
            total_score = ResultComputation.calculate_weighted_score(ca1_score, ca2_score, exam_score)
            
            # Get grade information
            grade, grade_point, description = ResultComputation.get_grade_from_score(
                total_score, grading_system_id
            )
            
            return {
                'success': True,
                'data': {
                    'ca1_score': ca1_score,
                    'ca2_score': ca2_score,
                    'exam_score': exam_score,
                    'total_score': total_score,
                    'grade': grade,
                    'grade_point': grade_point,
                    'description': description
                }
            }
            
        except (ValueError, TypeError) as e:
            return {'success': False, 'message': f'Invalid score format: {str(e)}'}
    
    @staticmethod
    def batch_process_results(results_data: List[Dict], grading_system_id: int) -> Dict:
        """Process multiple result entries in batch"""
        processed_results = []
        errors = []
        
        for i, result_data in enumerate(results_data):
            result = ResultProcessor.process_result_entry(result_data, grading_system_id)
            
            if result['success']:
                processed_results.append({
                    'index': i,
                    'student_id': result_data.get('student_id'),
                    'subject_id': result_data.get('subject_id'),
                    **result['data']
                })
            else:
                errors.append({
                    'index': i,
                    'student_id': result_data.get('student_id'),
                    'error': result['message']
                })
        
        return {
            'success': len(errors) == 0,
            'processed_count': len(processed_results),
            'error_count': len(errors),
            'results': processed_results,
            'errors': errors
        }
    
    @staticmethod
    def update_term_summary(student_id: int, term_id: int):
        """Update or create term result summary for a student"""
        # Get all results for the student in this term
        results = Result.query.filter_by(
            student_id=student_id,
            term_id=term_id,
            is_submitted=True
        ).all()
        
        if not results:
            return
        
        # Calculate summary statistics
        total_score = sum(result.total_score or Decimal('0') for result in results)
        average_score = total_score / len(results)
        highest_score = max(result.total_score or Decimal('0') for result in results)
        lowest_score = min(result.total_score or Decimal('0') for result in results)
        
        # Count grades
        grade_counts = {}
        for result in results:
            grade = result.grade or 'F9'
            grade_counts[grade] = grade_counts.get(grade, 0) + 1
        
        # Get or create summary record
        summary = TermResultSummary.query.filter_by(
            student_id=student_id,
            term_id=term_id
        ).first()
        
        if not summary:
            summary = TermResultSummary(
                student_id=student_id,
                term_id=term_id
            )
            db.session.add(summary)
        
        # Update summary data
        summary.total_subjects = len(results)
        summary.total_score = total_score
        summary.average_score = average_score
        summary.highest_score = highest_score
        summary.lowest_score = lowest_score
        summary.gpa = ResultComputation.calculate_gpa(results)
        
        # Get class position
        class_id = results[0].class_id
        position_data = RankingSystem.get_student_position(student_id, class_id, term_id)
        summary.class_position = position_data.get('position')
        summary.total_students = position_data.get('total_students')
        
        summary.updated_at = datetime.utcnow()
        
        try:
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            raise e

