from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
import enum

db = SQLAlchemy()

class SchoolType(enum.Enum):
    PRIMARY = 'primary'
    SECONDARY = 'secondary'
    BOTH = 'both'

class ClassLevel(enum.Enum):
    PRIMARY = 'primary'
    JUNIOR_SECONDARY = 'junior_secondary'
    SENIOR_SECONDARY = 'senior_secondary'

class UserRole(enum.Enum):
    SUPER_ADMIN = 'super_admin'
    SCHOOL_ADMIN = 'school_admin'
    TEACHER = 'teacher'
    STUDENT = 'student'
    PARENT = 'parent'

class Gender(enum.Enum):
    MALE = 'male'
    FEMALE = 'female'

class PromotionStatus(enum.Enum):
    PROMOTED = 'promoted'
    REPEATED = 'repeated'
    PENDING = 'pending'

class Rating(enum.Enum):
    EXCELLENT = 'excellent'
    VERY_GOOD = 'very_good'
    GOOD = 'good'
    FAIR = 'fair'
    POOR = 'poor'

# Core Models
class School(db.Model):
    __tablename__ = 'schools'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    address = db.Column(db.Text)
    phone = db.Column(db.String(20))
    email = db.Column(db.String(100))
    logo_url = db.Column(db.String(255))
    motto = db.Column(db.Text)
    principal_name = db.Column(db.String(100))
    school_type = db.Column(db.Enum(SchoolType), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    academic_sessions = db.relationship('AcademicSession', backref='school', lazy=True, cascade='all, delete-orphan')
    classes = db.relationship('Class', backref='school', lazy=True, cascade='all, delete-orphan')
    subjects = db.relationship('Subject', backref='school', lazy=True, cascade='all, delete-orphan')
    users = db.relationship('User', backref='school', lazy=True, cascade='all, delete-orphan')
    grading_systems = db.relationship('GradingSystem', backref='school', lazy=True, cascade='all, delete-orphan')

class AcademicSession(db.Model):
    __tablename__ = 'academic_sessions'
    
    id = db.Column(db.Integer, primary_key=True)
    school_id = db.Column(db.Integer, db.ForeignKey('schools.id'), nullable=False)
    session_name = db.Column(db.String(20), nullable=False)  # e.g., "2024/2025"
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=False)
    is_active = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    terms = db.relationship('Term', backref='session', lazy=True, cascade='all, delete-orphan')
    class_enrollments = db.relationship('ClassEnrollment', backref='session', lazy=True, cascade='all, delete-orphan')

class Term(db.Model):
    __tablename__ = 'terms'
    
    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.Integer, db.ForeignKey('academic_sessions.id'), nullable=False)
    term_number = db.Column(db.Integer, nullable=False)  # 1, 2, or 3
    term_name = db.Column(db.String(20), nullable=False)  # "First Term", "Second Term", "Third Term"
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=False)
    is_active = db.Column(db.Boolean, default=False)
    is_locked = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    results = db.relationship('Result', backref='term', lazy=True, cascade='all, delete-orphan')
    term_results_summaries = db.relationship('TermResultSummary', backref='term', lazy=True, cascade='all, delete-orphan')
    
    __table_args__ = (db.UniqueConstraint('session_id', 'term_number', name='unique_term_session'),)

class Class(db.Model):
    __tablename__ = 'classes'
    
    id = db.Column(db.Integer, primary_key=True)
    school_id = db.Column(db.Integer, db.ForeignKey('schools.id'), nullable=False)
    class_name = db.Column(db.String(50), nullable=False)  # "Primary 1", "JSS 1", "SS 2", etc.
    class_level = db.Column(db.Enum(ClassLevel), nullable=False)
    class_number = db.Column(db.Integer, nullable=False)
    arm = db.Column(db.String(10))  # "A", "B", "C", etc.
    capacity = db.Column(db.Integer, default=40)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    class_subjects = db.relationship('ClassSubject', backref='class_obj', lazy=True, cascade='all, delete-orphan')
    students = db.relationship('Student', backref='current_class', lazy=True)
    class_enrollments = db.relationship('ClassEnrollment', backref='class_obj', lazy=True, cascade='all, delete-orphan')
    results = db.relationship('Result', backref='class_obj', lazy=True, cascade='all, delete-orphan')

class Subject(db.Model):
    __tablename__ = 'subjects'
    
    id = db.Column(db.Integer, primary_key=True)
    school_id = db.Column(db.Integer, db.ForeignKey('schools.id'), nullable=False)
    subject_name = db.Column(db.String(100), nullable=False)
    subject_code = db.Column(db.String(10))
    is_core = db.Column(db.Boolean, default=True)
    class_level = db.Column(db.Enum(ClassLevel), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    class_subjects = db.relationship('ClassSubject', backref='subject', lazy=True, cascade='all, delete-orphan')
    results = db.relationship('Result', backref='subject', lazy=True, cascade='all, delete-orphan')

class ClassSubject(db.Model):
    __tablename__ = 'class_subjects'
    
    id = db.Column(db.Integer, primary_key=True)
    class_id = db.Column(db.Integer, db.ForeignKey('classes.id'), nullable=False)
    subject_id = db.Column(db.Integer, db.ForeignKey('subjects.id'), nullable=False)
    teacher_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    teacher = db.relationship('User', backref='teaching_subjects', lazy=True)
    
    __table_args__ = (db.UniqueConstraint('class_id', 'subject_id', name='unique_class_subject'),)

class User(db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    school_id = db.Column(db.Integer, db.ForeignKey('schools.id'), nullable=False)
    username = db.Column(db.String(50), unique=True, nullable=False)
    email = db.Column(db.String(100), unique=True)
    password_hash = db.Column(db.String(255), nullable=False)
    first_name = db.Column(db.String(50), nullable=False)
    last_name = db.Column(db.String(50), nullable=False)
    middle_name = db.Column(db.String(50))
    phone = db.Column(db.String(20))
    address = db.Column(db.Text)
    date_of_birth = db.Column(db.Date)
    gender = db.Column(db.Enum(Gender), nullable=False)
    role = db.Column(db.Enum(UserRole), nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    profile_picture_url = db.Column(db.String(255))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    student_profile = db.relationship('Student', backref='user', uselist=False, cascade='all, delete-orphan')
    parent_children = db.relationship('ParentChild', backref='parent', lazy=True, cascade='all, delete-orphan')
    submitted_results = db.relationship('Result', backref='submitted_by_user', lazy=True, foreign_keys='Result.submitted_by')
    
    def set_password(self, password):
        """Set password using secure hashing"""
        from src.utils.security import SecurityManager
        self.password_hash = SecurityManager.hash_password(password)
    
    def check_password(self, password):
        """Check password against hash"""
        from src.utils.security import SecurityManager
        return SecurityManager.verify_password(password, self.password_hash)
    
    @property
    def full_name(self):
        if self.middle_name:
            return f"{self.first_name} {self.middle_name} {self.last_name}"
        return f"{self.first_name} {self.last_name}"

class Student(db.Model):
    __tablename__ = 'students'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    student_id = db.Column(db.String(20), unique=True, nullable=False)
    admission_number = db.Column(db.String(20), unique=True)
    admission_date = db.Column(db.Date)
    current_class_id = db.Column(db.Integer, db.ForeignKey('classes.id'))
    guardian_name = db.Column(db.String(100))
    guardian_phone = db.Column(db.String(20))
    guardian_email = db.Column(db.String(100))
    guardian_address = db.Column(db.Text)
    emergency_contact = db.Column(db.String(20))
    blood_group = db.Column(db.String(5))
    medical_conditions = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    class_enrollments = db.relationship('ClassEnrollment', backref='student', lazy=True, cascade='all, delete-orphan')
    results = db.relationship('Result', backref='student', lazy=True, cascade='all, delete-orphan')
    term_results_summaries = db.relationship('TermResultSummary', backref='student', lazy=True, cascade='all, delete-orphan')
    parent_relationships = db.relationship('ParentChild', backref='child', lazy=True, cascade='all, delete-orphan')

class ParentChild(db.Model):
    __tablename__ = 'parent_children'
    
    id = db.Column(db.Integer, primary_key=True)
    parent_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    child_id = db.Column(db.Integer, db.ForeignKey('students.id'), nullable=False)
    relationship = db.Column(db.String(20), default='parent')  # parent, guardian, etc.
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    __table_args__ = (db.UniqueConstraint('parent_id', 'child_id', name='unique_parent_child'),)

class ClassEnrollment(db.Model):
    __tablename__ = 'class_enrollments'
    
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('students.id'), nullable=False)
    class_id = db.Column(db.Integer, db.ForeignKey('classes.id'), nullable=False)
    session_id = db.Column(db.Integer, db.ForeignKey('academic_sessions.id'), nullable=False)
    enrollment_date = db.Column(db.Date, nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    __table_args__ = (db.UniqueConstraint('student_id', 'session_id', name='unique_student_session'),)

class Result(db.Model):
    __tablename__ = 'results'
    
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('students.id'), nullable=False)
    class_id = db.Column(db.Integer, db.ForeignKey('classes.id'), nullable=False)
    subject_id = db.Column(db.Integer, db.ForeignKey('subjects.id'), nullable=False)
    term_id = db.Column(db.Integer, db.ForeignKey('terms.id'), nullable=False)
    ca1_score = db.Column(db.Numeric(5, 2), default=0)
    ca2_score = db.Column(db.Numeric(5, 2), default=0)
    exam_score = db.Column(db.Numeric(5, 2), default=0)
    total_score = db.Column(db.Numeric(5, 2))
    grade = db.Column(db.String(2))
    grade_point = db.Column(db.Numeric(3, 2))
    subject_position = db.Column(db.Integer)
    class_average = db.Column(db.Numeric(5, 2))
    teacher_comment = db.Column(db.Text)
    is_submitted = db.Column(db.Boolean, default=False)
    submitted_at = db.Column(db.DateTime)
    submitted_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    __table_args__ = (db.UniqueConstraint('student_id', 'subject_id', 'term_id', name='unique_student_subject_term'),)
    
    def calculate_total_score(self):
        """Calculate total score with weighted percentages: CA1(10%) + CA2(10%) + Exam(80%)"""
        from decimal import Decimal
        ca1_weighted = (self.ca1_score or Decimal('0')) * Decimal('0.1')
        ca2_weighted = (self.ca2_score or Decimal('0')) * Decimal('0.1')
        exam_weighted = (self.exam_score or Decimal('0')) * Decimal('0.8')
        self.total_score = ca1_weighted + ca2_weighted + exam_weighted
        return self.total_score

class TermResultSummary(db.Model):
    __tablename__ = 'term_results_summary'
    
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('students.id'), nullable=False)
    term_id = db.Column(db.Integer, db.ForeignKey('terms.id'), nullable=False)
    total_subjects = db.Column(db.Integer, nullable=False)
    total_score = db.Column(db.Numeric(8, 2), nullable=False)
    average_score = db.Column(db.Numeric(5, 2), nullable=False)
    class_position = db.Column(db.Integer)
    total_students = db.Column(db.Integer)
    attendance_present = db.Column(db.Integer, default=0)
    attendance_absent = db.Column(db.Integer, default=0)
    cognitive_comment = db.Column(db.Text)
    psychomotor_rating = db.Column(db.Enum(Rating), default=Rating.GOOD)
    affective_rating = db.Column(db.Enum(Rating), default=Rating.GOOD)
    class_teacher_comment = db.Column(db.Text)
    principal_comment = db.Column(db.Text)
    promotion_status = db.Column(db.Enum(PromotionStatus), default=PromotionStatus.PENDING)
    next_term_begins = db.Column(db.Date)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    __table_args__ = (db.UniqueConstraint('student_id', 'term_id', name='unique_student_term'),)

class GradingSystem(db.Model):
    __tablename__ = 'grading_systems'
    
    id = db.Column(db.Integer, primary_key=True)
    school_id = db.Column(db.Integer, db.ForeignKey('schools.id'), nullable=False)
    system_name = db.Column(db.String(50), nullable=False)
    is_default = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    grade_scales = db.relationship('GradeScale', backref='grading_system', lazy=True, cascade='all, delete-orphan')

class GradeScale(db.Model):
    __tablename__ = 'grade_scales'
    
    id = db.Column(db.Integer, primary_key=True)
    grading_system_id = db.Column(db.Integer, db.ForeignKey('grading_systems.id'), nullable=False)
    grade = db.Column(db.String(2), nullable=False)
    min_score = db.Column(db.Numeric(5, 2), nullable=False)
    max_score = db.Column(db.Numeric(5, 2), nullable=False)
    grade_point = db.Column(db.Numeric(3, 2), nullable=False)
    description = db.Column(db.String(50))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

# JWT Blacklist for token management
class TokenBlacklist(db.Model):
    __tablename__ = 'token_blacklist'
    
    id = db.Column(db.Integer, primary_key=True)
    jti = db.Column(db.String(36), nullable=False, unique=True)
    token_type = db.Column(db.String(10), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    revoked = db.Column(db.Boolean, default=True)
    expires = db.Column(db.DateTime, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

