from flask import request, jsonify, render_template, redirect, url_for, session, Blueprint
from datetime import datetime, timedelta
import password_utils as pw
import send_mail as sm
import random
from models import Users
from database import db


def otp_generator():
    return random.randint(100000, 999999)

login_bp = Blueprint('auth', __name__)

# Admin Dashboard - Delete User
@login_bp.route('/delete_user/<int:user_id>', methods=['POST'])
def delete_user(user_id):
    user = Users.query.get_or_404(user_id)
    if session.get('role') == "admin":
        db.session.delete(user)
        db.session.commit()
        sm.user_deleted(user.Email, user)
        return redirect(url_for('auth.admin_dashboard'))  # Use 'auth' prefix here
    else:
        return jsonify({'error': "You don't have enough rights.."}), 400

# Admin Dashboard - Update Approval
@login_bp.route('/update_approval/<int:user_id>', methods=['POST'])
def update_approval(user_id):
    user = Users.query.get_or_404(user_id)
    if session.get('role') == "admin":
        approved = 'approved' in request.form  # Check if checkbox is checked
        user.approved = approved
        db.session.commit()
        sm.user_approved(user.Email, user)
        return redirect(url_for('auth.admin_dashboard'))  # Use 'auth' prefix here
    else:
        return jsonify({'error': "You don't have enough rights to make changes.."}), 400

# Admin Dashboard Route
@login_bp.route('/admin_dashboard')
def admin_dashboard():
    users = Users.query.all()
    return render_template('admin_dashboard.html', users=users)

# User Registration
@login_bp.route('/add_user', methods=['POST', 'GET'])
def add_user():
    if request.method == 'POST':
        # Retrieving form data
        username = request.form['username']
        email = request.form['email']
        name = request.form['username']  # Assuming the user's name is the same as the username 
        password = request.form['password']
        dob = request.form['dob']
        role = request.form.get('role')  # Optional field
        phone_number = request.form.get('phone_number')  # Optional field
        hashed_password = pw.hash_password(password)
        dob = datetime.strptime(dob, '%Y-%m-%d').date()
        approved = False
        if role.lower() == "admin":
            approved = True

        # Create a new user object
        new_user = Users(
            UserName=username,
            Password=hashed_password.decode('utf-8'),
            Email=email,
            Name=name,
            DOB=dob,
            Role=role,
            PhoneNumber=phone_number,
            approved=approved
        )

        # Add and commit the new user to the database
        try:
            db.session.add(new_user)
            db.session.commit()
            sm.approval_status_mail(email, username)
            return jsonify({'message': 'User added successfully!'}), 201
        except Exception as e:
            db.session.rollback()
            return jsonify({'error': str(e)}), 400

    return render_template('signup.html')

# User Login
@login_bp.route('/', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        # Query the database to find a user by username
        user = Users.query.filter_by(UserName=username).first()

        if user and pw.verify_password(password, user.Password.encode('utf-8')):
            if not user.approved and user.Role != 'admin':
                session['error_message'] = "Your account is not approved by the admin."
                return redirect(url_for('auth.login'))
            session.pop('error_message', None)  # Clear any previous error messages
            otp = otp_generator()
            sm.send_otp_email(user.Email, otp)

            session['otp'] = otp
            session['otp_expiry'] = (datetime.now() + timedelta(minutes=5)).isoformat()
            session['user'] = username
            session['role'] = user.Role
            return redirect(url_for('auth.verify_otp'))

        else:
            # Store the error message in session
            session['error_message'] = 'Wrong password. Please try again.'
            return redirect(url_for('auth.login'))  # Correct route here

    # Retrieve the error message from session (if any)
    error_message = session.pop('error_message', None)
    return render_template('login.html', error_message=error_message)

# OTP Resend
@login_bp.route('/resend_otp', methods=['POST'])
def resend_otp():
    if 'user' in session:
        username = session['user']
        user = Users.query.filter_by(UserName=username).first()
        if user:
            # Generate a new OTP
            otp = otp_generator()
            sm.send_otp_email(user.Email, otp)

            session['otp'] = otp
            session['otp_expiry'] = (datetime.now() + timedelta(minutes=5)).isoformat()
            session['error_message'] = 'A new OTP has been sent to your email.'
        else:
            session['error_message'] = 'User not found. Please log in again.'
    else:
        session['error_message'] = 'Session expired. Please log in again.'

    return redirect(url_for('auth.verify_otp'))  # Correct route here

# Forgot Password
@login_bp.route('/forgot_password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        email = request.form['email']

        # Check if email exists in the database
        user = Users.query.filter_by(Email=email).first()
        if not user:
            session['error_message'] = 'Email not found.'
            return redirect(url_for('auth.forgot_password'))  # Correct route here

        # Generate OTP and store it in session
        otp = otp_generator()
        sm.send_otp_email(email, otp)

        session['reset_otp'] = otp
        session['reset_email'] = email
        session['reset_otp_expiry'] = (datetime.now() + timedelta(minutes=5)).isoformat()
        return redirect(url_for('auth.verify_otp'))  # Correct route here

    error_message = session.pop('error_message', None)
    return render_template('forgot_password.html', error_message=error_message)

# Reset Password
@login_bp.route('/reset_password', methods=['GET', 'POST'])
def reset_password():
    if request.method == 'POST':
        new_password = request.form['new_password']
        confirm_password = request.form['confirm_password']

        if new_password != confirm_password:
            session['error_message'] = 'Passwords do not match.'
            return redirect(url_for('auth.reset_password'))  # Correct route here

        email = session.get('reset_email')
        if not email:
            return jsonify({'error': 'Session expired. Start the process again.'}), 400

        # Update the password in the database
        user = Users.query.filter_by(Email=email).first()
        if not user:
            return jsonify({'error': 'User not found.'}), 404

        hashed_password = pw.hash_password(new_password)
        user.Password = hashed_password.decode('utf-8')
        db.session.commit()

        session.pop('reset_email')
        return jsonify({'message': 'Password reset successfully!'}), 200

    error_message = session.pop('error_message', None)
    return render_template('reset_password.html', error_message=error_message)

# Verify OTP
@login_bp.route('/verify_otp', methods=['GET', 'POST'])
def verify_otp():
    if request.method == 'POST':
        entered_otp = request.form['otp']

        # Handle password reset OTP verification
        if 'reset_otp' in session and 'reset_otp_expiry' in session:
            reset_otp_expiry = datetime.fromisoformat(session['reset_otp_expiry'])
            if datetime.now() < reset_otp_expiry and int(entered_otp) == session['reset_otp']:
                session.pop('reset_otp')
                session.pop('reset_otp_expiry')
                return redirect(url_for('auth.reset_password'))  # Proceed to password reset
            else:
                session['error_message'] = 'Invalid or expired OTP for password reset.'
                return redirect(url_for('auth.verify_otp'))  # Correct route here

        # Handle login OTP verification
        elif 'otp' in session and 'otp_expiry' in session:
            otp_expiry = datetime.fromisoformat(session['otp_expiry'])
            if datetime.now() < otp_expiry and int(entered_otp) == session['otp']:
                session.pop('otp')
                session.pop('otp_expiry')
                if session.get('role') == 'admin':
                    return redirect(url_for('auth.admin_dashboard'))  # Redirect to Admin Dashboard
                else:
                    return jsonify({'message': 'Successfully logged in to your account!'}), 201
            else:
                session['error_message'] = 'Invalid or expired OTP for login.'
                return redirect(url_for('auth.verify_otp'))  # Correct route here

        else:
            session['error_message'] = 'OTP context not found.'
            return redirect(url_for('auth.verify_otp'))  # Correct route here

    error_message = session.pop('error_message', None)
    return render_template('verify_otp.html', error_message=error_message)
