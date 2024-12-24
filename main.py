from flask import Flask, request, jsonify, render_template, redirect, url_for, session
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timedelta
import password_utils as pw
import random
import smtplib
from email.mime.text import MIMEText

# Flask app setup
app = Flask(__name__)
app.secret_key = 'your_secret_key'  # Required for session management
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///mydatabase.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SQLALCHEMY_ECHO'] = True

db = SQLAlchemy(app)

# Define the Users table
class Users(db.Model):
    _tablename_ = 'users'
    UserID = db.Column(db.Integer, primary_key=True)
    UserName = db.Column(db.String(50), nullable=False)
    Password = db.Column(db.String(100), nullable=False)
    Email = db.Column(db.String(100), unique=True, nullable=False)
    Name = db.Column(db.String(100), nullable=False)
    DOB = db.Column(db.Date, nullable=True)
    Role = db.Column(db.String(50), nullable=True)
    PhoneNumber = db.Column(db.String(15), unique=True, nullable=True)

def send_otp_email(email, otp):
    sender_email = 'examplenamez543@gmail.com'
    sender_password = 'mfnppwcnqlmpzymc'
    subject = 'Your OTP Code'
    body = f'Your OTP code is: {otp}'

    msg = MIMEText(body)
    msg['Subject'] = subject
    msg['From'] = sender_email
    msg['To'] = email

    try:
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
            server.login(sender_email, sender_password)
            server.sendmail(sender_email, email, msg.as_string())
    except Exception as e:
        print(f'Error sending email: {str(e)}')


# Route to insert a user record
@app.route('/add_user', methods=['POST', 'GET'])
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

        # Create a new user object
        new_user = Users(
            UserName=username,
            Password=hashed_password.decode('utf-8'),
            Email=email,
            Name=name,
            DOB=dob,
            Role=role,
            PhoneNumber=phone_number
        )

        # Add and commit the new user to the database
        try:
            db.session.add(new_user)
            db.session.commit()
            return jsonify({'message': 'User added successfully!'}), 201
        except Exception as e:
            db.session.rollback()
            return jsonify({'error': str(e)}), 400
    
    return render_template('signup.html')

@app.route('/', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        # Query the database to find a user by username
        user = Users.query.filter_by(UserName=username).first()

        if user and pw.verify_password(password,user.Password.encode('utf-8')):
            session.pop('error_message', None)  # Clear any previous error messages
            otp = random.randint(100000, 999999)
            session['otp'] = otp
            session['otp_expiry'] = (datetime.now() + timedelta(minutes=5)).isoformat()
            session['user'] = username
            send_otp_email(user.Email, otp)

            return redirect(url_for('verify_otp'))
        else:
            # Store the error message in session
            session['error_message'] = 'Wrong password. Please try again.'
            return redirect(url_for('login'))

    # Retrieve the error message from session (if any)
    error_message = session.pop('error_message', None)
    return render_template('login.html', error_message=error_message)

@app.route('/forgot_password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        email = request.form['email']

        # Check if email exists in the database
        user = Users.query.filter_by(Email=email).first()
        if not user:
            session['error_message'] = 'Email not found.'
            return redirect(url_for('forgot_password'))

        # Generate OTP and store it in session
        otp = random.randint(100000, 999999)
        session['reset_otp'] = otp
        session['reset_email'] = email
        session['reset_otp_expiry'] = (datetime.now() + timedelta(minutes=5)).isoformat()

        # Send OTP using existing function
        send_otp_email(email, otp)
        return redirect(url_for('verify_otp'))

    error_message = session.pop('error_message', None)
    return render_template('forgot_password.html', error_message=error_message)

@app.route('/reset_password', methods=['GET', 'POST'])
def reset_password():
    if request.method == 'POST':
        new_password = request.form['new_password']
        confirm_password = request.form['confirm_password']

        if new_password != confirm_password:
            session['error_message'] = 'Passwords do not match.'
            return redirect(url_for('reset_password'))

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


# Verify OTP route
# Verify OTP route
@app.route('/verify_otp', methods=['GET', 'POST'])
def verify_otp():
    if request.method == 'POST':
        entered_otp = request.form['otp']

        # Check for OTP context: login or password reset
        if 'otp' in session and 'otp_expiry' in session:
            # Login OTP verification
            otp_expiry = datetime.fromisoformat(session['otp_expiry'])
            if datetime.now() < otp_expiry and int(entered_otp) == session['otp']:
                session.pop('otp')
                session.pop('otp_expiry')
                return jsonify({'message': 'Successfully logged in to your account!'}), 201
            else:
                session['error_message'] = 'Invalid or expired OTP for login.'
                return redirect(url_for('verify_otp'))

        elif 'reset_otp' in session and 'reset_otp_expiry' in session:
            # Password reset OTP verification
            reset_otp_expiry = datetime.fromisoformat(session['reset_otp_expiry'])
            if datetime.now() < reset_otp_expiry and int(entered_otp) == session['reset_otp']:
                session.pop('reset_otp')
                session.pop('reset_otp_expiry')
                return redirect(url_for('reset_password'))  # Proceed to password reset

            else:
                session['error_message'] = 'Invalid or expired OTP for password reset.'
                return redirect(url_for('verify_otp'))

        else:
            session['error_message'] = 'OTP context not found.'
            return redirect(url_for('verify_otp'))

    error_message = session.pop('error_message', None)
    return render_template('verify_otp.html', error_message=error_message)

# Initialize database tables
with app.app_context():
    db.create_all()

if __name__ == '__main__':
    app.run(debug=True)

