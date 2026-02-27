from flask import Blueprint, request, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from models import db, User, LoginActivity

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/register', methods=['POST'])
def register():
    data = request.get_json()

    email = data['email'].strip().lower()

    if User.query.filter_by(email=email).first():
        return jsonify({'message': 'Email already registered'}), 400

    hashed_password = generate_password_hash(data['password'], method='pbkdf2:sha256')

    new_user = User(
        name=f"{data['firstName']} {data['lastName']}",
        email=email,
        password=hashed_password,
        role='student'
    )

    db.session.add(new_user)
    db.session.commit()

    return jsonify({'message': 'Registration successful!'}), 201


@auth_bp.route('/login', methods=['POST'])
def login():
    data = request.get_json()

    email = data['email'].strip().lower()
    user = User.query.filter_by(email=email).first()

    if not user or not check_password_hash(user.password, data['password']):
        return jsonify({'message': 'Invalid email or password'}), 401

    login_entry = LoginActivity(user_id=user.id, email=email)
    db.session.add(login_entry)
    db.session.commit()

    return jsonify({
        'message': 'Login successful',
        'user': user.to_dict()
    }), 200
