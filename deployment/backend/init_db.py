#!/usr/bin/env python3
"""
Database initialization script for Nigerian School Result Portal
This script creates sample data for testing and demonstration purposes
"""

import os
import sys
from datetime import datetime, date, timedelta

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from src.main import create_app
from src.models.models import (
    db, School, AcademicSession, Term, Class, Subject, ClassSubject,
    User, Student, ParentChild, ClassEnrollment, Result, TermResultSummary,
    GradingSystem, GradeScale, SchoolType, ClassLevel, UserRole, Gender,
    PromotionStatus, Rating
)
from decimal import Decimal

def init_database():
    """Initialize database with sample data"""
    app = create_app('development')
    
    with app.app_context():
        try:
            # Drop all tables and recreate
            print("Dropping existing tables...")
            db.drop_all()
            
            print("Creating new tables...")
            db.create_all()
            
            # Create sample school
            print("Creating sample school...")
            school = School(
                name="Excellence International School",
                address="123 Education Avenue, Victoria Island, Lagos",
                phone="+234-801-234-5678",
                email="info@excellenceschool.edu.ng",
                motto="Excellence in Learning, Character in Living",
                principal_name="Dr. Adebayo Johnson",
                school_type=SchoolType.BOTH
            )
            db.session.add(school)
            db.session.flush()
            
            # Create academic session
            print("Creating academic session...")
            session = AcademicSession(
                school_id=school.id,
                session_name="2024/2025",
                start_date=date(2024, 9, 1),
                end_date=date(2025, 7, 31),
                is_active=True
            )
            db.session.add(session)
            db.session.flush()
            
            # Create terms
            print("Creating terms...")
            terms = [
                Term(
                    session_id=session.id,
                    term_number=1,
                    term_name="First Term",
                    start_date=date(2024, 9, 1),
                    end_date=date(2024, 12, 20),
                    is_active=True
                ),
                Term(
                    session_id=session.id,
                    term_number=2,
                    term_name="Second Term",
                    start_date=date(2025, 1, 15),
                    end_date=date(2025, 4, 10),
                    is_active=False
                ),
                Term(
                    session_id=session.id,
                    term_number=3,
                    term_name="Third Term",
                    start_date=date(2025, 4, 20),
                    end_date=date(2025, 7, 31),
                    is_active=False
                )
            ]
            
            for term in terms:
                db.session.add(term)
            db.session.flush()
            
            # Create classes
            print("Creating classes...")
            classes = [
                # Primary Classes
                Class(school_id=school.id, class_name="Primary 1A", class_level=ClassLevel.PRIMARY, class_number=1, arm="A"),
                Class(school_id=school.id, class_name="Primary 2A", class_level=ClassLevel.PRIMARY, class_number=2, arm="A"),
                Class(school_id=school.id, class_name="Primary 3A", class_level=ClassLevel.PRIMARY, class_number=3, arm="A"),
                Class(school_id=school.id, class_name="Primary 4A", class_level=ClassLevel.PRIMARY, class_number=4, arm="A"),
                Class(school_id=school.id, class_name="Primary 5A", class_level=ClassLevel.PRIMARY, class_number=5, arm="A"),
                Class(school_id=school.id, class_name="Primary 6A", class_level=ClassLevel.PRIMARY, class_number=6, arm="A"),
                
                # Junior Secondary Classes
                Class(school_id=school.id, class_name="JSS 1A", class_level=ClassLevel.JUNIOR_SECONDARY, class_number=1, arm="A"),
                Class(school_id=school.id, class_name="JSS 2A", class_level=ClassLevel.JUNIOR_SECONDARY, class_number=2, arm="A"),
                Class(school_id=school.id, class_name="JSS 3A", class_level=ClassLevel.JUNIOR_SECONDARY, class_number=3, arm="A"),
                
                # Senior Secondary Classes
                Class(school_id=school.id, class_name="SS 1A", class_level=ClassLevel.SENIOR_SECONDARY, class_number=1, arm="A"),
                Class(school_id=school.id, class_name="SS 2A", class_level=ClassLevel.SENIOR_SECONDARY, class_number=2, arm="A"),
                Class(school_id=school.id, class_name="SS 3A", class_level=ClassLevel.SENIOR_SECONDARY, class_number=3, arm="A"),
            ]
            
            for cls in classes:
                db.session.add(cls)
            db.session.flush()
            
            # Create subjects
            print("Creating subjects...")
            subjects = [
                # Primary subjects
                Subject(school_id=school.id, subject_name="Mathematics", subject_code="MATH", class_level=ClassLevel.PRIMARY, is_core=True),
                Subject(school_id=school.id, subject_name="English Language", subject_code="ENG", class_level=ClassLevel.PRIMARY, is_core=True),
                Subject(school_id=school.id, subject_name="Basic Science", subject_code="BSC", class_level=ClassLevel.PRIMARY, is_core=True),
                Subject(school_id=school.id, subject_name="Social Studies", subject_code="SST", class_level=ClassLevel.PRIMARY, is_core=True),
                Subject(school_id=school.id, subject_name="Yoruba Language", subject_code="YOR", class_level=ClassLevel.PRIMARY, is_core=False),
                Subject(school_id=school.id, subject_name="Christian Religious Studies", subject_code="CRS", class_level=ClassLevel.PRIMARY, is_core=False),
                
                # Junior Secondary subjects
                Subject(school_id=school.id, subject_name="Mathematics", subject_code="MATH", class_level=ClassLevel.JUNIOR_SECONDARY, is_core=True),
                Subject(school_id=school.id, subject_name="English Language", subject_code="ENG", class_level=ClassLevel.JUNIOR_SECONDARY, is_core=True),
                Subject(school_id=school.id, subject_name="Basic Science", subject_code="BSC", class_level=ClassLevel.JUNIOR_SECONDARY, is_core=True),
                Subject(school_id=school.id, subject_name="Social Studies", subject_code="SST", class_level=ClassLevel.JUNIOR_SECONDARY, is_core=True),
                Subject(school_id=school.id, subject_name="Computer Studies", subject_code="CMP", class_level=ClassLevel.JUNIOR_SECONDARY, is_core=True),
                Subject(school_id=school.id, subject_name="French Language", subject_code="FRE", class_level=ClassLevel.JUNIOR_SECONDARY, is_core=False),
                
                # Senior Secondary subjects
                Subject(school_id=school.id, subject_name="Mathematics", subject_code="MATH", class_level=ClassLevel.SENIOR_SECONDARY, is_core=True),
                Subject(school_id=school.id, subject_name="English Language", subject_code="ENG", class_level=ClassLevel.SENIOR_SECONDARY, is_core=True),
                Subject(school_id=school.id, subject_name="Physics", subject_code="PHY", class_level=ClassLevel.SENIOR_SECONDARY, is_core=True),
                Subject(school_id=school.id, subject_name="Chemistry", subject_code="CHE", class_level=ClassLevel.SENIOR_SECONDARY, is_core=True),
                Subject(school_id=school.id, subject_name="Biology", subject_code="BIO", class_level=ClassLevel.SENIOR_SECONDARY, is_core=True),
                Subject(school_id=school.id, subject_name="Economics", subject_code="ECO", class_level=ClassLevel.SENIOR_SECONDARY, is_core=False),
                Subject(school_id=school.id, subject_name="Government", subject_code="GOV", class_level=ClassLevel.SENIOR_SECONDARY, is_core=False),
            ]
            
            for subject in subjects:
                db.session.add(subject)
            db.session.flush()
            
            # Create grading system (WAEC standard)
            print("Creating grading system...")
            grading_system = GradingSystem(
                school_id=school.id,
                system_name="WAEC Standard Grading",
                is_default=True
            )
            db.session.add(grading_system)
            db.session.flush()
            
            # Create grade scales
            grade_scales = [
                GradeScale(grading_system_id=grading_system.id, grade="A1", min_score=75, max_score=100, grade_point=4.0, description="Excellent"),
                GradeScale(grading_system_id=grading_system.id, grade="B2", min_score=70, max_score=74, grade_point=3.5, description="Very Good"),
                GradeScale(grading_system_id=grading_system.id, grade="B3", min_score=65, max_score=69, grade_point=3.0, description="Good"),
                GradeScale(grading_system_id=grading_system.id, grade="C4", min_score=60, max_score=64, grade_point=2.5, description="Credit"),
                GradeScale(grading_system_id=grading_system.id, grade="C5", min_score=55, max_score=59, grade_point=2.0, description="Credit"),
                GradeScale(grading_system_id=grading_system.id, grade="C6", min_score=50, max_score=54, grade_point=1.5, description="Credit"),
                GradeScale(grading_system_id=grading_system.id, grade="D7", min_score=45, max_score=49, grade_point=1.0, description="Pass"),
                GradeScale(grading_system_id=grading_system.id, grade="E8", min_score=40, max_score=44, grade_point=0.5, description="Pass"),
                GradeScale(grading_system_id=grading_system.id, grade="F9", min_score=0, max_score=39, grade_point=0.0, description="Fail"),
            ]
            
            for scale in grade_scales:
                db.session.add(scale)
            
            # Create users
            print("Creating users...")
            
            # Super Admin
            super_admin = User(
                school_id=school.id,
                username="superadmin",
                email="admin@excellenceschool.edu.ng",
                first_name="System",
                last_name="Administrator",
                gender=Gender.MALE,
                role=UserRole.SUPER_ADMIN,
                is_active=True
            )
            super_admin.set_password("admin123")
            db.session.add(super_admin)
            
            # School Admin
            school_admin = User(
                school_id=school.id,
                username="schooladmin",
                email="principal@excellenceschool.edu.ng",
                first_name="Adebayo",
                last_name="Johnson",
                gender=Gender.MALE,
                role=UserRole.SCHOOL_ADMIN,
                is_active=True
            )
            school_admin.set_password("admin123")
            db.session.add(school_admin)
            
            # Teachers
            teachers_data = [
                {"username": "teacher1", "first_name": "Funmi", "last_name": "Adebayo", "email": "funmi@excellenceschool.edu.ng", "gender": Gender.FEMALE},
                {"username": "teacher2", "first_name": "Kemi", "last_name": "Ogundimu", "email": "kemi@excellenceschool.edu.ng", "gender": Gender.FEMALE},
                {"username": "teacher3", "first_name": "Tunde", "last_name": "Okafor", "email": "tunde@excellenceschool.edu.ng", "gender": Gender.MALE},
                {"username": "teacher4", "first_name": "Bisi", "last_name": "Adeyemi", "email": "bisi@excellenceschool.edu.ng", "gender": Gender.FEMALE},
                {"username": "teacher5", "first_name": "Emeka", "last_name": "Nwankwo", "email": "emeka@excellenceschool.edu.ng", "gender": Gender.MALE},
            ]
            
            teachers = []
            for teacher_data in teachers_data:
                teacher = User(
                    school_id=school.id,
                    username=teacher_data["username"],
                    email=teacher_data["email"],
                    first_name=teacher_data["first_name"],
                    last_name=teacher_data["last_name"],
                    gender=teacher_data["gender"],
                    role=UserRole.TEACHER,
                    is_active=True
                )
                teacher.set_password("teacher123")
                db.session.add(teacher)
                teachers.append(teacher)
            
            db.session.flush()
            
            # Create students and parents
            print("Creating students and parents...")
            students_data = [
                {"first_name": "Adunni", "last_name": "Bakare", "gender": Gender.FEMALE, "class_idx": 0},
                {"first_name": "Chinedu", "last_name": "Okoro", "gender": Gender.MALE, "class_idx": 0},
                {"first_name": "Fatima", "last_name": "Ibrahim", "gender": Gender.FEMALE, "class_idx": 0},
                {"first_name": "Kelechi", "last_name": "Eze", "gender": Gender.MALE, "class_idx": 0},
                {"first_name": "Aminat", "last_name": "Yusuf", "gender": Gender.FEMALE, "class_idx": 0},
                {"first_name": "Olumide", "last_name": "Adeyemi", "gender": Gender.MALE, "class_idx": 6},  # JSS 1A
                {"first_name": "Chioma", "last_name": "Nwachukwu", "gender": Gender.FEMALE, "class_idx": 6},
                {"first_name": "Ibrahim", "last_name": "Musa", "gender": Gender.MALE, "class_idx": 6},
                {"first_name": "Blessing", "last_name": "Okafor", "gender": Gender.FEMALE, "class_idx": 9},  # SS 1A
                {"first_name": "David", "last_name": "Ogundimu", "gender": Gender.MALE, "class_idx": 9},
            ]
            
            students = []
            parents = []
            
            for i, student_data in enumerate(students_data):
                # Create parent
                parent = User(
                    school_id=school.id,
                    username=f"parent{i+1}",
                    email=f"parent{i+1}@email.com",
                    first_name=f"Mr/Mrs",
                    last_name=student_data["last_name"],
                    gender=Gender.MALE if i % 2 == 0 else Gender.FEMALE,
                    role=UserRole.PARENT,
                    is_active=True
                )
                parent.set_password("parent123")
                db.session.add(parent)
                parents.append(parent)
                
                # Create student user
                student_user = User(
                    school_id=school.id,
                    username=f"student{i+1}",
                    email=f"student{i+1}@email.com",
                    first_name=student_data["first_name"],
                    last_name=student_data["last_name"],
                    gender=student_data["gender"],
                    role=UserRole.STUDENT,
                    is_active=True
                )
                student_user.set_password("student123")
                db.session.add(student_user)
                db.session.flush()
                
                # Create student profile
                student = Student(
                    user_id=student_user.id,
                    student_id=f"STU{2024}{i+1:04d}",
                    admission_number=f"ADM{2024}{i+1:04d}",
                    admission_date=date(2024, 9, 1),
                    current_class_id=classes[student_data["class_idx"]].id,
                    guardian_name=f"Mr/Mrs {student_data['last_name']}",
                    guardian_phone=f"+234-80{i+1}-234-567{i}",
                    guardian_email=f"parent{i+1}@email.com"
                )
                db.session.add(student)
                students.append(student)
                
            db.session.flush()
            
            # Create parent-child relationships
            for i, (parent, student) in enumerate(zip(parents, students)):
                parent_child = ParentChild(
                    parent_id=parent.id,
                    child_id=student.id,
                    relationship="parent"
                )
                db.session.add(parent_child)
            
            # Create class enrollments
            print("Creating class enrollments...")
            for student in students:
                enrollment = ClassEnrollment(
                    student_id=student.id,
                    class_id=student.current_class_id,
                    session_id=session.id,
                    enrollment_date=date(2024, 9, 1),
                    is_active=True
                )
                db.session.add(enrollment)
            
            # Assign subjects to classes and teachers
            print("Assigning subjects to classes...")
            
            # Primary 1A subjects
            primary_subjects = [s for s in subjects if s.class_level == ClassLevel.PRIMARY][:6]
            for i, subject in enumerate(primary_subjects):
                class_subject = ClassSubject(
                    class_id=classes[0].id,  # Primary 1A
                    subject_id=subject.id,
                    teacher_id=teachers[i % len(teachers)].id,
                    is_active=True
                )
                db.session.add(class_subject)
            
            # JSS 1A subjects
            jss_subjects = [s for s in subjects if s.class_level == ClassLevel.JUNIOR_SECONDARY][:6]
            for i, subject in enumerate(jss_subjects):
                class_subject = ClassSubject(
                    class_id=classes[6].id,  # JSS 1A
                    subject_id=subject.id,
                    teacher_id=teachers[i % len(teachers)].id,
                    is_active=True
                )
                db.session.add(class_subject)
            
            # SS 1A subjects
            ss_subjects = [s for s in subjects if s.class_level == ClassLevel.SENIOR_SECONDARY][:7]
            for i, subject in enumerate(ss_subjects):
                class_subject = ClassSubject(
                    class_id=classes[9].id,  # SS 1A
                    subject_id=subject.id,
                    teacher_id=teachers[i % len(teachers)].id,
                    is_active=True
                )
                db.session.add(class_subject)
            
            db.session.flush()
            
            # Create sample results
            print("Creating sample results...")
            active_term = terms[0]  # First term
            
            # Get students in different classes
            primary_students = [s for s in students if s.current_class_id == classes[0].id]  # Primary 1A
            jss_students = [s for s in students if s.current_class_id == classes[6].id]  # JSS 1A
            ss_students = [s for s in students if s.current_class_id == classes[9].id]  # SS 1A
            
            # Create results for Primary 1A students
            for student in primary_students:
                for subject in primary_subjects:
                    result = Result(
                        student_id=student.id,
                        class_id=classes[0].id,
                        subject_id=subject.id,
                        term_id=active_term.id,
                        ca1_score=Decimal(str(7 + (hash(f"{student.id}{subject.id}") % 4))),  # 7-10
                        ca2_score=Decimal(str(6 + (hash(f"{student.id}{subject.id}1") % 5))),  # 6-10
                        exam_score=Decimal(str(45 + (hash(f"{student.id}{subject.id}2") % 35))),  # 45-80
                        is_submitted=True,
                        submitted_at=datetime.utcnow(),
                        submitted_by=teachers[0].id
                    )
                    result.calculate_total_score()
                    
                    # Assign grade based on total score
                    for scale in grade_scales:
                        if scale.min_score <= result.total_score <= scale.max_score:
                            result.grade = scale.grade
                            result.grade_point = scale.grade_point
                            break
                    
                    result.teacher_comment = "Good work, keep it up!"
                    db.session.add(result)
            
            # Similar for JSS and SS students
            for student in jss_students:
                for subject in jss_subjects:
                    result = Result(
                        student_id=student.id,
                        class_id=classes[6].id,
                        subject_id=subject.id,
                        term_id=active_term.id,
                        ca1_score=Decimal(str(6 + (hash(f"{student.id}{subject.id}") % 5))),
                        ca2_score=Decimal(str(7 + (hash(f"{student.id}{subject.id}1") % 4))),
                        exam_score=Decimal(str(40 + (hash(f"{student.id}{subject.id}2") % 40))),
                        is_submitted=True,
                        submitted_at=datetime.utcnow(),
                        submitted_by=teachers[1].id
                    )
                    result.calculate_total_score()
                    
                    for scale in grade_scales:
                        if scale.min_score <= result.total_score <= scale.max_score:
                            result.grade = scale.grade
                            result.grade_point = scale.grade_point
                            break
                    
                    result.teacher_comment = "Shows good understanding of the subject."
                    db.session.add(result)
            
            for student in ss_students:
                for subject in ss_subjects:
                    result = Result(
                        student_id=student.id,
                        class_id=classes[9].id,
                        subject_id=subject.id,
                        term_id=active_term.id,
                        ca1_score=Decimal(str(8 + (hash(f"{student.id}{subject.id}") % 3))),
                        ca2_score=Decimal(str(7 + (hash(f"{student.id}{subject.id}1") % 4))),
                        exam_score=Decimal(str(50 + (hash(f"{student.id}{subject.id}2") % 30))),
                        is_submitted=True,
                        submitted_at=datetime.utcnow(),
                        submitted_by=teachers[2].id
                    )
                    result.calculate_total_score()
                    
                    for scale in grade_scales:
                        if scale.min_score <= result.total_score <= scale.max_score:
                            result.grade = scale.grade
                            result.grade_point = scale.grade_point
                            break
                    
                    result.teacher_comment = "Excellent performance, well done!"
                    db.session.add(result)
            
            # Commit all changes
            db.session.commit()
            
            print("✅ Database initialized successfully!")
            print("\n" + "="*50)
            print("SAMPLE LOGIN CREDENTIALS")
            print("="*50)
            print("Super Admin:")
            print("  Username: superadmin")
            print("  Password: admin123")
            print("\nSchool Admin:")
            print("  Username: schooladmin")
            print("  Password: admin123")
            print("\nTeacher:")
            print("  Username: teacher1")
            print("  Password: teacher123")
            print("\nStudent:")
            print("  Username: student1")
            print("  Password: student123")
            print("\nParent:")
            print("  Username: parent1")
            print("  Password: parent123")
            print("="*50)
            
        except Exception as e:
            print(f"❌ Error initializing database: {str(e)}")
            db.session.rollback()
            raise

if __name__ == "__main__":
    init_database()

