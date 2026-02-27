from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

# Initialize SQLAlchemy
db = SQLAlchemy()

# --- USER MODEL ---
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=True) 
    email = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False) 
    role = db.Column(db.String(20), nullable=False)  # 'student' or 'admin'

    student_uid = db.Column(db.String(30), unique=True, nullable=True)

    mobile_number = db.Column(db.String(30), nullable=True)
    date_of_birth = db.Column(db.String(20), nullable=True)
    institution = db.Column(db.String(200), nullable=True)

    course = db.Column(db.String(200), nullable=True)
    semester = db.Column(db.String(50), nullable=True)
    cgpa = db.Column(db.String(20), nullable=True)

    id_proof_path = db.Column(db.String(300), nullable=True)
    face_image_path = db.Column(db.String(300), nullable=True)

    proctoring_consent = db.Column(db.Boolean, default=False)
    terms_accepted = db.Column(db.Boolean, default=False)
    registration_complete = db.Column(db.Boolean, default=False)

    def to_dict(self):
        return {
            'id': self.id,
            'student_uid': self.student_uid,
            'name': self.name,
            'email': self.email,
            'role': self.role,
            'registration_complete': self.registration_complete
        }

# --- PASSWORD OTP MODEL ---
class PasswordOTP(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    otp_hash = db.Column(db.String(200), nullable=False)
    expires_at = db.Column(db.DateTime, nullable=False)
    used = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    user = db.relationship('User', backref='password_otps')

# --- EXAM MODELS ---
class Exam(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=True)
    duration_minutes = db.Column(db.Integer, nullable=True)
    total_marks = db.Column(db.Integer, default=0)
    pass_percentage = db.Column(db.Float, default=40.0)
    is_active = db.Column(db.Boolean, default=True)
    allow_reattempt = db.Column(db.Boolean, default=False)
    reattempt_after_days = db.Column(db.Integer, nullable=True)
    available_from = db.Column(db.Date, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

class ExamQuestion(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    exam_id = db.Column(db.Integer, db.ForeignKey('exam.id'), nullable=False)
    question_text = db.Column(db.Text, nullable=False)
    option_a = db.Column(db.Text, nullable=False)
    option_b = db.Column(db.Text, nullable=False)
    option_c = db.Column(db.Text, nullable=False)
    option_d = db.Column(db.Text, nullable=False)
    correct_option = db.Column(db.Integer, nullable=False)  # 0=A,1=B,2=C,3=D
    marks = db.Column(db.Integer, default=1)
    order_index = db.Column(db.Integer, default=0)

    exam = db.relationship('Exam', backref='questions')

# --- EXAM SESSION MODEL ---
class ExamSession(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    exam_id = db.Column(db.Integer, db.ForeignKey('exam.id'), nullable=True)
    start_time = db.Column(db.DateTime, default=datetime.utcnow)
    end_time = db.Column(db.DateTime, nullable=True)
    status = db.Column(db.String(20), default='Active') # Active, Completed, Terminated
    warnings_count = db.Column(db.Integer, default=0)
    cheating_status = db.Column(db.Boolean, default=False)

    obtained_marks = db.Column(db.Integer, nullable=True)
    total_marks = db.Column(db.Integer, nullable=True)
    percentage = db.Column(db.Float, nullable=True)
    result_status = db.Column(db.String(20), nullable=True)  # Passed / Failed
    submitted_at = db.Column(db.DateTime, nullable=True)

    results_published = db.Column(db.Boolean, default=True)

    exam = db.relationship('Exam', backref='sessions')
    user = db.relationship('User', backref='exam_sessions')
    
    # Relationship to warnings
    warnings = db.relationship('Warning', backref='session', lazy=True)

# --- WARNING MODEL ---
class Warning(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.Integer, db.ForeignKey('exam_session.id'), nullable=False)
    violation_type = db.Column(db.String(100), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

# --- LOGIN ACTIVITY MODEL ---
class LoginActivity(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    email = db.Column(db.String(100), nullable=False)
    login_time = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    user = db.relationship('User', backref='login_activities')

class ExamResponse(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.Integer, db.ForeignKey('exam_session.id'), nullable=False)
    question_id = db.Column(db.Integer, db.ForeignKey('exam_question.id'), nullable=False)
    selected_option = db.Column(db.Integer, nullable=True)
    is_correct = db.Column(db.Boolean, default=False)
    marks_awarded = db.Column(db.Integer, default=0)

    session = db.relationship('ExamSession', backref='responses')
    question = db.relationship('ExamQuestion')