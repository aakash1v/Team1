from flask import Flask, request, jsonify, render_template
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import bcrypt  # Import bcrypt for password hashing

# Flask app setup
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///mydatabase.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SQLALCHEMY_ECHO'] = True

db = SQLAlchemy(app)

# Define the Users table
class Users(db.Model):
    __tablename__ = 'users'
    UserID = db.Column(db.Integer, primary_key=True)
    UserName = db.Column(db.String(50), nullable=False)
    Password = db.Column(db.String(100), nullable=False)
    Email = db.Column(db.String(100), unique=True, nullable=False)
    Name = db.Column(db.String(100), nullable=False)
    DOB = db.Column(db.Date, nullable=True)

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/add_user_form')
def add_user_form():
    return render_template('signup.html')

# Route to insert a user record
@app.route('/add_user', methods=['POST'])
def add_user():
    username = request.form['username']
    email = request.form['email']
    name = request.form['name']
    password = request.form['password']
    dob = request.form['dob']

    try:
        # Convert the date string to a datetime.date object
        dob = datetime.strptime(dob, '%Y-%m-%d').date()
    except ValueError:
        return jsonify({'error': 'Invalid date format. Use YYYY-MM-DD.'}), 400

    # Hash the password before storing it
    hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())

    # Create a new user object
    new_user = Users(UserName=username, Password=hashed_password.decode('utf-8'), Email=email, Name=name, DOB=dob)

    # Add and commit the new user to the database
    try:
        db.session.add(new_user)
        db.session.commit()
        return jsonify({'message': 'User added successfully!'}), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 400

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        # Query the database to find a user by username
        user = Users.query.filter_by(UserName=username).first()

        if user and bcrypt.checkpw(password.encode('utf-8'), user.Password.encode('utf-8')):
            return jsonify({'message': 'Successfully logged in to your account!'}), 201
        else:
            return jsonify({'message': 'Make sure the credentials are correct'}), 401

    return render_template('login.html')

# Initialize database tables
with app.app_context():
    db.create_all()

if __name__ == '__main__':
    app.run(debug=True)
