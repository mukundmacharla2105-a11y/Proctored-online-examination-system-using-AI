from flask import Flask, render_template, request, jsonify, redirect, url_for, session, send_from_directory, abort, make_response
from flask_socketio import SocketIO, emit
from flask_cors import CORS
from models import db, User, Exam, ExamQuestion, ExamSession, ExamResponse, Warning, LoginActivity, PasswordOTP
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from sqlalchemy import text
import os
import eventlet
from proctor import ProctorEngine
import secrets
import base64
from datetime import timedelta
from io import BytesIO
import csv

from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm

# Initialize App
app = Flask(__name__, template_folder='templates', static_folder='static')
app.config['SECRET_KEY'] = 'proctor_secret_key_123'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Enable CORS with credentials support
CORS(app, supports_credentials=True)
db.init_app(app)
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='eventlet')

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_DIR = os.path.join(BASE_DIR, 'uploads')
os.makedirs(UPLOAD_DIR, exist_ok=True)


def _get_existing_columns(table_name: str):
    try:
        rows = db.session.execute(text(f"PRAGMA table_info({table_name})")).fetchall()
        return {r[1] for r in rows}
    except Exception:
        return set()


def ensure_sqlite_schema():
    """Minimal schema upgrader (SQLite) for added columns without migrations."""
    try:
        existing = _get_existing_columns('user')
        if existing:
            alters = []
            if 'student_uid' not in existing:
                alters.append("ALTER TABLE user ADD COLUMN student_uid VARCHAR(30)")
            if 'mobile_number' not in existing:
                alters.append("ALTER TABLE user ADD COLUMN mobile_number VARCHAR(30)")
            if 'date_of_birth' not in existing:
                alters.append("ALTER TABLE user ADD COLUMN date_of_birth VARCHAR(20)")
            if 'institution' not in existing:
                alters.append("ALTER TABLE user ADD COLUMN institution VARCHAR(200)")
            if 'course' not in existing:
                alters.append("ALTER TABLE user ADD COLUMN course VARCHAR(200)")
            if 'semester' not in existing:
                alters.append("ALTER TABLE user ADD COLUMN semester VARCHAR(50)")
            if 'cgpa' not in existing:
                alters.append("ALTER TABLE user ADD COLUMN cgpa VARCHAR(20)")
            if 'id_proof_path' not in existing:
                alters.append("ALTER TABLE user ADD COLUMN id_proof_path VARCHAR(300)")
            if 'face_image_path' not in existing:
                alters.append("ALTER TABLE user ADD COLUMN face_image_path VARCHAR(300)")
            if 'proctoring_consent' not in existing:
                alters.append("ALTER TABLE user ADD COLUMN proctoring_consent BOOLEAN DEFAULT 0")
            if 'terms_accepted' not in existing:
                alters.append("ALTER TABLE user ADD COLUMN terms_accepted BOOLEAN DEFAULT 0")
            if 'registration_complete' not in existing:
                alters.append("ALTER TABLE user ADD COLUMN registration_complete BOOLEAN DEFAULT 0")

            for stmt in alters:
                db.session.execute(text(stmt))
            db.session.commit()

        existing_exam_cols = _get_existing_columns('exam')
        if existing_exam_cols:
            alters = []
            if 'allow_reattempt' not in existing_exam_cols:
                alters.append("ALTER TABLE exam ADD COLUMN allow_reattempt BOOLEAN DEFAULT 0")
            if 'reattempt_after_days' not in existing_exam_cols:
                alters.append("ALTER TABLE exam ADD COLUMN reattempt_after_days INTEGER")
            if 'available_from' not in existing_exam_cols:
                alters.append("ALTER TABLE exam ADD COLUMN available_from DATE")

            for stmt in alters:
                db.session.execute(text(stmt))
            db.session.commit()

        existing_session_cols = _get_existing_columns('exam_session')
        if existing_session_cols:
            alters = []
            if 'exam_id' not in existing_session_cols:
                alters.append("ALTER TABLE exam_session ADD COLUMN exam_id INTEGER")
            if 'obtained_marks' not in existing_session_cols:
                alters.append("ALTER TABLE exam_session ADD COLUMN obtained_marks INTEGER")
            if 'total_marks' not in existing_session_cols:
                alters.append("ALTER TABLE exam_session ADD COLUMN total_marks INTEGER")
            if 'percentage' not in existing_session_cols:
                alters.append("ALTER TABLE exam_session ADD COLUMN percentage FLOAT")
            if 'result_status' not in existing_session_cols:
                alters.append("ALTER TABLE exam_session ADD COLUMN result_status VARCHAR(20)")
            if 'submitted_at' not in existing_session_cols:
                alters.append("ALTER TABLE exam_session ADD COLUMN submitted_at DATETIME")
            if 'results_published' not in existing_session_cols:
                alters.append("ALTER TABLE exam_session ADD COLUMN results_published BOOLEAN DEFAULT 1")

            for stmt in alters:
                db.session.execute(text(stmt))
            db.session.commit()
    except Exception:
        db.session.rollback()


def _seed_default_exam_if_missing():
    existing = Exam.query.count()
    if existing:
        return

    exam = Exam(
        name='AI Proctored Exam',
        description='Default seeded exam',
        duration_minutes=30,
        total_marks=5,
        pass_percentage=40.0,
        is_active=True,
    )
    db.session.add(exam)
    db.session.flush()

    seeded_questions = [
        {
            'question_text': 'What is 2 + 2?',
            'option_a': '3',
            'option_b': '4',
            'option_c': '5',
            'option_d': '6',
            'correct_option': 1,
            'marks': 1,
        },
        {
            'question_text': 'HTML stands for?',
            'option_a': 'Hyper Text Markup Language',
            'option_b': 'High Text',
            'option_c': 'Hyper Tabular',
            'option_d': 'None',
            'correct_option': 0,
            'marks': 1,
        },
        {
            'question_text': 'Which is a Python keyword?',
            'option_a': 'function',
            'option_b': 'def',
            'option_c': 'var',
            'option_d': 'let',
            'correct_option': 1,
            'marks': 1,
        },
        {
            'question_text': 'CSS is used for?',
            'option_a': 'Structure',
            'option_b': 'Database',
            'option_c': 'Styling',
            'option_d': 'Logic',
            'correct_option': 2,
            'marks': 1,
        },
        {
            'question_text': 'Is Python compiled?',
            'option_a': 'Yes',
            'option_b': 'No, Interpreted',
            'option_c': 'Both',
            'option_d': 'None',
            'correct_option': 1,
            'marks': 1,
        },
    ]

    for i, q in enumerate(seeded_questions):
        db.session.add(
            ExamQuestion(
                exam_id=exam.id,
                order_index=i,
                **q,
            )
        )

    db.session.commit()


def _safe_basename(path_value: str) -> str:
    if not path_value:
        return ''
    try:
        return os.path.basename(path_value)
    except Exception:
        return ''


def _save_upload(file_storage, prefix: str) -> str:
    filename = secure_filename(file_storage.filename or '')
    ext = os.path.splitext(filename)[1].lower()
    if ext not in ['.png', '.jpg', '.jpeg', '.pdf']:
        raise ValueError('Invalid file type')

    token = secrets.token_hex(16)
    out_name = f"{prefix}_{token}{ext}"
    out_path = os.path.join(UPLOAD_DIR, out_name)
    file_storage.save(out_path)
    return out_path


def _save_face_data_url(data_url: str) -> str:
    if not data_url or ',' not in data_url:
        raise ValueError('Invalid face capture')
    header, b64 = data_url.split(',', 1)
    if 'image' not in header:
        raise ValueError('Invalid face capture')

    raw = base64.b64decode(b64)
    token = secrets.token_hex(16)
    out_name = f"face_{token}.jpg"
    out_path = os.path.join(UPLOAD_DIR, out_name)
    with open(out_path, 'wb') as f:
        f.write(raw)
    return out_path


def _send_otp_email(to_email: str, otp_code: str) -> bool:
    """Send OTP via SMTP. If SMTP env vars missing, log to console and return True."""
    host = os.environ.get('SMTP_HOST')
    port = os.environ.get('SMTP_PORT')
    user = os.environ.get('SMTP_USER')
    password = os.environ.get('SMTP_PASS')
    from_email = os.environ.get('SMTP_FROM') or user

    if not host or not port or not user or not password or not from_email:
        print(f"DEV OTP for {to_email}: {otp_code}")
        return True

    import smtplib
    from email.mime.text import MIMEText

    msg = MIMEText(
        f"Your ProctorExam.AI OTP is: {otp_code}\n\nThis code expires in 10 minutes.",
        'plain',
        'utf-8',
    )
    msg['Subject'] = 'ProctorExam.AI - Password Reset OTP'
    msg['From'] = from_email
    msg['To'] = to_email

    with smtplib.SMTP(host, int(port)) as server:
        server.starttls()
        server.login(user, password)
        server.sendmail(from_email, [to_email], msg.as_string())
    return True


# --- Lazy Loading AI to prevent setup crashes ---
proctor = None

# Lightweight proctoring engine + in-memory per-session state
proctor_engine = ProctorEngine()
proctor_session_state = {}

def get_proctor():
    global proctor
    if proctor is None:
        try:
            from ai_proctor import AIProctor
            proctor = AIProctor()
            print("✅ AI Proctor Module Loaded Successfully")
        except Exception as e:
            print(f"⚠️  AI Module Error: {e}")
            proctor = None
    return proctor


# --- Routes ---

@app.route('/')
def root():
    return render_template('home.html')

@app.route('/home')
@app.route('/home.html')
def home():
    return render_template('home.html')

# --- LOGIN ROUTE ---
@app.route('/login', methods=['GET', 'POST'])
@app.route('/login.html', methods=['GET', 'POST'])
def login():
    if request.path == '/login.html' and request.method == 'GET':
        session.clear()

    if request.method == 'POST':
        email = ""
        password = ""

        # 1. Handle JSON (Fetch API)
        if request.is_json:
            data = request.get_json()
            email = data.get('email')
            if email:
                email = email.strip().lower()

            password = data.get('password')
        # 2. Handle HTML Form
        else:
            email = request.form.get('email')
            if email:
                email = email.strip().lower()

            password = request.form.get('password')

        # 3. Sanitize
        if password:
            password = password.strip()

        # Database Lookup
        user = User.query.filter_by(email=email).first()

        # 4. Verify Password
        if user and check_password_hash(user.password, password): 
            session['user_id'] = user.id
            session['role'] = user.role

            if user.role == 'student' and not user.student_uid:
                year = datetime.utcnow().year
                user.student_uid = f"STD-{year}-{str(user.id).zfill(6)}"
                db.session.add(user)
            
            # Record activity
            login_entry = LoginActivity(user_id=user.id, email=email)
            db.session.add(login_entry)
            db.session.commit()
            
            target_url = url_for('admin_dashboard') if user.role == 'admin' else url_for('student_dashboard')

            if request.is_json:
                return jsonify({'success': True, 'redirect': target_url, 'user': user.to_dict()})

            return redirect(target_url)
            
        # Failure
        if request.is_json:
            return jsonify({'success': False, 'message': 'Invalid email or password'}), 401
        
        return render_template('login.html', error="Invalid credentials")
            
    return render_template('login.html')

# --- REGISTER ROUTE ---
@app.route('/register', methods=['GET', 'POST'])
@app.route('/register.html', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        first_name = ""
        last_name = ""
        email = ""
        password = ""

        mobile_number = ""
        date_of_birth = ""
        institution = ""
        proctoring_consent = False
        terms_accepted = False


        # 1. Handle JSON (Fetch API)
        if request.is_json:
            data = request.get_json()
            first_name = data.get('first_name', '')
            last_name = data.get('last_name', '')
            email = data.get('email')
            if email:
                email = email.strip().lower()

            password = data.get('password')

            mobile_number = (data.get('mobile_number') or '').strip()
            date_of_birth = (data.get('date_of_birth') or '').strip()
            institution = (data.get('institution') or '').strip()
            proctoring_consent = bool(data.get('proctoring_consent'))
            terms_accepted = bool(data.get('terms_accepted'))
        # 2. Handle HTML Form
        else:
            first_name = request.form.get('first_name', '')
            last_name = request.form.get('last_name', '')
            email = request.form.get('email')
            if email:
                email = email.strip().lower()

            password = request.form.get('password')

            mobile_number = (request.form.get('mobile_number') or '').strip()
            date_of_birth = (request.form.get('date_of_birth') or '').strip()
            institution = (request.form.get('institution') or '').strip()
            proctoring_consent = request.form.get('proctoring_consent') == 'on'
            terms_accepted = request.form.get('terms_accepted') == 'on'


        # 3. Sanitize
        if password:
            password = password.strip()

        # Validation
        if not email or not password:
            msg = 'Email and password are required'
            if request.is_json:
                return jsonify({'success': False, 'message': msg}), 400
            return render_template('register.html', error=msg)

        if len(password) < 6:
            msg = 'Password must be at least 6 characters'
            if request.is_json:
                return jsonify({'success': False, 'message': msg}), 400
            return render_template('register.html', error=msg)

        if not mobile_number or not date_of_birth or not institution:
            msg = 'All fields are required'
            if request.is_json:
                return jsonify({'success': False, 'message': msg}), 400
            return render_template('register.html', error=msg)

        if not proctoring_consent or not terms_accepted:
            msg = 'Consent and Terms acceptance are required'
            if request.is_json:
                return jsonify({'success': False, 'message': msg}), 400
            return render_template('register.html', error=msg)


        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            msg = 'Email already registered'
            if request.is_json:
                return jsonify({'success': False, 'message': msg}), 400
            return render_template('register.html', error=msg)

        id_proof_path = None
        face_image_path = None

        if not request.is_json:
            try:
                id_proof = request.files.get('id_proof')
                if not id_proof or not id_proof.filename:
                    msg = 'ID proof upload is required'
                    return render_template('register.html', error=msg)
                id_proof_path = _save_upload(id_proof, 'idproof')

                face_data = (request.form.get('face_image_data') or '').strip()
                if not face_data:
                    msg = 'Webcam photo capture is required'
                    return render_template('register.html', error=msg)
                face_image_path = _save_face_data_url(face_data)
            except Exception:
                msg = 'Invalid ID proof or face capture'
                return render_template('register.html', error=msg)

        # 4. Create User (Hash Password)
        hashed_password = generate_password_hash(password, method='pbkdf2:sha256')


        new_user = User(
            name=f"{first_name} {last_name}".strip(),
            email=email,
            password=hashed_password,
            role='student',
            mobile_number=mobile_number,
            date_of_birth=date_of_birth,
            institution=institution,
            id_proof_path=id_proof_path,
            face_image_path=face_image_path,
            proctoring_consent=bool(proctoring_consent),
            terms_accepted=bool(terms_accepted),
            registration_complete=True
        )

        try:
            db.session.add(new_user)
            db.session.commit()

            if request.is_json:
                return jsonify({'success': True, 'redirect': url_for('login')})
            return redirect(url_for('login'))
        except Exception as e:
            db.session.rollback()
            print(f"Database Error: {e}")
            if request.is_json:
                return jsonify({'success': False, 'message': 'Database error'}), 500
            return render_template('register.html', error="Registration failed")

    return render_template('register.html')

@app.route('/forgot-password/request', methods=['POST'])
def forgot_password_request():
    data = request.get_json(silent=True) or {}
    email = (data.get('email') or '').strip().lower()
    if not email:
        return jsonify({'success': False, 'message': 'Email is required'}), 400

    user = User.query.filter_by(email=email).first()
    if not user or user.role != 'student':
        return jsonify({'success': True, 'message': 'If the email exists, an OTP has been sent.'})

    otp_code = ''.join(str(secrets.randbelow(10)) for _ in range(6))
    otp_hash = generate_password_hash(otp_code, method='pbkdf2:sha256')
    expires_at = datetime.utcnow() + timedelta(minutes=10)

    rec = PasswordOTP(user_id=user.id, otp_hash=otp_hash, expires_at=expires_at, used=False)
    db.session.add(rec)
    db.session.commit()

    _send_otp_email(email, otp_code)
    return jsonify({'success': True, 'message': 'If the email exists, an OTP has been sent.'})

@app.route('/forgot-password/verify', methods=['POST'])
def forgot_password_verify():
    data = request.get_json(silent=True) or {}
    email = (data.get('email') or '').strip().lower()
    otp = (data.get('otp') or '').strip()
    if not email or not otp:
        return jsonify({'success': False, 'message': 'Email and OTP are required'}), 400

    user = User.query.filter_by(email=email).first()
    if not user:
        return jsonify({'success': False, 'message': 'Invalid or expired OTP'}), 400

    rec = PasswordOTP.query.filter_by(user_id=user.id, used=False).order_by(PasswordOTP.created_at.desc()).first()
    if not rec or rec.expires_at < datetime.utcnow() or not check_password_hash(rec.otp_hash, otp):
        return jsonify({'success': False, 'message': 'Invalid or expired OTP'}), 400

    return jsonify({'success': True, 'message': 'OTP verified'})

@app.route('/forgot-password/reset', methods=['POST'])
def forgot_password_reset():
    data = request.get_json(silent=True) or {}
    email = (data.get('email') or '').strip().lower()
    otp = (data.get('otp') or '').strip()
    new_password = (data.get('new_password') or '').strip()
    if not email or not otp or not new_password:
        return jsonify({'success': False, 'message': 'Email, OTP, and new password are required'}), 400

    if len(new_password) < 6:
        return jsonify({'success': False, 'message': 'Password must be at least 6 characters'}), 400

    user = User.query.filter_by(email=email).first()
    if not user:
        return jsonify({'success': False, 'message': 'Invalid or expired OTP'}), 400

    rec = PasswordOTP.query.filter_by(user_id=user.id, used=False).order_by(PasswordOTP.created_at.desc()).first()
    if not rec or rec.expires_at < datetime.utcnow() or not check_password_hash(rec.otp_hash, otp):
        return jsonify({'success': False, 'message': 'Invalid or expired OTP'}), 400

    rec.used = True
    user.password = generate_password_hash(new_password, method='pbkdf2:sha256')
    db.session.commit()

    return jsonify({'success': True, 'message': 'Password updated successfully'})

# --- ADMIN LOGIN ROUTE ---
@app.route('/admin_login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':

        email = request.form.get('email')
        password = request.form.get('password')

        # Sanitize
        if email:
            email = email.strip().lower()
        if password:
            password = password.strip()

        # Only check admin users
        user = User.query.filter_by(email=email, role='admin').first()

        if user and check_password_hash(user.password, password):

            session['user_id'] = user.id
            session['role'] = 'admin'

            # Log activity (optional)
            login_entry = LoginActivity(user_id=user.id, email=email)
            db.session.add(login_entry)
            db.session.commit()

            return redirect(url_for('admin_dashboard'))

        return render_template(
            'admin_login.html',
            error="Invalid Admin Credentials"
        )

    return render_template('admin_login.html')


@app.route('/uploads/<path:filename>')
def uploaded_file(filename: str):
    if 'user_id' not in session:
        abort(401)

    filename = os.path.basename(filename)
    if not filename:
        abort(404)

    user = User.query.get(session['user_id'])
    if not user:
        abort(401)

    if session.get('role') != 'admin':
        allowed = {
            _safe_basename(user.face_image_path),
            _safe_basename(user.id_proof_path),
        }
        if filename not in allowed:
            abort(403)

    return send_from_directory(UPLOAD_DIR, filename, as_attachment=False)


@app.route('/student_dashboard')
@app.route('/student_dashboard.html')
def student_dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    user = User.query.get(session['user_id'])
    if not user or user.role != 'student':
        return redirect(url_for('login'))

    exams = Exam.query.filter_by(is_active=True).order_by(Exam.created_at.desc()).all()
    upcoming_exam = exams[0] if exams else None

    def _exam_access_for_user(exam_obj: Exam, user_obj: User):
        now = datetime.utcnow()
        today = now.date()

        available_from = getattr(exam_obj, 'available_from', None)
        if available_from and today < available_from:
            return {
                'allowed': False,
                'badge_text': f"Available after {available_from.strftime('%b %d, %Y')}",
            }

        last = (
            ExamSession.query
            .filter_by(user_id=user_obj.id, exam_id=exam_obj.id)
            .filter(ExamSession.status == 'Completed')
            .filter(ExamSession.submitted_at.isnot(None))
            .order_by(ExamSession.submitted_at.desc())
            .first()
        )

        if not last:
            return {'allowed': True, 'badge_text': 'Available now'}

        allow_reattempt = bool(getattr(exam_obj, 'allow_reattempt', False))
        if not allow_reattempt:
            return {'allowed': False, 'badge_text': 'Single attempt completed'}

        days = getattr(exam_obj, 'reattempt_after_days', None)
        try:
            days = int(days) if days is not None else None
        except Exception:
            days = None
        if not days or days <= 0:
            return {'allowed': True, 'badge_text': 'Available now'}

        last_date = (last.submitted_at or last.end_time or last.start_time)
        last_day = last_date.date() if last_date else today
        unlock_day = last_day + timedelta(days=days)
        if today < unlock_day:
            return {'allowed': False, 'badge_text': f"Reattempt locked ({days} days)"}

        return {'allowed': True, 'badge_text': 'Available now'}

    for e in exams:
        access = _exam_access_for_user(e, user)
        setattr(e, '_access_allowed', bool(access.get('allowed')))
        setattr(e, '_access_badge_text', access.get('badge_text') or 'Available')

    completed_sessions = (
        ExamSession.query
        .filter_by(user_id=user.id, status='Completed')
        .filter(ExamSession.submitted_at.isnot(None))
        .order_by(ExamSession.submitted_at.desc())
        .all()
    )

    upcoming_exam = exams[0] if exams else None

    exams_completed = len(completed_sessions)
    avg_score = 0.0
    if exams_completed:
        vals = [float(s.percentage or 0.0) for s in completed_sessions]
        avg_score = sum(vals) / len(vals)

    attempted_exam_ids = {s.exam_id for s in completed_sessions if s.exam_id is not None}
    pending_exams = 0
    for e in exams:
        if e.id not in attempted_exam_ids:
            pending_exams += 1

    recent_results = []
    for s in completed_sessions[:5]:
        e = Exam.query.get(s.exam_id) if s.exam_id else None
        recent_results.append({
            'session_id': s.id,
            'exam_name': (e.name if e else 'Exam'),
            'date': (s.submitted_at or s.end_time or s.start_time),
            'percentage': float(s.percentage or 0.0),
            'result_status': (s.result_status or 'Completed'),
        })

    initials = ''.join([p[0] for p in (user.name or '').split()[:2]]).upper() or 'U'

    return render_template(
        'student_dashboard.html',
        user=user,
        initials=initials,
        exams=exams,
        upcoming_exam=upcoming_exam,
        exams_completed=exams_completed,
        avg_score=avg_score,
        pending_exams=pending_exams,
        recent_results=recent_results,
    )

@app.route('/profile')
@app.route('/profile.html')
def profile():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    user = User.query.get(session['user_id'])
    if not user or user.role != 'student':
        return redirect(url_for('login'))

    completed_sessions = (
        ExamSession.query
        .filter_by(user_id=user.id, status='Completed')
        .filter(ExamSession.submitted_at.isnot(None))
        .order_by(ExamSession.submitted_at.desc())
        .limit(10)
        .all()
    )
    history = []
    for s in completed_sessions:
        e = Exam.query.get(s.exam_id) if s.exam_id else None
        history.append({
            'session_id': s.id,
            'exam_name': (e.name if e else 'Exam'),
            'date': (s.submitted_at or s.end_time or s.start_time),
            'percentage': float(s.percentage or 0.0),
            'result_status': (s.result_status or 'Completed'),
        })

    initials = ''.join([p[0] for p in (user.name or '').split()[:2]]).upper() or 'U'
    face_filename = _safe_basename(user.face_image_path)
    face_url = url_for('uploaded_file', filename=face_filename) if face_filename else None

    return render_template(
        'profile.html',
        user=user,
        initials=initials,
        face_url=face_url,
        history=history,
    )
  




@app.route('/exam')
@app.route('/exam.html')
def exam():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    user = User.query.get(session['user_id'])
    if not user or user.role != 'student':
        return redirect(url_for('login'))

    exam_id = request.args.get('exam_id', type=int)
    if not exam_id:
        first_exam = Exam.query.filter_by(is_active=True).order_by(Exam.created_at.asc()).first()
        exam_id = first_exam.id if first_exam else None
    if not exam_id:
        return redirect(url_for('student_dashboard'))

    target_exam = Exam.query.get(exam_id)
    if not target_exam or not target_exam.is_active:
        return redirect(url_for('student_dashboard'))

    today = datetime.utcnow().date()
    available_from = getattr(target_exam, 'available_from', None)
    if available_from and today < available_from:
        return redirect(url_for('student_dashboard'))

    last = (
        ExamSession.query
        .filter_by(user_id=user.id, exam_id=target_exam.id)
        .filter(ExamSession.status == 'Completed')
        .filter(ExamSession.submitted_at.isnot(None))
        .order_by(ExamSession.submitted_at.desc())
        .first()
    )
    if last:
        allow_reattempt = bool(getattr(target_exam, 'allow_reattempt', False))
        if not allow_reattempt:
            return redirect(url_for('student_dashboard'))

        days = getattr(target_exam, 'reattempt_after_days', None)
        try:
            days = int(days) if days is not None else None
        except Exception:
            days = None
        if days and days > 0:
            last_date = (last.submitted_at or last.end_time or last.start_time)
            last_day = last_date.date() if last_date else today
            unlock_day = last_day + timedelta(days=days)
            if today < unlock_day:
                return redirect(url_for('student_dashboard'))

    new_session = ExamSession(user_id=session['user_id'], exam_id=exam_id)
    db.session.add(new_session)
    db.session.commit()
    session['exam_session_id'] = new_session.id
    
    return render_template('exam.html', user_name=user.name or 'Student', exam_id=exam_id)

   

@app.route('/api/profile/update', methods=['POST'])
def update_profile():
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': 'Unauthorized'}), 401
    user = User.query.get(session['user_id'])
    if not user or user.role != 'student':
        return jsonify({'success': False, 'message': 'Unauthorized'}), 401

    data = request.get_json(silent=True) or {}
    name = (data.get('name') or '').strip()
    email = (data.get('email') or '').strip().lower()
    mobile = (data.get('mobile_number') or '').strip()
    institution = (data.get('institution') or '').strip()
    course = (data.get('course') or '').strip()
    semester = (data.get('semester') or '').strip()
    cgpa = (data.get('cgpa') or '').strip()

    if email and email != user.email:
        exists = User.query.filter(User.email == email, User.id != user.id).first()
        if exists:
            return jsonify({'success': False, 'message': 'Email already in use'}), 400
        user.email = email

    if name:
        user.name = name
    if mobile:
        user.mobile_number = mobile
    if institution:
        user.institution = institution

    user.course = course or user.course
    user.semester = semester or user.semester
    user.cgpa = cgpa or user.cgpa

    db.session.commit()
    return jsonify({'success': True, 'message': 'Profile updated', 'user': user.to_dict()})


@app.route('/report/<int:session_id>.pdf')
def exam_report_pdf(session_id: int):
    if 'user_id' not in session:
        return redirect(url_for('login'))

    s = ExamSession.query.get_or_404(session_id)
    viewer = User.query.get(session['user_id'])
    if not viewer:
        return redirect(url_for('login'))

    if session.get('role') != 'admin' and s.user_id != viewer.id:
        abort(403)

    student = User.query.get(s.user_id)
    exam = Exam.query.get(s.exam_id) if s.exam_id else None
    responses = (
        ExamResponse.query
        .filter_by(session_id=s.id)
        .join(ExamQuestion, ExamResponse.question_id == ExamQuestion.id)
        .order_by(ExamQuestion.order_index.asc(), ExamQuestion.id.asc())
        .all()
    )

    buf = BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    width, height = A4

    y = height - 18 * mm
    c.setFont('Helvetica-Bold', 14)
    c.drawString(18 * mm, y, 'Exam Report')
    y -= 10 * mm

    c.setFont('Helvetica', 10)
    c.drawString(18 * mm, y, f"Student Name: {(student.name if student else '')}")
    y -= 6 * mm
    c.drawString(18 * mm, y, f"Student ID: {(student.student_uid if student else '')}")
    y -= 6 * mm
    c.drawString(18 * mm, y, f"Exam Name: {(exam.name if exam else '')}")
    y -= 6 * mm
    date_val = (s.submitted_at or s.end_time or s.start_time)
    c.drawString(18 * mm, y, f"Date: {date_val.strftime('%Y-%m-%d %H:%M') if date_val else ''}")
    y -= 8 * mm

    obtained = int(s.obtained_marks or 0)
    total = int(s.total_marks or 0)
    percent = float(s.percentage or 0.0)
    c.drawString(18 * mm, y, f"Total Marks: {total}")
    y -= 6 * mm
    c.drawString(18 * mm, y, f"Obtained Marks: {obtained}")
    y -= 6 * mm
    c.drawString(18 * mm, y, f"Percentage: {percent:.2f}%")
    y -= 10 * mm

    c.setFont('Helvetica-Bold', 11)
    c.drawString(18 * mm, y, 'Question-wise Breakdown')
    y -= 8 * mm

    for idx, r in enumerate(responses, start=1):
        q = ExamQuestion.query.get(r.question_id)
        if not q:
            continue

        if y < 25 * mm:
            c.showPage()
            y = height - 18 * mm

        c.setFont('Helvetica-Bold', 10)
        c.drawString(18 * mm, y, f"Q{idx}. {q.question_text}")
        y -= 6 * mm

        options = [q.option_a, q.option_b, q.option_c, q.option_d]
        correct = options[q.correct_option] if 0 <= q.correct_option < len(options) else ''
        selected = ''
        if r.selected_option is not None and 0 <= int(r.selected_option) < len(options):
            selected = options[int(r.selected_option)]

        c.setFont('Helvetica', 9)
        c.drawString(20 * mm, y, f"Correct Answer: {correct}")
        y -= 5 * mm
        c.drawString(20 * mm, y, f"Selected Answer: {selected}")
        y -= 5 * mm
        c.drawString(20 * mm, y, f"Result: {'Correct' if r.is_correct else 'Incorrect'}")
        y -= 7 * mm

    c.showPage()
    c.save()

    pdf = buf.getvalue()
    buf.close()

    resp = make_response(pdf)
    resp.headers['Content-Type'] = 'application/pdf'
    resp.headers['Content-Disposition'] = f'attachment; filename=exam_report_{session_id}.pdf'
    return resp


@app.route('/admin_dashboard')
@app.route('/admin_dashboard.html')
def admin_dashboard():
    if 'role' not in session or session['role'] != 'admin':
        if 'user_id' not in session:
            return redirect(url_for('login'))
        return "Unauthorized Access: Admin only", 403
    return render_template('admin_dashboard.html')


@app.route('/student_details')
@app.route('/student_details.html')
def student_details():
    if 'role' not in session or session['role'] != 'admin':
        return "Unauthorized", 403
    return render_template('student_details.html')


@app.route('/create_exam')
@app.route('/create_exam.html')
def create_exam():
    if 'role' not in session or session['role'] != 'admin':
        return "Unauthorized", 403
    return render_template('create_exam.html')


@app.route('/admin/api/exams/parse_csv', methods=['POST'])
def admin_parse_exam_csv():
    if 'role' not in session or session.get('role') != 'admin':
        return jsonify({'success': False, 'message': 'Unauthorized'}), 403

    f = request.files.get('csv_file')
    if not f or not f.filename:
        return jsonify({'success': False, 'message': 'CSV file is required'}), 400

    try:
        raw = f.read()
        try:
            text_data = raw.decode('utf-8-sig')
        except Exception:
            text_data = raw.decode('utf-8')
    except Exception:
        return jsonify({'success': False, 'message': 'Failed to read CSV'}), 400

    expected = ['question_text', 'option_a', 'option_b', 'option_c', 'option_d', 'correct_option', 'marks']
    reader = csv.reader(text_data.splitlines())
    rows = list(reader)
    if not rows:
        return jsonify({'success': False, 'message': 'CSV is empty'}), 400

    header = [c.strip() for c in rows[0]]
    if header != expected:
        return jsonify({'success': False, 'message': 'CSV header must match exactly: ' + ','.join(expected)}), 400

    questions = []
    for idx, r in enumerate(rows[1:], start=2):
        if not r or all((c or '').strip() == '' for c in r):
            continue
        if len(r) != len(expected):
            return jsonify({'success': False, 'message': f'Invalid column count on line {idx}'}), 400

        q_text, a, b, c, d, correct_raw, marks_raw = [x.strip() for x in r]
        if not q_text or not a or not b or not c or not d or correct_raw == '' or marks_raw == '':
            return jsonify({'success': False, 'message': f'Empty values on line {idx}'}), 400

        try:
            correct_opt = int(correct_raw)
        except Exception:
            return jsonify({'success': False, 'message': f'Invalid correct_option on line {idx}'}), 400
        if correct_opt not in (0, 1, 2, 3):
            return jsonify({'success': False, 'message': f'correct_option must be 0-3 on line {idx}'}), 400

        try:
            marks = int(marks_raw)
        except Exception:
            return jsonify({'success': False, 'message': f'Invalid marks on line {idx}'}), 400
        if marks <= 0:
            return jsonify({'success': False, 'message': f'marks must be > 0 on line {idx}'}), 400

        questions.append({
            'question_text': q_text,
            'option_a': a,
            'option_b': b,
            'option_c': c,
            'option_d': d,
            'correct_option': correct_opt,
            'marks': marks,
        })

    if not questions:
        return jsonify({'success': False, 'message': 'No valid questions found in CSV'}), 400

    return jsonify({'success': True, 'questions': questions})





@app.route('/admin/api/exams', methods=['POST'])
def admin_create_exam_api():
    if 'role' not in session or session.get('role') != 'admin':
        return jsonify({'success': False, 'message': 'Unauthorized'}), 403

    data = request.get_json(silent=True) or {}
    name = (data.get('name') or '').strip()
    description = (data.get('description') or '').strip()
    duration_minutes = data.get('duration_minutes')
    total_marks = data.get('total_marks')
    allow_reattempt = bool(data.get('allow_reattempt'))
    reattempt_after_days = data.get('reattempt_after_days')
    available_from_raw = data.get('available_from')
    questions = data.get('questions') or []

    if not name:
        return jsonify({'success': False, 'message': 'Exam name is required'}), 400
    if not isinstance(questions, list) or len(questions) == 0:
        return jsonify({'success': False, 'message': 'At least one question is required'}), 400

    try:
        duration_val = int(duration_minutes) if duration_minutes is not None else None
    except Exception:
        duration_val = None

    try:
        total_val = int(total_marks) if total_marks is not None else None
    except Exception:
        total_val = None

    try:
        available_from_val = None
        if available_from_raw:
            try:
                available_from_val = datetime.strptime(str(available_from_raw).strip(), '%Y-%m-%d').date()
            except Exception:
                available_from_val = None

        reattempt_days_val = None
        if allow_reattempt and reattempt_after_days is not None:
            try:
                reattempt_days_val = int(reattempt_after_days)
            except Exception:
                reattempt_days_val = None

        exam = Exam(
            name=name,
            description=description or None,
            duration_minutes=duration_val,
            total_marks=int(total_val or 0),
            is_active=True,
            allow_reattempt=allow_reattempt,
            reattempt_after_days=reattempt_days_val,
            available_from=available_from_val,
        )
        db.session.add(exam)
        db.session.flush()

        inserted = 0
        for i, q in enumerate(questions):
            if not isinstance(q, dict):
                continue
            q_text = (q.get('question_text') or '').strip()
            a = (q.get('option_a') or '').strip()
            b = (q.get('option_b') or '').strip()
            c_opt = (q.get('option_c') or '').strip()
            d = (q.get('option_d') or '').strip()
            correct_opt = q.get('correct_option')
            marks = q.get('marks')

            if not q_text or not a or not b or not c_opt or not d:
                continue
            try:
                correct_opt = int(correct_opt)
            except Exception:
                continue
            if correct_opt not in (0, 1, 2, 3):
                continue
            try:
                marks = int(marks)
            except Exception:
                marks = 1
            if marks <= 0:
                marks = 1

            db.session.add(
                ExamQuestion(
                    exam_id=exam.id,
                    question_text=q_text,
                    option_a=a,
                    option_b=b,
                    option_c=c_opt,
                    option_d=d,
                    correct_option=correct_opt,
                    marks=marks,
                    order_index=i,
                )
            )
            inserted += 1

        if inserted == 0:
            db.session.rollback()
            return jsonify({'success': False, 'message': 'No valid questions to insert'}), 400

        if not total_val:
            try:
                total_val = sum(int(q.get('marks') or 0) for q in questions)
            except Exception:
                total_val = inserted
            exam.total_marks = int(total_val or 0)

        db.session.commit()
        return jsonify({'success': True, 'exam_id': exam.id})
    except Exception:
        db.session.rollback()
        return jsonify({'success': False, 'message': 'Failed to create exam'}), 500


@app.route('/admin/api/exams', methods=['GET'])
def admin_list_exams_api():
    if 'role' not in session or session.get('role') != 'admin':
        return jsonify({'success': False, 'message': 'Unauthorized'}), 403

    exams = Exam.query.order_by(Exam.created_at.desc()).all()
    out = []
    for e in exams:
        out.append({
            'id': e.id,
            'name': e.name,
            'description': e.description,
            'duration_minutes': e.duration_minutes,
            'total_marks': e.total_marks,
            'pass_percentage': e.pass_percentage,
            'is_active': bool(e.is_active),
            'allow_reattempt': bool(getattr(e, 'allow_reattempt', False)),
            'reattempt_after_days': getattr(e, 'reattempt_after_days', None),
            'available_from': (getattr(e, 'available_from', None).strftime('%Y-%m-%d') if getattr(e, 'available_from', None) else None),
            'question_count': ExamQuestion.query.filter_by(exam_id=e.id).count(),
        })
    return jsonify({'success': True, 'exams': out})


@app.route('/admin/api/exams/<int:exam_id>', methods=['PATCH'])
def admin_update_exam_api(exam_id: int):
    if 'role' not in session or session.get('role') != 'admin':
        return jsonify({'success': False, 'message': 'Unauthorized'}), 403

    e = Exam.query.get_or_404(exam_id)
    data = request.get_json(silent=True) or {}

    if 'is_active' in data:
        e.is_active = bool(data.get('is_active'))

    db.session.commit()
    return jsonify({'success': True})


@app.route('/admin/api/exams/<int:exam_id>', methods=['DELETE'])
def admin_delete_exam_api(exam_id: int):
    if 'role' not in session or session.get('role') != 'admin':
        return jsonify({'success': False, 'message': 'Unauthorized'}), 403

    e = Exam.query.get_or_404(exam_id)
    try:
        # detach sessions (keep history)
        ExamSession.query.filter_by(exam_id=e.id).update({'exam_id': None})
        ExamQuestion.query.filter_by(exam_id=e.id).delete()
        db.session.delete(e)
        db.session.commit()
        return jsonify({'success': True})
    except Exception:
        db.session.rollback()
        return jsonify({'success': False, 'message': 'Failed to delete exam'}), 500


# --- Exam APIs ---

@app.route('/api/exams')
def list_exams():
    exams = Exam.query.filter_by(is_active=True).order_by(Exam.created_at.desc()).all()
    data = []
    for e in exams:
        q_count = ExamQuestion.query.filter_by(exam_id=e.id).count()
        data.append({
            'id': e.id,
            'name': e.name,
            'description': e.description,
            'duration_minutes': e.duration_minutes,
            'total_marks': e.total_marks,
            'pass_percentage': e.pass_percentage,
            'question_count': q_count,
        })
    return jsonify({'success': True, 'exams': data})


@app.route('/api/exams/<int:exam_id>')
def get_exam(exam_id: int):
    e = Exam.query.get_or_404(exam_id)
    questions = (
        ExamQuestion.query.filter_by(exam_id=e.id)
        .order_by(ExamQuestion.order_index.asc(), ExamQuestion.id.asc())
        .all()
    )
    q_data = []
    for q in questions:
        q_data.append({
            'id': q.id,
            'question_text': q.question_text,
            'options': [q.option_a, q.option_b, q.option_c, q.option_d],
            'marks': q.marks,
            'order_index': q.order_index,
        })
    return jsonify({
        'success': True,
        'exam': {
            'id': e.id,
            'name': e.name,
            'description': e.description,
            'duration_minutes': e.duration_minutes,
            'total_marks': e.total_marks,
            'pass_percentage': e.pass_percentage,
        },
        'questions': q_data,
    })


@app.route('/api/exam/submit', methods=['POST'])
def submit_exam_attempt():
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': 'Unauthorized'}), 401

    payload = request.get_json(silent=True) or {}
    answers = payload.get('answers') or {}
    if not isinstance(answers, dict):
        return jsonify({'success': False, 'message': 'Invalid answers payload'}), 400

    session_id = session.get('exam_session_id')
    if not session_id:
        return jsonify({'success': False, 'message': 'No active exam session'}), 400

    s = ExamSession.query.get(session_id)
    if not s or s.user_id != session['user_id']:
        return jsonify({'success': False, 'message': 'Invalid exam session'}), 400

    if s.status and s.status.startswith('Terminated'):
        return jsonify({'success': False, 'message': 'Exam session was terminated'}), 400

    if s.status == 'Completed' and s.submitted_at is not None:
        return jsonify({'success': True, 'message': 'Already submitted', 'session_id': s.id})

    if not s.exam_id:
        return jsonify({'success': False, 'message': 'Exam not linked to session'}), 400

    exam = Exam.query.get(s.exam_id)
    if not exam:
        return jsonify({'success': False, 'message': 'Exam not found'}), 400

    questions = (
        ExamQuestion.query.filter_by(exam_id=exam.id)
        .order_by(ExamQuestion.order_index.asc(), ExamQuestion.id.asc())
        .all()
    )

    ExamResponse.query.filter_by(session_id=s.id).delete()

    obtained = 0
    total = 0
    for q in questions:
        total += int(q.marks or 0)
        raw_selected = answers.get(str(q.id))
        selected = None
        if raw_selected is not None:
            try:
                selected = int(raw_selected)
            except Exception:
                selected = None

        is_correct = selected is not None and selected == q.correct_option
        marks_awarded = int(q.marks or 0) if is_correct else 0
        obtained += marks_awarded

        db.session.add(
            ExamResponse(
                session_id=s.id,
                question_id=q.id,
                selected_option=selected,
                is_correct=is_correct,
                marks_awarded=marks_awarded,
            )
        )

    percentage = (obtained / total * 100.0) if total > 0 else 0.0
    result_status = 'Passed' if percentage >= float(exam.pass_percentage or 0.0) else 'Failed'

    s.status = 'Completed'
    s.end_time = datetime.utcnow()
    s.submitted_at = datetime.utcnow()
    s.obtained_marks = obtained
    s.total_marks = total
    s.percentage = percentage
    s.result_status = result_status
    if hasattr(s, 'results_published'):
        s.results_published = False
    db.session.commit()

    proctor_session_state.pop(s.id, None)

    return jsonify({
        'success': True,
        'message': 'Exam submitted',
        'session_id': s.id,
        'obtained_marks': obtained,
        'total_marks': total,
        'percentage': percentage,
        'result_status': result_status,
    })


# --- Admin APIs ---

@app.route('/admin/api/stats')
def admin_stats():
    if 'role' not in session or session.get('role') != 'admin':
        return jsonify({'error': 'Unauthorized'}), 403

    total_students = User.query.filter_by(role='student').count()
    created_exams = Exam.query.count()

    pending_results = 0
    try:
        pending_results = (
            ExamSession.query
            .filter(ExamSession.status == 'Completed')
            .filter(ExamSession.submitted_at.isnot(None))
            .filter(ExamSession.results_published == False)  # noqa: E712
            .count()
        )
    except Exception:
        pending_results = 0

    return jsonify({
        'total_students': total_students,
        'created_exams': created_exams,
        'pending_results': pending_results,
    })


@app.route('/admin/api/sessions')
def admin_sessions():
    if 'role' not in session or session.get('role') != 'admin':
        return jsonify({'error': 'Unauthorized'}), 403

    sessions_data = ExamSession.query.order_by(ExamSession.start_time.desc()).limit(50).all()
    data = []
    for s in sessions_data:
        student = User.query.get(s.user_id)
        exam = Exam.query.get(s.exam_id) if s.exam_id else None

        warnings = Warning.query.filter_by(session_id=s.id).all()
        v_count = len(warnings)
        type_counts = {}
        for w in warnings:
            key = (w.violation_type or '').strip() or 'Violation'
            type_counts[key] = type_counts.get(key, 0) + 1
        top_types = sorted(type_counts.items(), key=lambda kv: kv[1], reverse=True)[:2]
        top_text = ', '.join([f"{t}({c})" for t, c in top_types])
        violation_summary = f"{v_count} violations" + (f": {top_text}" if top_text else '') if v_count else ''

        report_pdf_url = url_for('exam_report_pdf', session_id=s.id)
        report_csv_url = url_for('admin_session_report_csv', session_id=s.id)

        data.append({
            'session_id': s.id,
            'student_name': student.name if student else 'Unknown',
            'student_uid': student.student_uid if student else None,
            'exam_name': exam.name if exam else None,
            'status': s.status,
            'warnings': s.warnings_count,
            'violation_count': v_count,
            'violation_summary': violation_summary,
            'percentage': float(s.percentage) if s.percentage is not None else None,
            'date': s.start_time.strftime('%Y-%m-%d %H:%M') if s.start_time else None,
            'report_pdf_url': report_pdf_url,
            'report_csv_url': report_csv_url,
        })
    return jsonify(data)


@app.route('/admin/report/<int:session_id>.csv')
def admin_session_report_csv(session_id: int):
    if 'role' not in session or session.get('role') != 'admin':
        return redirect(url_for('login'))

    s = ExamSession.query.get_or_404(session_id)
    student = User.query.get(s.user_id)
    exam = Exam.query.get(s.exam_id) if s.exam_id else None
    responses = (
        ExamResponse.query
        .filter_by(session_id=s.id)
        .join(ExamQuestion, ExamResponse.question_id == ExamQuestion.id)
        .order_by(ExamQuestion.order_index.asc(), ExamQuestion.id.asc())
        .all()
    )

    def _csv_escape(value: str) -> str:
        value = value or ''
        value = value.replace('"', '""')
        return f'"{value}"'

    out = []
    out.append('student_name,student_uid,exam_name,question,selected_option,is_correct,marks_awarded')
    for r in responses:
        q = ExamQuestion.query.get(r.question_id)
        q_text = (q.question_text if q else '').replace('\n', ' ').replace('\r', ' ')
        selected = '' if r.selected_option is None else str(r.selected_option)
        row = ','.join([
            _csv_escape(student.name if student else ''),
            _csv_escape(student.student_uid if student else ''),
            _csv_escape(exam.name if exam else ''),
            _csv_escape(q_text),
            selected,
            str(1 if r.is_correct else 0),
            str(int(r.marks_awarded or 0)),
        ])
        out.append(row)

    csv_data = "\n".join(out)
    resp = make_response(csv_data)
    resp.headers['Content-Type'] = 'text/csv; charset=utf-8'
    resp.headers['Content-Disposition'] = f'attachment; filename=session_{session_id}_report.csv'
    return resp


@app.route('/admin/users')
def admin_users_api():
    if 'role' not in session or session.get('role') != 'admin':
        return jsonify({'error': 'Unauthorized'}), 403

    students = User.query.filter_by(role='student').order_by(User.id.desc()).all()
    users_list = []
    for s in students:
        users_list.append({
            'id': s.id,
            'student_uid': s.student_uid,
            'name': s.name,
            'email': s.email,
            'mobile_number': s.mobile_number,
            'institution': s.institution,
            'role': s.role,
            'registration_complete': s.registration_complete,
        })
    return jsonify(users_list)


@app.route('/admin/api/users/<int:user_id>')
def admin_get_user(user_id: int):
    if 'role' not in session or session.get('role') != 'admin':
        return jsonify({'success': False, 'message': 'Unauthorized'}), 403

    u = User.query.get_or_404(user_id)
    if u.role != 'student':
        return jsonify({'success': False, 'message': 'Not a student'}), 400

    id_proof_filename = _safe_basename(u.id_proof_path)
    face_filename = _safe_basename(u.face_image_path)
    id_proof_url = url_for('uploaded_file', filename=id_proof_filename) if id_proof_filename else None
    face_url = url_for('uploaded_file', filename=face_filename) if face_filename else None

    sessions = (
        ExamSession.query
        .filter_by(user_id=u.id)
        .order_by(ExamSession.start_time.desc())
        .limit(20)
        .all()
    )
    history = []
    for s in sessions:
        e = Exam.query.get(s.exam_id) if s.exam_id else None
        history.append({
            'session_id': s.id,
            'exam_name': (e.name if e else 'Exam'),
            'date': s.start_time.strftime('%Y-%m-%d %H:%M') if s.start_time else '',
            'status': s.status,
            'percentage': float(s.percentage) if s.percentage is not None else None,
        })

    return jsonify({
        'success': True,
        'user': {
            'id': u.id,
            'student_uid': u.student_uid,
            'name': u.name,
            'email': u.email,
            'mobile_number': u.mobile_number,
            'institution': u.institution,
            'date_of_birth': u.date_of_birth,
            'id_proof_url': id_proof_url,
            'face_url': face_url,
        },
        'history': history,
    })


@app.route('/admin/api/users/<int:user_id>', methods=['DELETE'])
def admin_delete_user(user_id: int):
    if 'role' not in session or session.get('role') != 'admin':
        return jsonify({'success': False, 'message': 'Unauthorized'}), 403

    u = User.query.get_or_404(user_id)
    if u.role != 'student':
        return jsonify({'success': False, 'message': 'Not a student'}), 400

    try:
        sessions = ExamSession.query.filter_by(user_id=u.id).all()
        for s in sessions:
            ExamResponse.query.filter_by(session_id=s.id).delete()
            Warning.query.filter_by(session_id=s.id).delete()
        ExamSession.query.filter_by(user_id=u.id).delete()
        PasswordOTP.query.filter_by(user_id=u.id).delete()
        LoginActivity.query.filter_by(user_id=u.id).delete()

        db.session.delete(u)
        db.session.commit()
        return jsonify({'success': True, 'message': 'Student deleted'})
    except Exception:
        db.session.rollback()
        return jsonify({'success': False, 'message': 'Delete failed'}), 500


# --- Socket.IO proctoring/exam events ---

def handle_violation(exam_session_id: int, message: str):
    current_session = ExamSession.query.get(exam_session_id)
    if not current_session or current_session.status != 'Active':
        return

    current_session.warnings_count += 1
    new_warning = Warning(session_id=exam_session_id, violation_type=message)
    db.session.add(new_warning)

    max_warnings = 6
    if current_session.warnings_count >= max_warnings:
        current_session.cheating_status = True
        current_session.status = 'Terminated (Cheating)'
        current_session.end_time = datetime.utcnow()
        db.session.commit()

        proctor_session_state.pop(exam_session_id, None)

        emit('exam_terminated', {
            'reason': 'Max warnings exceeded. Exam Terminated.',
            'redirect': url_for('student_dashboard')
        })
        return

    db.session.commit()
    emit('warning_alert', {
        'message': message,
        'count': current_session.warnings_count
    })


@socketio.on('process_frame')
def handle_frame(data):
    exam_session_id = session.get('exam_session_id')
    if not exam_session_id:
        return

    image_data = data.get('image')
    audio_level = data.get('audio_level', 0)
    client_violation_type = data.get('violation_type')

    state = proctor_session_state.setdefault(exam_session_id, {})
    res = proctor_engine.analyze(
        session_state=state,
        image_data_url=image_data,
        audio_level=audio_level,
        client_violation_type=client_violation_type,
    )

    if res.violation and res.message:
        handle_violation(exam_session_id, res.message)


@socketio.on('tab_change')
def handle_tab_change(data):
    exam_session_id = session.get('exam_session_id')
    if exam_session_id:
        handle_violation(exam_session_id, 'Tab Switch / Window Minimized detected')


@socketio.on('submit_exam')
def handle_submit():
    exam_session_id = session.get('exam_session_id')
    if exam_session_id:
        s = ExamSession.query.get(exam_session_id)
        if s and s.status == 'Active':
            s.status = 'Completed'
            s.end_time = datetime.utcnow()
            db.session.commit()

        proctor_session_state.pop(exam_session_id, None)


if __name__ == '__main__':
    with app.app_context():
        db.create_all()

        ensure_sqlite_schema()

        _seed_default_exam_if_missing()

        # Create default admin if not exists
        admin = User.query.filter_by(role='admin').first()
        if not admin:
            default_admin = User(
                name="Super Admin",
                email="admin@system.com",
                password=generate_password_hash("admin123"),
                role="admin"
            )
            db.session.add(default_admin)
            db.session.commit()
            print("✅ Default Admin Created: admin@system.com / admin123")

    socketio.run(app, debug=True, port=5000)