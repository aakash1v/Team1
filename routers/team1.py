from flask import request, jsonify, render_template, redirect, url_for, session, Blueprint, current_app
from datetime import datetime, timedelta
import password_utils as pw
import send_mail as sm
import random
from models import Users
from database import db
from flask_login import LoginManager, login_user, login_required, logout_user, current_user
import os
import csv
from werkzeug.utils import secure_filename
import pandas as pd
import matplotlib.pyplot as plt
import io
import base64
import seaborn as sns


USER =""
# File to store history
CSV_FILE = "user_history.csv"

login_manager = LoginManager()
login_bp = Blueprint('auth', __name__)  


# Ensure the upload folder exists
os.makedirs('static/uploads', exist_ok=True)

# Check if the file extension is allowed
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in {'png', 'jpg', 'jpeg', 'gif'}

@login_manager.user_loader
def load_user(user_id):
    try:
        return Users.query.get(int(user_id))
    except Exception as e:
        print(f"Error loading user: {e}")
        return None
    

def otp_generator():
    return random.randint(100000, 999999)

# Initialize the CSV file if it doesn't exist
if not os.path.exists(CSV_FILE):
    with open(CSV_FILE, mode='w', newline='') as file:
        writer = csv.writer(file)
        writer.writerow(["User ID","Username", "Role", "Action", "Timestamp", "IP Address"])  # Header row

# Function to log actions to CSV
def log_to_csv(user_id, action):
    user = db.session.execute(db.Select(Users).where(Users.UserID==user_id)).scalar()
    print(user.UserName, user)
    with open(CSV_FILE, mode='a', newline='') as file:
        writer = csv.writer(file)
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        ip_address = request.remote_addr or "Unknown"
        writer.writerow([user_id, user.UserName, user.Role, action, timestamp, ip_address])

# Function to read records from the CSV file
def get_history_from_csv(user_id):
    history = []
    with open(CSV_FILE, mode='r') as file:
        csv_reader = csv.DictReader(file)
        for row in csv_reader:
            if int(row['User ID']) == user_id:
                history.append({
                    'id': row['User ID'],
                    'username': row['Username'],
                    'role': row['Role'],
                    'action': row['Action'],
                    'timestamp': row['Timestamp'],
                    'ip_address': row['IP Address']
                })
    # print(history)
    return history


@login_bp.route('/history/<int:user_id>', methods=['POST'])
def history(user_id):
    history = get_history_from_csv(user_id)
    print(history)
    return render_template('history.html', history=history)



### ADMIN DASHBOARD ROUTES ....

@login_bp.route('/admin_dashboard')
@login_required
def admin_dashboard():
    print(current_user.Name)
    if current_user.Role == 'admin':
        users = Users.query.all()
        return render_template('admin_dashboard.html', users=users, u=current_user)
    else:
        return jsonify({'error': "u don't have access to this page....."})


@login_bp.route('/delete_user/<int:user_id>', methods=['POST'])
@login_required
def delete_user(user_id):
    user = Users.query.get_or_404(user_id)
    db.session.delete(user)
    db.session.commit()
    sm.user_deleted(user.Email, user)
    return redirect(url_for('auth.admin_dashboard'))  


@login_bp.route('/update_approval/<int:user_id>', methods=['POST'])
@login_required
def update_approval(user_id):
    user = Users.query.get_or_404(user_id)
    approved = 'approved' in request.form  # Check if checkbox is checked
    user.Approved = approved
    db.session.commit()
    sm.user_approved(user.Email, user)
    return redirect(url_for('auth.admin_dashboard'))  


#####  USER REGESTRATION ....

@login_bp.route('/add_user', methods=['POST', 'GET'])
def add_user():
    if request.method == 'POST':
        # Retrieving form data
        username = request.form['username']
        email = request.form['email']
        name = request.form['name']  
        password = request.form['password']
        dob = request.form['dob']
        role = request.form.get('role')  # Optional field
        phone_number = request.form.get('phone_number')  # Optional field
        hashed_password = pw.hash_password(password)
        dob = datetime.strptime(dob, '%Y-%m-%d').date()
        approved = False
        if role.lower() == "admin":
            approved = True

        # Check if file is uploaded and is allowed
        file = request.files['file']
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            filepath = os.path.join('static/uploads', filename)
            file.save(filepath)
        # Create a new user object
        new_user = Users(
            UserName=username,
            Password=hashed_password.decode('utf-8'),
            Email=email,
            Name=name,
            DOB=dob,
            Role=role,
            PhoneNumber=phone_number,
            Approved=approved,
            profile_picture='uploads/'+ filename
        )

        # Add and commit the new user to the database
        try:
            db.session.add(new_user)
            db.session.commit()
            admins = db.session.execute(db.select(Users).where(Users.Role == "admin")).scalars().all()
            if role != "admin":
                for admin in admins:
                    ## sending mail to admin for approval...
                    sm.sending_approval_req(admin, new_user)
            return jsonify({'message': 'User added successfully!'}), 201
        except Exception as e:
            db.session.rollback()
            return jsonify({'error': str(e)}), 400

    return render_template('signup.html')

###  User Login
@login_bp.route('/', methods=['GET', 'POST'])
def login():
    global USER
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        # Query the database to find a user by username
        user = Users.query.filter_by(UserName=username).first()
        USER = user
        if user and pw.verify_password(password, user.Password.encode('utf-8')):
            if not user.Approved and user.Role != 'admin':
                session['error_message'] = "Your account is not approved by the admin."
                return redirect(url_for('auth.login'))
            session.pop('error_message', None)  # Clear any previous error messages
            otp = otp_generator()
            sm.send_otp_email(user.Email, otp)

            session['otp'] = otp
            session['otp_expiry'] = (datetime.now() + timedelta(minutes=5)).isoformat()
            session['username'] = user.UserName
            session['role'] = user.Role
            return redirect(url_for('auth.verify_otp'))

        else:
            # Store the error message in session
            session['error_message'] = 'Wrong password. Please try again.'
            return redirect(url_for('auth.login'))  # Correct route here

    # Retrieve the error message from session (if any)
    error_message = session.pop('error_message', None)
    return render_template('login.html', error_message=error_message)

#### Logout

@login_bp.route('/logout', methods=['POST', 'GET'])
@login_required
def logout():
    print(current_user.UserName)
    # track_logout(None, current_user)  # Call track_login manually
    log_to_csv(current_user.UserID, "Logout")
    logout_user()
    return redirect(url_for('auth.login'))



#### VERIFY OTP ...

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
                    login_user(USER)
                    log_to_csv(current_user.UserID, "Login")

                    # track_login(None, current_user)  # Call track_login manually

                    return redirect(url_for('auth.admin_dashboard'))  # Redirect to Admin Dashboard
                else:
                    print(USER)
                    print(USER.UserID)
                    login_user(USER)
                    log_to_csv(current_user.UserID, "Login")

                    # track_login(None, current_user)  # Call track_login manually

                    return redirect(f'/projects/{current_user.Role}/{current_user.UserID}')
            else:
                session['error_message'] = 'Invalid or expired OTP for login.'
                return redirect(url_for('auth.verify_otp'))  # Correct route here

        else:
            session['error_message'] = 'OTP context not found.'
            return redirect(url_for('auth.verify_otp'))  # Correct route here

    error_message = session.pop('error_message', None)
    return render_template('verify_otp.html', error_message=error_message)


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
        user = db.session.execute(db.select(Users).where(Users.Email == email)).scalar()
        user_id = user.UserID
        if not user:
            return jsonify({'error': 'User not found.'}), 404
        
        hashed_password = pw.hash_password(new_password)
        user.Password = hashed_password.decode('utf-8')
        db.session.commit()

        session.pop('reset_email')
        return jsonify({'message': f'Hi, {user.Name} ur Password reset successfully! for {user_id}'}), 200

    error_message = session.pop('error_message', None)
    return render_template('reset_password.html', error_message=error_message)


### Visulization...

# Load and preprocess the data
df = pd.read_csv('user_history2.csv')
df['Timestamp'] = pd.to_datetime(df['Timestamp'])
df = df.sort_values(by=["User ID", "Timestamp"]).reset_index(drop=True)

# Calculate session data
session_data = []
for user_id in df["User ID"].unique():
    user_data = df[df["User ID"] == user_id]
    login_time = None

    for _, row in user_data.iterrows():
        if row["Action"] == "Login":
            login_time = row["Timestamp"]
        elif row["Action"] == "Logout" and login_time:
            session_duration = (row["Timestamp"] - login_time).total_seconds() / 60
            session_data.append({
                "User ID": user_id,
                "Username": row["Username"],
                "Role": row["Role"],
                "Login Time": login_time,
                "Logout Time": row["Timestamp"],
                "Session Duration (minutes)": session_duration
            })
            login_time = None

session_df = pd.DataFrame(session_data)
session_df["Session ID"] = session_df.groupby("Username").cumcount() + 1


@login_bp.route('/charts')
def charts():
    # User Role Distribution Pie Chart
    role_counts = df['Role'].value_counts()

    # Create the pie chart
    plt.figure(figsize=(6, 6))
    wedges, texts, autotexts = plt.pie(role_counts, labels=role_counts.index, autopct='%1.1f%%', startangle=90,
                                       colors=['#ff9999', '#66b3ff', '#99ff99', '#ffcc99', '#c2c2f0'], 
                                       wedgeprops={'edgecolor': 'black', 'linewidth': 1, 'linestyle': 'solid'}, 
                                       pctdistance=0.6)  # Moves the labels inside the pie chart

    # Increase font size of the data labels and make them more visible
    for autotext in autotexts:
        autotext.set_fontsize(12)  # Set the font size for the percentage labels inside the pie

    for text in texts:
        text.set_fontsize(12)  # Set the font size for the category labels inside the pie

    # Adjust title and layout
    plt.title('User Role Distribution', fontsize=14)
    plt.axis('equal')  # Equal aspect ratio ensures the pie is a circle

    # Save pie chart to static folder
    pie_chart_path = os.path.join('static', 'pie_chart.png')
    plt.savefig(pie_chart_path, bbox_inches='tight')  # Ensures labels are not cut off
    plt.close()

    # Session Duration Bar Chart
    plt.figure(figsize=(10, 6))  # Reduce the figure size for better presentation
    sns.barplot(data=session_df, x="Username", y="Session Duration (minutes)", hue="Session ID", palette="viridis")
    plt.title("Session Durations per User", fontsize=16)
    plt.xlabel("Username", fontsize=12)
    plt.ylabel("Session Duration (minutes)", fontsize=12)

    # Rotate x-axis labels for better visibility and adjust the font size
    plt.xticks(rotation=45, ha="right", fontsize=10)

    # Adjust legend font size and position
    plt.legend(title="Session ID", bbox_to_anchor=(1.05, 1), loc='upper left', fontsize=10)

    plt.tight_layout()  # Automatically adjusts layout for better fitting

    # Save bar chart to static folder
    bar_chart_path = os.path.join('static', 'session_chart.png')
    plt.savefig(bar_chart_path, bbox_inches='tight')  # Ensures labels are not cut off
    plt.close()

    # Render template with chart images
    return render_template('charts.html', pie_chart_url='static/pie_chart.png', bar_chart_url='static/session_chart.png')