from flask import Flask, request, jsonify, render_template, redirect, url_for, session
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import bcrypt  # Import bcrypt for password hashing

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

@app.route('/add_user_form')
def add_user_form():
    return render_template('signup.html')

# Route to insert a user record
@app.route('/add_user', methods=['POST'])
def add_user():
    # Retrieving form data
    username = request.form['username']
    email = request.form['email']
    name = request.form['username']  # Assuming the user's name is the same as the username for simplicity
    password = request.form['password']
    dob = request.form['dob']
    role = request.form.get('role')  # Optional field
    phone_number = request.form.get('phone_number')  # Optional field

    try:
        # Convert the date string to a datetime.date object
        dob = datetime.strptime(dob, '%Y-%m-%d').date()
    except ValueError:
        return jsonify({'error': 'Invalid date format. Use YYYY-MM-DD.'}), 400

    # Hash the password before storing it
    hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())

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

@app.route('/', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        # Query the database to find a user by username
        user = Users.query.filter_by(UserName=username).first()

        if user and bcrypt.checkpw(password.encode('utf-8'), user.Password.encode('utf-8')):
            # Successful login
            session.pop('error_message', None)  # Clear any previous error messages
            return jsonify({'message': 'Successfully logged in to your account!'}), 201
        else:
            # Store the error message in session
            session['error_message'] = 'Wrong password. Please try again.'
            return redirect(url_for('login'))

    # Retrieve the error message from session (if any)
    error_message = session.pop('error_message', None)
    return render_template('login.html', error_message=error_message)

# Initialize database tables
with app.app_context():
    db.create_all()

if __name__ == '__main__':
    app.run(debug=True)
