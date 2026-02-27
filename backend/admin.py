from flask import Blueprint, jsonify
from models import User

admin_bp = Blueprint('admin', __name__)

@admin_bp.route('/users', methods=['GET'])
def get_users():
    # Fetch all users with role 'student'
    students = User.query.filter_by(role='student').all()
    
    # Convert list of objects to list of dictionaries
    student_list = [student.to_dict() for student in students]
    
    return jsonify(student_list), 200