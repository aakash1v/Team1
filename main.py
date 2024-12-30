from flask import Flask, redirect, url_for
from routers.team1 import login_bp  # Import the auth blueprint
from database import db  # Import the db instance
import os

# Flask app factory
def create_app():
    app = Flask(__name__)

    # Configurations
    app.config['SECRET_KEY'] = '8BYkEfBA6O6donzWlSihBXox7C0sKR6b'
    app.config['SESSION_COOKIE_NAME'] = 'your_session_cookie_name'

    app.config['SQLALCHEMY_DATABASE_URI'] = f"sqlite:///{os.path.join(app.instance_path, 'mydatabase.db')}"
    os.makedirs(app.instance_path, exist_ok=True)
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['SQLALCHEMY_ECHO'] = True

    # Initialize extensions
    db.init_app(app)

    # Register the auth blueprint with the url_prefix 'auth'
    app.register_blueprint(login_bp, url_prefix='/auth')

    # Redirect the root route to '/auth'
    @app.route('/')
    def index():
        return redirect(url_for('auth.login'))  # Redirect to the login route of the 'auth' blueprint

    # Create tables if necessary
    with app.app_context():
        db.create_all()

    return app

if __name__ == '__main__':
    app = create_app()
    app.run(debug=True)
