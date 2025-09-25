from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash

auth_bp = Blueprint('auth', __name__, url_prefix='/auth')

# Import db - models will be imported inside functions to avoid circular imports
from app import db

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))

    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '').strip()
        confirm_password = request.form.get('confirm_password', '').strip()
        
        # Validation
        if not username or not email or not password:
            flash('All fields are required.', 'error')
            return redirect(url_for('auth.register'))
        
        if password != confirm_password:
            flash('Passwords do not match.', 'error')
            return redirect(url_for('auth.register'))
        
        if len(password) < 6:
            flash('Password must be at least 6 characters long.', 'error')
            return redirect(url_for('auth.register'))
        
        from app.models import User

        # Check if user exists
        existing_user = User.query.filter_by(username=username).first()
        if existing_user:
            flash('Username already exists.', 'error')
            return redirect(url_for('auth.register'))

        existing_email = User.query.filter_by(email=email).first()
        if existing_email:
            flash('Email already registered.', 'error')
            return redirect(url_for('auth.register'))

        # Check if this is the first user (make them admin automatically)
        from app.models import User
        user_count = User.query.count()
        is_first_user = user_count == 0

        # Create new user
        hashed_password = generate_password_hash(password, method='pbkdf2:sha256')
        new_user = User(username=username, email=email, password_hash=hashed_password, is_admin=is_first_user)

        print(f"DEBUG: Attempting to register user - Username: {username}, Email: {email}")
        try:
            db.session.add(new_user)
            print("DEBUG: Added user to session")
            db.session.commit()
            print(f"DEBUG: User registered successfully - Username: {username}, Email: {email}")

            # Verify user was saved
            saved_user = User.query.filter_by(username=username).first()
            print(f"DEBUG: Verification - User exists in DB: {saved_user is not None}")

            flash('Registration successful! Please log in.', 'success')
            return redirect(url_for('auth.login'))
        except Exception as e:
            db.session.rollback()
            print(f"DEBUG: Registration error: {str(e)}")
            print(f"DEBUG: Error type: {type(e)}")
            flash('An error occurred during registration.', 'error')
            return redirect(url_for('auth.register'))
    
    return render_template('auth/register.html', title='Register')

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))
    
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()
        remember = request.form.get('remember') == 'on'
        
        from app.models import User

        if not username or not password:
            flash('Username and password are required.', 'error')
            return redirect(url_for('auth.login'))

        print(f"DEBUG: Login attempt - Username: '{username}', Password length: {len(password)}")
        user = User.query.filter_by(username=username).first()
        print(f"DEBUG: User found in database: {user is not None}")
        if user:
            print(f"DEBUG: Stored hash: {user.password_hash[:20]}...")
            password_check = check_password_hash(user.password_hash, password)
            print(f"DEBUG: Password check result: {password_check}")

        if user and check_password_hash(user.password_hash, password):
            login_user(user, remember=remember)
            user.last_login = db.func.now()
            db.session.commit()

            next_page = request.args.get('next')
            if next_page:
                return redirect(next_page)
            return redirect(url_for('main.dashboard'))
        else:
            print(f"DEBUG: Login failed - User exists: {user is not None}")
            flash('Invalid username or password.', 'error')
            return redirect(url_for('auth.login'))
    
    return render_template('auth/login.html', title='Login')

@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('main.index'))