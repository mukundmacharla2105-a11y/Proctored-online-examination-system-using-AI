from app import app, db, User
from werkzeug.security import generate_password_hash, check_password_hash
import os

def initialize_database():
    print("\n===========================================")
    print("      DATABASE SETUP & DIAGNOSTICS")
    print("===========================================")
    
    # 1. Detect Database Path from App Config to ensure consistency
    db_uri = app.config.get('SQLALCHEMY_DATABASE_URI', '')
    print(f"ℹ️  App Config URI: {db_uri}")
    
    if db_uri.startswith('sqlite:///'):
        raw_path = db_uri.replace('sqlite:///', '')
        db_path = os.path.abspath(raw_path)
        print(f"📂 Target Database File: {db_path}")

    # 2. Reset and Create Fresh Data
    with app.app_context():
        print("\n--- Resetting Database ---")
        try:
            # SQL-based reset (Safer than deleting the file on Windows)
            db.drop_all()
            print("🗑️  Old tables dropped (SQL Reset).")
            db.create_all()
            print("✅ New tables created.")
        except Exception as e:
            print(f"❌ Error during reset: {e}")
            return

        # 3. Add Users (Safe Insert)
        print("\n--- Adding Users ---")
        
        # Check if student exists (Double safety, though drop_all should have cleared it)
        if not User.query.filter_by(email='student@test.com').first():
            hashed_pw_student = generate_password_hash('password123', method='pbkdf2:sha256')
            student = User(
                name='Test Student',
                email='student@test.com',
                password=hashed_pw_student,
                role='student'
            )
            db.session.add(student)
            print("✅ Added: student@test.com")
        
        # Check if admin exists
        if not User.query.filter_by(email='admin@test.com').first():
            hashed_pw_admin = generate_password_hash('admin', method='pbkdf2:sha256')
            admin = User(
                name='Admin User',
                email='admin@test.com',
                password=hashed_pw_admin,
                role='admin'
            )
            db.session.add(admin)
            print("✅ Added: admin@test.com")

        try:
            db.session.commit()
            print("💾 Changes saved to database.")
        except Exception as e:
            db.session.rollback()
            print(f"❌ Error saving users: {e}")

        # 4. VERIFICATION
        print("\n--- 🔍 Verification Check ---")
        
        # List ALL users in DB
        all_users = User.query.all()
        print(f"👥 Total Users Found in DB: {len(all_users)}")
        for u in all_users:
            print(f"   - ID: {u.id} | Email: {u.email} | Role: {u.role}")

        # Login Logic Check
        test_user = User.query.filter_by(email='student@test.com').first()
        if test_user:
            if check_password_hash(test_user.password, 'password123'):
                print("\n✅ LOGIN CHECK PASSED: Password 'password123' matches hash.")
            else:
                print("\n❌ LOGIN CHECK FAILED: Hash mismatch.")
        else:
            print("\n❌ CRITICAL ERROR: User was not saved to DB.")

    print("\n===========================================")
    print(" SETUP COMPLETE")
    print(" 1. Run 'python app.py'")
    print(" 2. Login with: student@test.com / password123")
    print("===========================================\n")

if __name__ == '__main__':
    initialize_database()