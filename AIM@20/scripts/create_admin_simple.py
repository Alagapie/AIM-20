#!/usr/bin/env python3
"""
Simple script to create admin account ABC.
Run this after the application is running and database exists.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def create_admin_simple():
    """Create admin user ABC with simple approach"""

    # Check if we can connect to database
    db_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'instance', 'aim20_vision20_dev.db')
    if not os.path.exists(db_path):
        print("Database not found. Please run the application first to create the database.")
        return False

    try:
        import sqlite3
        from werkzeug.security import generate_password_hash

        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Check if is_admin column exists, if not add it
        cursor.execute("PRAGMA table_info(user)")
        columns = [col[1] for col in cursor.fetchall()]

        if 'is_admin' not in columns:
            print("Adding is_admin column...")
            cursor.execute("ALTER TABLE user ADD COLUMN is_admin BOOLEAN DEFAULT FALSE")
            conn.commit()

        # Check if ABC user exists
        cursor.execute("SELECT id FROM user WHERE username = 'ABC'")
        existing = cursor.fetchone()

        if existing:
            # Update to admin
            cursor.execute("UPDATE user SET is_admin = 1 WHERE username = 'ABC'")
            conn.commit()
            print("Updated user ABC to admin status")
        else:
            # Create new admin user
            password_hash = generate_password_hash('123456')
            cursor.execute("""
                INSERT INTO user (username, email, password_hash, is_admin, created_at)
                VALUES ('ABC', 'admin@aim20.com', ?, 1, datetime('now'))
            """, (password_hash,))
            conn.commit()
            print("Created new admin user ABC")

        conn.close()
        return True

    except Exception as e:
        print(f"Error: {e}")
        return False

if __name__ == "__main__":
    print("Creating admin account ABC...")
    print("=" * 40)

    if create_admin_simple():
        print("\n" + "=" * 40)
        print("SUCCESS!")
        print("\nAdmin Account Details:")
        print("  Username: ABC")
        print("  Password: 123456")
        print("  Email: admin@aim20.com")
        print("  Role: Administrator")
        print("\nAccess admin panel at: /admin/")
        print("=" * 40)
    else:
        print("\nFAILED!")
        print("Please make sure the application has been run at least once to create the database.")
        sys.exit(1)