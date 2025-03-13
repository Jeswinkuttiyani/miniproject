from flask import Flask, render_template, request, redirect, url_for, session
from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi
from werkzeug.security import generate_password_hash, check_password_hash
import re

app = Flask(__name__)
app.secret_key = "your_secret_key"

# MongoDB Connection
uri = "mongodb+srv://project:123@miniproject.wi501.mongodb.net/?retryWrites=true&w=majority&appName=MiniProject"
client = MongoClient(uri, server_api=ServerApi('1'))

db = client['carbon']
users_collection = db['users']  # ✅ Use only one collection named 'users'

# Allowed email domains
ALLOWED_DOMAINS = {"gmail.com", "yahoo.com", "outlook.com", "hotmail.com"}

# Email validation function
def is_valid_email(email):
    """Check if the email format is valid and belongs to an allowed domain."""
    email_regex = r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z]{2,}$'
    
    if not re.match(email_regex, email):
        return False

    domain = email.split('@')[-1]

    # Allow only specific trusted email providers
    if domain not in ALLOWED_DOMAINS:
        return False

    return True

# --- Home Route ---
@app.route('/')
def home():
    return render_template('frontpage.html')

# --- Render DF Pages ---
@app.route('/df1')
def df1():
    return render_template('df1.html')

@app.route('/df2')
def df2():
    return render_template('df2.html')

@app.route('/df3')
def df3():
    return render_template('df3.html')

@app.route('/df4')
def df4():
    return render_template('df4.html')

# --- Signup Route ---
@app.route('/signup', methods=['GET', 'POST'])
def signup():
    error_message = None  # Initialize error message variable

    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        password = request.form['password']
        
        # ✅ Validate email format and domain
        if not is_valid_email(email):
            error_message = "Invalid or non-approved email domain! Please use a common provider."
            return render_template('signup.html', error=error_message)

        hashed_password = generate_password_hash(password)

        # Check if user already exists
        existing_user = users_collection.find_one({"email": email})
        if existing_user:
            error_message = "Email already registered! Please log in."
            return render_template('signup.html', error=error_message)

        # Insert new user into MongoDB
        users_collection.insert_one({
            "name": name,
            "email": email,
            "password": hashed_password
        })
        return redirect(url_for('login'))  # Redirect to login after successful signup

    return render_template('signup.html', error=None)

# --- Login Route ---
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        # Fetch user from MongoDB
        user = users_collection.find_one({"email": email})

        if user and check_password_hash(user['password'], password):
            session['user'] = user['name']
            return render_template('success.html', email=email)
        else:
            return render_template('login2.html', error="Invalid Login, try again.")

    return render_template('login2.html', error=None)

# --- Logout Route ---
@app.route('/logout')
def logout():
    session.pop('user', None)
    return redirect(url_for('home'))

if __name__ == '__main__':
    app.run(debug=True)
