from flask import Flask, render_template, request, redirect, url_for, session, jsonify
from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi
from werkzeug.security import generate_password_hash, check_password_hash
import datetime
import re

app = Flask(__name__)
app.secret_key = "your_secret_key"

# MongoDB Connection
uri = "mongodb+srv://project:123@miniproject.wi501.mongodb.net/?retryWrites=true&w=majority&appName=MiniProject"
client = MongoClient(uri, server_api=ServerApi('1'))
db = client['carbon']
users_collection = db['users']
footprints_collection = db['footprints']

# Allowed email domains
ALLOWED_DOMAINS = {"gmail.com", "yahoo.com", "outlook.com", "hotmail.com"}

def is_valid_email(email):
    email_regex = r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z]{2,}$'
    if not re.match(email_regex, email):
        return False
    domain = email.split('@')[-1]
    return domain in ALLOWED_DOMAINS

# --- Home Route ---
@app.route('/')
def home():
    return render_template('frontpage.html')

# --- Additional Page Routes ---
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
    error_message = None  
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        password = request.form['password']
        
        if not is_valid_email(email):
            error_message = "Invalid or non-approved email domain! Please use a common provider."
            return render_template('signup.html', error=error_message)
        
        hashed_password = generate_password_hash(password)
        existing_user = users_collection.find_one({"email": email})
        if existing_user:
            error_message = "Email already registered! Please log in."
            return render_template('signup.html', error=error_message)
        
        users_collection.insert_one({
            "name": name,
            "email": email,
            "password": hashed_password
        })
        return redirect(url_for('login')) 
    return render_template('signup.html', error=None)

# --- Login Route ---
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        user = users_collection.find_one({"email": email})
        if user and check_password_hash(user['password'], password):
            session['user'] = user['email']
            return redirect(url_for('dashboard'))
        else:
            return render_template('login.html', error="Invalid Login, try again.")
    return render_template('login.html', error=None)

# --- Logout Route ---
@app.route('/logout')
def logout():
    session.pop('user', None)
    return redirect(url_for('home'))

# --- Dashboard Route ---
@app.route('/dashboard', methods=['GET'])
def dashboard():
    if "user" not in session:
        return redirect(url_for("login"))

    user = session["user"]

    # Fetch the most recent footprint record from MongoDB
    last_footprint = footprints_collection.find_one({"user": user}, sort=[("date", -1)])

    if last_footprint:
        result = {
            "total": last_footprint["total_footprint"],
            "breakdown": last_footprint["breakdown"]
        }
    else:
        # Default values for first-time login users
        result = {
            "total": 0,
            "breakdown": {
                "transport": 0,
                "energy": 0,
                "food": 0,
                "waste": 0,
                "water": 0
            }
        }

    # Fetch the last 7 days of carbon footprint data
    seven_days_ago = datetime.datetime.now() - datetime.timedelta(days=7)
    last_7_days_footprints = list(footprints_collection.find({
        "user": user,
        "date": {"$gte": seven_days_ago}
    }, sort=[("date", 1)]))

    # Group footprints by day and keep only the last entry for each day
    daily_footprints = {}
    for footprint in last_7_days_footprints:
        date_str = footprint["date"].strftime("%Y-%m-%d")  # Group by date (without time)
        daily_footprints[date_str] = footprint  # Overwrite with the latest entry for the day

    # Generate a list of the last 7 days (including today)
    dates = [(datetime.datetime.now() - datetime.timedelta(days=i)).strftime("%Y-%m-%d") for i in range(6, -1, -1)]

    # Prepare data for the line chart
    totals = []
    for date in dates:
        if date in daily_footprints:
            totals.append(daily_footprints[date]["total_footprint"])
        else:
            totals.append(0)  # No data for this day, set total to 0

    return render_template("dashboard.html", result=result, dates=dates, totals=totals)
# --- Carbon Footprint Calculator Route ---
@app.route('/calculator', methods=['GET'])
def calculator():
    if "user" not in session:
        return redirect(url_for("login"))
    return render_template("calculator.html")

# --- Calculate Route (New Page for Results) ---
@app.route('/calculate', methods=['POST'])
def calculate():
    if "user" not in session:
        return redirect(url_for("login"))
    user = session["user"]
    data = {
        "transport": {"mode": request.form["transport_mode"], "distance": float(request.form["distance"] or 0)},
        "energy": {"electricity": float(request.form["electricity"] or 0), "natural_gas": float(request.form["natural_gas"] or 0)},
        "food": {"diet": request.form["diet_type"]},
        "waste": {"amount": float(request.form["waste"] or 0)},
        "water": {"usage": float(request.form["water"] or 0)}
    }
    result = calculate_footprint(data)
    footprint_data = {"user": user, "date": datetime.datetime.now(), "total_footprint": result["total"], "breakdown": result["breakdown"]}
    footprints_collection.insert_one(footprint_data)
    return redirect(url_for('dashboard'))

def calculate_footprint(data):
    factors = {"car": 0.21, "bus": 0.11, "train": 0.06, "flight": 0.25, "electricity": 0.4, "natural_gas": 2.3, "meat_diet": 3.3, "vegetarian_diet": 1.5, "vegan_diet": 0.8, "waste": 0.5, "water": 0.3}
    transport = data.get("transport", {}).get("distance", 0) * factors.get(data.get("transport", {}).get("mode", "car"), 0)
    energy = data.get("energy", {}).get("electricity", 0) * factors["electricity"] + data.get("energy", {}).get("natural_gas", 0) * factors["natural_gas"]
    food = factors[data.get("food", {}).get("diet", "meat_diet")]
    waste = data.get("waste", {}).get("amount", 0) * factors["waste"]
    water = data.get("water", {}).get("usage", 0) * factors["water"]
    total_footprint = transport + energy + food + waste + water
    return {"total": total_footprint, "breakdown": {"transport": transport, "energy": energy, "food": food, "waste": waste, "water": water}}

if __name__ == '__main__':
    app.run(debug=True)