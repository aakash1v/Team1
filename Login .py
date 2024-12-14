from flask import Flask, request, render_template, redirect, url_for

# Flask application
app = Flask(__name__)

# Mock credentials for login
VALID_USERNAME = "admin"
VALID_PASSWORD = "password123"

# Routes
@app.route('/')
def login_page():
    return '''
        <h1>Login</h1>
        <form action="/login" method="post">
            <label for="username">Username:</label>
            <input type="text" id="username" name="username"><br><br>
            <label for="password">Password:</label>
            <input type="password" id="password" name="password"><br><br>
            <button type="submit">Login</button>
        </form>
        <p>
            <a href="/forgot-password">Forgot Password?</a> |
            <a href="/new-user">New User? Sign Up</a>
        </p>
    '''

@app.route('/login', methods=['POST'])
def login():
    username = request.form.get('username')
    password = request.form.get('password')

    if username == VALID_USERNAME and password == VALID_PASSWORD:
        return f"<h1>Welcome, {username}!</h1><p>Login successful.</p>"
    else:
        return '''
            <h1>Login Failed</h1>
            <p>Invalid username or password. Please try again.</p>
            <a href="/">Go back to Login</a>
        '''

@app.route('/forgot-password')
def forgot_password():
    return '''
        <h1>Forgot Password</h1>
        <p>To reset your password, please contact the system administrator or click below:</p>
        <form action="/reset-password" method="post">
            <label for="email">Enter your email:</label>
            <input type="email" id="email" name="email"><br><br>
            <button type="submit">Reset Password</button>
        </form>
        <a href="/">Back to Login</a>
    '''

@app.route('/new-user')
def new_user():
    return '''
        <h1>New User Registration</h1>
        <form action="/register" method="post">
            <label for="username">Username:</label>
            <input type="text" id="username" name="username"><br><br>
            <label for="password">Password:</label>
            <input type="password" id="password" name="password"><br><br>
            <label for="email">Email:</label>
            <input type="email" id="email" name="email"><br><br>
            <button type="submit">Register</button>
        </form>
        <a href="/">Back to Login</a>
    '''

@app.route('/reset-password', methods=['POST'])
def reset_password():
    email = request.form.get('email')
    return f"<h1>Password Reset</h1><p>Instructions have been sent to {email}.</p><a href='/'>Back to Login</a>"

@app.route('/register', methods=['POST'])
def register():
    username = request.form.get('username')
    password = request.form.get('password')
    email = request.form.get('email')
    return f"<h1>Registration Successful</h1><p>Welcome, {username}! Your account has been created with email {email}.</p><a href='/'>Go to Login</a>"

# Run the application
if __name__ == '__main__':
    app.run(debug=True)
