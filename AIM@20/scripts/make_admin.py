#!/usr/bin/env python3
"""
Script to promote a user to admin status.
Usage: python scripts/make_admin.py <username>
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from app.models import User

def make_admin(username):
    """Promote a user to admin status"""
    app = create_app()

    with app.app_context():
        user = User.query.filter_by(username=username).first()

        if not user:
            print(f"❌ User '{username}' not found!")
            return False

        if user.is_admin:
            print(f"ℹ️  User '{username}' is already an admin")
            return True

        user.is_admin = True

        try:
            from app import db
            db.session.commit()
            print(f"✅ Successfully promoted '{username}' to admin!")
            return True
        except Exception as e:
            print(f"❌ Error promoting user: {e}")
            db.session.rollback()
            return False

def list_users():
    """List all users with their admin status"""
    app = create_app()

    with app.app_context():
        users = User.query.all()

        if not users:
            print("No users found.")
            return

        print("Current users:")
        print("-" * 50)
        for user in users:
            admin_status = "👑 ADMIN" if user.is_admin else "👤 USER"
            print(f"{user.username:<20} | {user.email:<30} | {admin_status}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python scripts/make_admin.py list                    # List all users")
        print("  python scripts/make_admin.py <username>             # Make user admin")
        sys.exit(1)

    command = sys.argv[1]

    if command == "list":
        list_users()
    else:
        username = command
        success = make_admin(username)
        sys.exit(0 if success else 1)