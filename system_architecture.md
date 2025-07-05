# Nigerian School Result Portal - System Architecture

## Executive Summary

The Nigerian School Result Portal is a comprehensive web-based application designed to manage academic results for primary and secondary schools across Nigeria. The system provides role-based access for administrators, teachers, students, and parents, with features including result entry, computation, report generation, and performance tracking.

## System Overview

### Architecture Pattern
The system follows a modern three-tier architecture:
- **Presentation Layer**: React.js frontend with responsive design
- **Business Logic Layer**: Flask REST API backend
- **Data Layer**: MySQL database with normalized schema

### Technology Stack

#### Backend Technologies
- **Framework**: Flask (Python)
- **Database**: MySQL 8.0
- **ORM**: SQLAlchemy
- **Authentication**: JWT (JSON Web Tokens)
- **API Documentation**: Flask-RESTX (Swagger)
- **File Processing**: ReportLab for PDF generation
- **Email Service**: Flask-Mail with SMTP

#### Frontend Technologies
- **Framework**: React.js 18
- **State Management**: Redux Toolkit
- **UI Library**: Material-UI (MUI)
- **Styling**: Tailwind CSS
- **Charts**: Chart.js for performance visualization
- **PDF Viewer**: React-PDF

#### Development Tools
- **Version Control**: Git
- **Package Management**: npm (frontend), pip (backend)
- **Testing**: Jest (frontend), pytest (backend)
- **Code Quality**: ESLint, Prettier, Black

## Database Design

### Core Entities and Relationships

The database schema is designed to handle the complex relationships between schools, classes, subjects, students, teachers, and results while maintaining data integrity and supporting the Nigerian educational system structure.

#### Schools Table
```sql
CREATE TABLE schools (
    id INT PRIMARY KEY AUTO_INCREMENT,
    name VARCHAR(255) NOT NULL,
    address TEXT,
    phone VARCHAR(20),
    email VARCHAR(100),
    logo_url VARCHAR(255),
    motto TEXT,
    principal_name VARCHAR(100),
    school_type ENUM('primary', 'secondary', 'both') NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);
```

#### Academic Sessions Table
```sql
CREATE TABLE academic_sessions (
    id INT PRIMARY KEY AUTO_INCREMENT,
    school_id INT NOT NULL,
    session_name VARCHAR(20) NOT NULL, -- e.g., "2024/2025"
    start_date DATE NOT NULL,
    end_date DATE NOT NULL,
    is_active BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (school_id) REFERENCES schools(id) ON DELETE CASCADE
);
```

#### Terms Table
```sql
CREATE TABLE terms (
    id INT PRIMARY KEY AUTO_INCREMENT,
    session_id INT NOT NULL,
    term_number TINYINT NOT NULL CHECK (term_number IN (1, 2, 3)),
    term_name VARCHAR(20) NOT NULL, -- "First Term", "Second Term", "Third Term"
    start_date DATE NOT NULL,
    end_date DATE NOT NULL,
    is_active BOOLEAN DEFAULT FALSE,
    is_locked BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (session_id) REFERENCES academic_sessions(id) ON DELETE CASCADE,
    UNIQUE KEY unique_term_session (session_id, term_number)
);
```

#### Classes Table
```sql
CREATE TABLE classes (
    id INT PRIMARY KEY AUTO_INCREMENT,
    school_id INT NOT NULL,
    class_name VARCHAR(50) NOT NULL, -- "Primary 1", "JSS 1", "SS 2", etc.
    class_level ENUM('primary', 'junior_secondary', 'senior_secondary') NOT NULL,
    class_number TINYINT NOT NULL,
    arm VARCHAR(10), -- "A", "B", "C", etc.
    capacity INT DEFAULT 40,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (school_id) REFERENCES schools(id) ON DELETE CASCADE
);
```

#### Subjects Table
```sql
CREATE TABLE subjects (
    id INT PRIMARY KEY AUTO_INCREMENT,
    school_id INT NOT NULL,
    subject_name VARCHAR(100) NOT NULL,
    subject_code VARCHAR(10),
    is_core BOOLEAN DEFAULT TRUE,
    class_level ENUM('primary', 'junior_secondary', 'senior_secondary') NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (school_id) REFERENCES schools(id) ON DELETE CASCADE
);
```

#### Class Subjects Table (Many-to-Many)
```sql
CREATE TABLE class_subjects (
    id INT PRIMARY KEY AUTO_INCREMENT,
    class_id INT NOT NULL,
    subject_id INT NOT NULL,
    teacher_id INT,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (class_id) REFERENCES classes(id) ON DELETE CASCADE,
    FOREIGN KEY (subject_id) REFERENCES subjects(id) ON DELETE CASCADE,
    FOREIGN KEY (teacher_id) REFERENCES users(id) ON DELETE SET NULL,
    UNIQUE KEY unique_class_subject (class_id, subject_id)
);
```

#### Users Table
```sql
CREATE TABLE users (
    id INT PRIMARY KEY AUTO_INCREMENT,
    school_id INT NOT NULL,
    username VARCHAR(50) UNIQUE NOT NULL,
    email VARCHAR(100) UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    first_name VARCHAR(50) NOT NULL,
    last_name VARCHAR(50) NOT NULL,
    middle_name VARCHAR(50),
    phone VARCHAR(20),
    address TEXT,
    date_of_birth DATE,
    gender ENUM('male', 'female') NOT NULL,
    role ENUM('admin', 'teacher', 'student', 'parent') NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    profile_picture_url VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (school_id) REFERENCES schools(id) ON DELETE CASCADE
);
```

#### Students Table (Extended User Information)
```sql
CREATE TABLE students (
    id INT PRIMARY KEY AUTO_INCREMENT,
    user_id INT NOT NULL,
    student_id VARCHAR(20) UNIQUE NOT NULL,
    admission_number VARCHAR(20) UNIQUE,
    admission_date DATE,
    current_class_id INT,
    guardian_name VARCHAR(100),
    guardian_phone VARCHAR(20),
    guardian_email VARCHAR(100),
    guardian_address TEXT,
    emergency_contact VARCHAR(20),
    blood_group VARCHAR(5),
    medical_conditions TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (current_class_id) REFERENCES classes(id) ON DELETE SET NULL
);
```

#### Class Enrollments Table
```sql
CREATE TABLE class_enrollments (
    id INT PRIMARY KEY AUTO_INCREMENT,
    student_id INT NOT NULL,
    class_id INT NOT NULL,
    session_id INT NOT NULL,
    enrollment_date DATE NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (student_id) REFERENCES students(id) ON DELETE CASCADE,
    FOREIGN KEY (class_id) REFERENCES classes(id) ON DELETE CASCADE,
    FOREIGN KEY (session_id) REFERENCES academic_sessions(id) ON DELETE CASCADE,
    UNIQUE KEY unique_student_session (student_id, session_id)
);
```

#### Results Table
```sql
CREATE TABLE results (
    id INT PRIMARY KEY AUTO_INCREMENT,
    student_id INT NOT NULL,
    class_id INT NOT NULL,
    subject_id INT NOT NULL,
    term_id INT NOT NULL,
    ca1_score DECIMAL(5,2) DEFAULT 0,
    ca2_score DECIMAL(5,2) DEFAULT 0,
    exam_score DECIMAL(5,2) DEFAULT 0,
    total_score DECIMAL(5,2) GENERATED ALWAYS AS (ca1_score + ca2_score + exam_score) STORED,
    grade VARCHAR(2),
    grade_point DECIMAL(3,2),
    subject_position INT,
    class_average DECIMAL(5,2),
    teacher_comment TEXT,
    is_submitted BOOLEAN DEFAULT FALSE,
    submitted_at TIMESTAMP NULL,
    submitted_by INT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (student_id) REFERENCES students(id) ON DELETE CASCADE,
    FOREIGN KEY (class_id) REFERENCES classes(id) ON DELETE CASCADE,
    FOREIGN KEY (subject_id) REFERENCES subjects(id) ON DELETE CASCADE,
    FOREIGN KEY (term_id) REFERENCES terms(id) ON DELETE CASCADE,
    FOREIGN KEY (submitted_by) REFERENCES users(id) ON DELETE SET NULL,
    UNIQUE KEY unique_student_subject_term (student_id, subject_id, term_id)
);
```

#### Term Results Summary Table
```sql
CREATE TABLE term_results_summary (
    id INT PRIMARY KEY AUTO_INCREMENT,
    student_id INT NOT NULL,
    term_id INT NOT NULL,
    total_subjects INT NOT NULL,
    total_score DECIMAL(8,2) NOT NULL,
    average_score DECIMAL(5,2) NOT NULL,
    class_position INT,
    total_students INT,
    attendance_present INT DEFAULT 0,
    attendance_absent INT DEFAULT 0,
    cognitive_comment TEXT,
    psychomotor_rating ENUM('excellent', 'very_good', 'good', 'fair', 'poor') DEFAULT 'good',
    affective_rating ENUM('excellent', 'very_good', 'good', 'fair', 'poor') DEFAULT 'good',
    class_teacher_comment TEXT,
    principal_comment TEXT,
    promotion_status ENUM('promoted', 'repeated', 'pending') DEFAULT 'pending',
    next_term_begins DATE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (student_id) REFERENCES students(id) ON DELETE CASCADE,
    FOREIGN KEY (term_id) REFERENCES terms(id) ON DELETE CASCADE,
    UNIQUE KEY unique_student_term (student_id, term_id)
);
```

#### Grading Systems Table
```sql
CREATE TABLE grading_systems (
    id INT PRIMARY KEY AUTO_INCREMENT,
    school_id INT NOT NULL,
    system_name VARCHAR(50) NOT NULL,
    is_default BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (school_id) REFERENCES schools(id) ON DELETE CASCADE
);
```

#### Grade Scales Table
```sql
CREATE TABLE grade_scales (
    id INT PRIMARY KEY AUTO_INCREMENT,
    grading_system_id INT NOT NULL,
    grade VARCHAR(2) NOT NULL,
    min_score DECIMAL(5,2) NOT NULL,
    max_score DECIMAL(5,2) NOT NULL,
    grade_point DECIMAL(3,2) NOT NULL,
    description VARCHAR(50),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (grading_system_id) REFERENCES grading_systems(id) ON DELETE CASCADE
);
```

### Database Indexes for Performance

```sql
-- Performance indexes
CREATE INDEX idx_results_student_term ON results(student_id, term_id);
CREATE INDEX idx_results_class_subject ON results(class_id, subject_id);
CREATE INDEX idx_users_school_role ON users(school_id, role);
CREATE INDEX idx_students_admission ON students(admission_number);
CREATE INDEX idx_class_enrollments_active ON class_enrollments(is_active, session_id);
```

## API Design

### RESTful API Endpoints

The API follows REST principles with consistent naming conventions and HTTP methods. All endpoints return JSON responses with standardized error handling.

#### Authentication Endpoints
```
POST /api/auth/login
POST /api/auth/logout
POST /api/auth/refresh
POST /api/auth/forgot-password
POST /api/auth/reset-password
```

#### Admin Management Endpoints
```
GET /api/admin/dashboard
GET /api/admin/schools
POST /api/admin/schools
PUT /api/admin/schools/{id}
DELETE /api/admin/schools/{id}

GET /api/admin/sessions
POST /api/admin/sessions
PUT /api/admin/sessions/{id}
DELETE /api/admin/sessions/{id}

GET /api/admin/terms
POST /api/admin/terms
PUT /api/admin/terms/{id}
DELETE /api/admin/terms/{id}

GET /api/admin/classes
POST /api/admin/classes
PUT /api/admin/classes/{id}
DELETE /api/admin/classes/{id}

GET /api/admin/subjects
POST /api/admin/subjects
PUT /api/admin/subjects/{id}
DELETE /api/admin/subjects/{id}

GET /api/admin/users
POST /api/admin/users
PUT /api/admin/users/{id}
DELETE /api/admin/users/{id}

GET /api/admin/grading-systems
POST /api/admin/grading-systems
PUT /api/admin/grading-systems/{id}
DELETE /api/admin/grading-systems/{id}
```

#### Teacher Portal Endpoints
```
GET /api/teacher/dashboard
GET /api/teacher/classes
GET /api/teacher/classes/{id}/students
GET /api/teacher/classes/{id}/subjects

GET /api/teacher/results
POST /api/teacher/results/batch
PUT /api/teacher/results/{id}
POST /api/teacher/results/submit

GET /api/teacher/students/{id}/history
POST /api/teacher/comments
```

#### Student Portal Endpoints
```
GET /api/student/dashboard
GET /api/student/profile
PUT /api/student/profile

GET /api/student/results
GET /api/student/results/{term_id}
GET /api/student/results/history
GET /api/student/performance-chart

POST /api/student/results/download-pdf
```

#### Parent Portal Endpoints
```
GET /api/parent/dashboard
GET /api/parent/children
GET /api/parent/children/{id}/results
GET /api/parent/children/{id}/results/{term_id}
GET /api/parent/children/{id}/performance-chart

POST /api/parent/children/{id}/results/download-pdf
GET /api/parent/notifications
```

#### Report Generation Endpoints
```
POST /api/reports/student-report-card
POST /api/reports/class-summary
POST /api/reports/subject-analysis
POST /api/reports/performance-trends
POST /api/reports/bulk-download
```

### API Response Format

All API responses follow a consistent format:

```json
{
    "success": true,
    "message": "Operation completed successfully",
    "data": {
        // Response data here
    },
    "meta": {
        "timestamp": "2024-12-30T10:30:00Z",
        "version": "1.0.0"
    }
}
```

Error responses:
```json
{
    "success": false,
    "message": "Validation error",
    "errors": [
        {
            "field": "email",
            "message": "Email is required"
        }
    ],
    "meta": {
        "timestamp": "2024-12-30T10:30:00Z",
        "version": "1.0.0"
    }
}
```

## Security Architecture

### Authentication and Authorization

The system implements a robust security model with role-based access control (RBAC) and JWT-based authentication.

#### Role Hierarchy
1. **Super Admin**: System-wide access across all schools
2. **School Admin**: Full access within their school
3. **Teacher**: Access to assigned classes and subjects
4. **Student**: Access to personal academic records
5. **Parent**: Access to their children's records

#### JWT Token Structure
```json
{
    "user_id": 123,
    "school_id": 1,
    "role": "teacher",
    "permissions": ["read_results", "write_results"],
    "exp": 1640995200,
    "iat": 1640908800
}
```

#### Permission Matrix

| Feature | Super Admin | School Admin | Teacher | Student | Parent |
|---------|-------------|--------------|---------|---------|---------|
| Manage Schools | ✓ | ✗ | ✗ | ✗ | ✗ |
| Manage Classes | ✓ | ✓ | ✗ | ✗ | ✗ |
| Manage Subjects | ✓ | ✓ | ✗ | ✗ | ✗ |
| Manage Users | ✓ | ✓ | ✗ | ✗ | ✗ |
| Enter Results | ✗ | ✓ | ✓ | ✗ | ✗ |
| View Own Results | ✗ | ✗ | ✗ | ✓ | ✗ |
| View Child Results | ✗ | ✗ | ✗ | ✗ | ✓ |
| Generate Reports | ✓ | ✓ | ✓ | ✓ | ✓ |

### Data Security Measures

#### Encryption
- All passwords are hashed using bcrypt with salt rounds of 12
- Sensitive data is encrypted at rest using AES-256
- All communications use HTTPS/TLS 1.3

#### Input Validation
- Server-side validation for all API endpoints
- SQL injection prevention through parameterized queries
- XSS protection through input sanitization
- CSRF protection using tokens

#### Access Control
- Rate limiting on authentication endpoints
- Session timeout after 30 minutes of inactivity
- IP-based access restrictions for admin accounts
- Audit logging for all sensitive operations

## System Integration Points

### External Services Integration

#### SMS Gateway Integration
For sending results and notifications to parents:
```python
class SMSService:
    def __init__(self, api_key, sender_id):
        self.api_key = api_key
        self.sender_id = sender_id
    
    def send_result_notification(self, phone_number, student_name, term):
        message = f"Dear Parent, {student_name}'s {term} results are now available. Login to view: https://portal.school.ng"
        return self.send_sms(phone_number, message)
```

#### Email Service Integration
For sending detailed reports and notifications:
```python
class EmailService:
    def __init__(self, smtp_config):
        self.smtp_config = smtp_config
    
    def send_result_email(self, parent_email, student_name, term, pdf_attachment):
        subject = f"{student_name} - {term} Academic Report"
        body = self.render_email_template('result_notification.html', {
            'student_name': student_name,
            'term': term
        })
        return self.send_email(parent_email, subject, body, [pdf_attachment])
```

#### Cloud Storage Integration
For storing report cards and documents:
```python
class CloudStorageService:
    def __init__(self, cloud_provider='aws_s3'):
        self.provider = cloud_provider
    
    def upload_report_card(self, student_id, term_id, pdf_file):
        file_path = f"reports/{student_id}/{term_id}/report_card.pdf"
        return self.upload_file(pdf_file, file_path)
```

### Performance Optimization

#### Caching Strategy
- Redis for session storage and frequently accessed data
- Database query result caching for static data
- CDN for static assets and generated reports

#### Database Optimization
- Proper indexing on frequently queried columns
- Query optimization for report generation
- Database connection pooling
- Read replicas for reporting queries

## Deployment Architecture

### Development Environment
- Local development using Docker containers
- MySQL database container
- Redis container for caching
- Flask development server
- React development server with hot reload

### Production Environment
- Load balancer (Nginx) for high availability
- Multiple application server instances
- Master-slave MySQL database setup
- Redis cluster for caching and sessions
- File storage service for documents and images
- Monitoring and logging services

### Scalability Considerations
- Horizontal scaling of application servers
- Database sharding by school_id for large deployments
- Microservices architecture for future expansion
- API rate limiting and throttling
- Automated backup and disaster recovery

This comprehensive architecture provides a solid foundation for building a robust, scalable, and secure school result portal that can handle the complex requirements of Nigerian educational institutions while maintaining high performance and reliability.

