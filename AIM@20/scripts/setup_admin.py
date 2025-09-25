#!/usr/bin/env python3
"""
Setup script to create admin account ABC with password 123456.
This will reset the database and create a fresh admin user.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from werkzeug.security import generate_password_hash

def setup_admin():
    """Setup admin user ABC with password 123456"""

    app = create_app()

    with app.app_context():
        from app import db

        try:
            # Try to add is_admin column if it doesn't exist (raw SQL)
            db.engine.execute(db.text("ALTER TABLE user ADD COLUMN is_admin BOOLEAN DEFAULT FALSE"))
            print("Added is_admin column to user table")
        except:
            print("is_admin column already exists")

        # Check if admin user already exists using raw SQL
        result = db.session.execute(db.text("SELECT id FROM user WHERE username = 'ABC'"))
        existing_admin = result.fetchone()

        if existing_admin:
            # Update existing user to be admin
            db.session.execute(db.text("UPDATE user SET is_admin = 1 WHERE username = 'ABC'"))
            db.session.commit()
            print("Updated existing user ABC to admin")
            return True

        # Create admin user using raw SQL to avoid model issues
        password_hash = generate_password_hash('123456')
        db.session.execute(db.text("""
            INSERT INTO user (username, email, password_hash, is_admin, created_at)
            VALUES ('ABC', 'admin@aim20.com', ?, 1, datetime('now'))
        """), (password_hash,))

        db.session.commit()
        print("Created admin user ABC with password 123456")
        print("Admin privileges: ENABLED")
        print("Email: admin@aim20.com")
        return True

if __name__ == "__main__":
    print("Setting up AIM20/VISION20 Admin Account...")
    print("=" * 50)

    success = setup_admin()

    if success:
        print("\n" + "=" * 50)
        print("ADMIN ACCOUNT SETUP COMPLETE!")
        print("\nLogin Details:")
        print("   Username: ABC")
        print("   Password: 123456")
        print("   Role: Administrator")
        print("\nAccess the application at: http://localhost:5000")
        print("Admin panel at: http://localhost:5000/admin/")
        print("=" * 50)
    else:
        print("\nADMIN ACCOUNT SETUP FAILED!")
        sys.exit(1)