from flask import Flask, render_template

# Create the Flask app
app = Flask(__name__)

# Simulated login and role data
user_data = {
    "username": "Abhinav",
    "role": "Admin"
}

# Define a route
@app.route('/')
def home():
    # return "Hello, Flask Server!"
    return render_template('index.html', user=user_data)

# Run the app
if __name__ == '__main__':
    app.run(debug=True)

