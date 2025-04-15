from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi
from flask_mail import Mail, Message
from werkzeug.security import generate_password_hash, check_password_hash
from random import randint
from datetime import datetime, timedelta 
import re
import numpy as np
from collections import defaultdict

# --- Flask App Initialization ---
app = Flask(__name__)
app.secret_key = "your_secret_key"

# MongoDB Connection
uri = "mongodb+srv://project:123@miniproject.wi501.mongodb.net/?retryWrites=true&w=majority&appName=MiniProject"
client = MongoClient(uri, server_api=ServerApi('1'))
db = client['carbon']
users_collection = db['users']
footprints_collection = db['footprints']
tasks_collection = db['tasks']

# --- Email Configuration ---
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = 'fahadka007@gmail.com'  # Replace with your email
app.config['MAIL_PASSWORD'] = 'spzv bgxg kjgs zmll'   # Replace with your password
mail = Mail(app)

# Allowed email domains
ALLOWED_DOMAINS = {"gmail.com", "yahoo.com", "outlook.com", "hotmail.com"}

# --- Helper Functions ---
def is_valid_email(email):
    email_regex = r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z]{2,}$'
    if not re.match(email_regex, email):
        return False
    domain = email.split('@')[-1]
    return domain in ALLOWED_DOMAINS

def is_valid_password(password):
    # Check if password is at least 6 characters long
    return len(password) >= 6

def send_otp(email):
    otp = str(randint(100000, 999999))  # Generate 6-digit OTP
    session['otp'] = otp
    
    # Store OTP expiry as a string in ISO format
    otp_expiry = datetime.now() + timedelta(minutes=5)
    session['otp_expiry'] = otp_expiry.isoformat()  # Store as string

    msg = Message("Email Verification - Carbon Footprint",
                  sender=app.config['MAIL_USERNAME'],
                  recipients=[email])
    msg.body = f"Your OTP is: {otp}. It is valid for 5 minutes."
    mail.send(msg)

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
from random import randint

# --- Signup Route with OTP ---
@app.route('/signup', methods=['GET', 'POST'])
def signup():
    error_message = None
    suggested_usernames = []

    if request.method == 'POST':
        name = request.form['name']
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']

        # Check email validity
        if not is_valid_email(email):
            error_message = "Invalid or non-approved email domain! Please use a common provider."
            return render_template('signup.html', error=error_message)

         # Check password validity
        if not is_valid_password(password):
            error_message = "Password must be at least 6 characters long."
            return render_template('signup.html', error=error_message)
        
        # Check for existing email or username
        if users_collection.find_one({"email": email}):
            flash("Email already registered! Please log in.")
            return redirect(url_for('login'))

        if users_collection.find_one({"username": username}):
            for _ in range(3):
                alt_username = f"{username}{randint(100, 999)}"
                if not users_collection.find_one({"username": alt_username}):
                    suggested_usernames.append(alt_username)
            error_message = "Username already taken. Try one of these:"
            return render_template('signup.html', error=error_message, suggestions=suggested_usernames)

        # Store signup data temporarily in session
        session['signup_data'] = {
            "name": name,
            "username": username,
            "email": email,
            "password": password
        }

        # Send OTP
        send_otp(email)

        return redirect(url_for('verify_otp'))

    return render_template('signup.html', error=None)

@app.route('/verify_otp', methods=['GET', 'POST'])
def verify_otp():
    if request.method == 'POST':
        entered_otp = request.form['otp']
        stored_otp = session.get('otp')
        otp_expiry_str = session.get('otp_expiry')

        if not stored_otp or not otp_expiry_str:
            flash("OTP expired or invalid. Please sign up again.")
            return redirect(url_for('signup'))

        # Convert expiry string back to datetime object
        otp_expiry = datetime.fromisoformat(otp_expiry_str)  # Convert string back to datetime

        if datetime.now() > otp_expiry:
            flash("OTP expired. Please sign up again.")
            return redirect(url_for('signup'))

        if entered_otp == stored_otp:
            signup_data = session.pop('signup_data', None)

            if signup_data:

                # Validate password again as a security measure
                if not is_valid_password(signup_data['password']):
                    flash("Invalid password. Password must be at least 6 characters long.")
                    return redirect(url_for('signup'))
                
                # Save the verified user in MongoDB
                hashed_password = generate_password_hash(signup_data['password'])
                users_collection.insert_one({
                    "name": signup_data['name'],
                    "username": signup_data['username'],
                    "email": signup_data['email'],
                    "password": hashed_password,
                    "verified": True,
                    "created_at": datetime.now()
                })

                flash("Email verified successfully!")
                return redirect(url_for('login'))

        flash("Invalid OTP. Please try again.")
        return redirect(url_for('verify_otp'))

    return render_template('verify_otp.html')

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


# --- Forgot Password Routes ---
@app.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        email = request.form['email']
        
        # Check if email exists in the database
        user = users_collection.find_one({"email": email})
        if not user:
            return render_template('forgot_password.html', error="Email not found in our records.")
        
        # Send OTP for password reset
        send_otp(email)
        
        # Store email in session for password reset process
        session['reset_email'] = email
        
        flash("OTP sent to your email. Please verify to reset your password.")
        return redirect(url_for('verify_reset_otp'))
    
    return render_template('forgot_password.html')

@app.route('/verify-reset-otp', methods=['GET', 'POST'])
def verify_reset_otp():
    if request.method == 'POST':
        entered_otp = request.form['otp']
        stored_otp = session.get('otp')
        otp_expiry_str = session.get('otp_expiry')
        reset_email = session.get('reset_email')
        
        if not stored_otp or not otp_expiry_str or not reset_email:
            flash("OTP expired or invalid. Please try again.")
            return redirect(url_for('forgot_password'))
        
        # Convert expiry string back to datetime object
        otp_expiry = datetime.fromisoformat(otp_expiry_str)
        
        if datetime.now() > otp_expiry:
            flash("OTP expired. Please try again.")
            return redirect(url_for('forgot_password'))
        
        if entered_otp == stored_otp:
            # Valid OTP - proceed to password reset
            return redirect(url_for('reset_password'))
        
        flash("Invalid OTP. Please try again.")
    
    return render_template('verify_reset_otp.html')

@app.route('/reset-password', methods=['GET', 'POST'])
def reset_password():
    reset_email = session.get('reset_email')
    
    if not reset_email:
        flash("Password reset session expired. Please try again.")
        return redirect(url_for('forgot_password'))
    
    if request.method == 'POST':
        new_password = request.form['new_password']
        confirm_password = request.form['confirm_password']
        
        # Validate new password
        if not is_valid_password(new_password):
            return render_template('reset_password.html', 
                                  error="Password must be at least 6 characters long.")
        
        # Check if passwords match
        if new_password != confirm_password:
            return render_template('reset_password.html', 
                                  error="Passwords don't match. Please try again.")
        
        # Update password in database
        hashed_password = generate_password_hash(new_password)
        users_collection.update_one(
            {"email": reset_email},
            {"$set": {"password": hashed_password}}
        )
        
        # Clear reset session data
        session.pop('reset_email', None)
        session.pop('otp', None)
        session.pop('otp_expiry', None)
        
        flash("Password reset successfully! Please login with your new password.")
        return redirect(url_for('login'))
    
    return render_template('reset_password.html')

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
       
    # Get today's date (without time)
    today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    tomorrow = today + timedelta(days=1)
    
     # Fetch today's footprint record from MongoDB (if exists)
    today_footprint = footprints_collection.find_one({
        "user": user,
        "date": {"$gte": today, "$lt": tomorrow}
    }, sort=[("date", -1)])  # Sort by date descending to get the latest entry for today

    if today_footprint:
        # Use today's footprint data if available
        result = {
            "total": today_footprint["total_footprint"],
            "breakdown": today_footprint["breakdown"]
        }
    else:
        # Show zero values if no entry for today
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
    seven_days_ago = datetime.now() - timedelta(days=7)
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
    dates = [(datetime.now() - timedelta(days=i)).strftime("%Y-%m-%d") for i in range(6, -1, -1)]

    # Prepare data for the line chart
    totals = []
    for date in dates:
        if date in daily_footprints:
            totals.append(daily_footprints[date]["total_footprint"])
        else:
            totals.append(0)  # No data for this day, set total to 0

    return render_template("dashboard.html", result=result, dates=dates, totals=totals)

# --- change password---
@app.route('/change-password', methods=['POST'])
def change_password():
    if "user" not in session:
        return jsonify({"success": False, "message": "User not logged in."})

    data = request.get_json()
    current_password = data.get('current_password')
    new_password = data.get('new_password')

    # Validate new password
    if not is_valid_password(new_password):
        return jsonify({"success": False, "message": "New password must be at least 6 characters long."})

    # Fetch the logged-in user's details
    user_email = session["user"]
    user = users_collection.find_one({"email": user_email})

    if not user:
        return jsonify({"success": False, "message": "User not found."})

    # Verify current password
    if not check_password_hash(user['password'], current_password):
        return jsonify({"success": False, "message": "Incorrect current password."})

    # Hash the new password
    new_hashed_password = generate_password_hash(new_password)

    # Update the password in MongoDB
    users_collection.update_one(
        {"email": user_email},
        {"$set": {"password": new_hashed_password}}
    )

    return jsonify({"success": True})

# --- Carbon Footprint Calculator Route ---
@app.route('/calculator', methods=['GET'])
def calculator():
    if "user" not in session:
        return redirect(url_for("login"))
    return render_template("calculator.html")

# --- Calculate Route (Updated for Multiple Entries) ---
@app.route('/calculate', methods=['POST'])
def calculate():
    if "user" not in session:
        return redirect(url_for("login"))
        
    user = session["user"]
    
    # Process multiple transport entries
    transport_modes = request.form.getlist('transport_mode[]')
    distances = request.form.getlist('distance[]')
    car_types = request.form.getlist('car_type[]')
    fuel_types = request.form.getlist('fuel_type[]')
    
    # Process multiple energy entries
    electricity_sources = request.form.getlist('electricity_source[]')
    electricity_usages = request.form.getlist('electricity[]')
    cooking_fuels = request.form.getlist('cooking_fuel[]')
    cooking_times = request.form.getlist('cooking_time[]')
    
    # Process food data
    diet_type = request.form.get('diet_type', 'none')
    food_consumed = float(request.form.get('food_consumed', 0))
    
    # Process other data
    waste = float(request.form.get('waste', 0))
    water = float(request.form.get('water', 0))
    
    # Prepare complete data structure
    data = {
        "transport": [],
        "energy": [],
        "food": {
            "diet": diet_type,
            "amount": food_consumed
        },
        "waste": {"amount": waste},
        "water": {"usage": water}
    }
    
    # Fill transport data
    for i in range(len(transport_modes)):
        if i < len(distances) and transport_modes[i] != 'none':
            transport_item = {
                "mode": transport_modes[i],
                "distance": float(distances[i] or 0)
            }
            
            # Add car-specific details if car is selected
            if transport_modes[i] == 'car' and i < len(car_types) and i < len(fuel_types):
                transport_item["car_type"] = car_types[i]
                transport_item["fuel_type"] = fuel_types[i]
                
            data["transport"].append(transport_item)
    
    # Fill energy data
    for i in range(len(electricity_sources)):
        if i < len(electricity_usages) and i < len(cooking_fuels) and i < len(cooking_times):
            if electricity_sources[i] != 'none' or cooking_fuels[i] != 'none':
                energy_item = {
                    "electricity_source": electricity_sources[i],
                    "electricity": float(electricity_usages[i] or 0),
                    "cooking_fuel": cooking_fuels[i],
                    "cooking_time": float(cooking_times[i] or 0)
                }
                data["energy"].append(energy_item)
    
    # Calculate footprint
    result = calculate_footprint(data)
    footprint_data = {
        "user": user, 
        "date": datetime.now(), 
        "total_footprint": result["total"], 
        "breakdown": result["breakdown"],
        "raw_data": data  # Store the raw input data for reference
    }
    
    footprints_collection.insert_one(footprint_data)
    return redirect(url_for('dashboard'))

def calculate_footprint(data):
    # Base emission factors
    base_factors = {
        "none": 0,
        "car": 0.21,  # Base car emission factor
        "public_transport": 0.11,
        "train": 0.06,
        "flight": 0.25,
        "marine": 0.30,  # New factor for marine transport
        
        # Electricity source factors
        "non_renewable_electricity": 0.5,
        "renewable_electricity": 0.1,
        "mixed_electricity": 0.3,
        
        # Cooking fuel factors
        "lpg": 0.3,
        "wood": 0.5,
        "electric": 0.1,  # This depends on electricity source
        "natural_gas": 0.2,
        
        "meat_diet": 3.3,
        "vegetarian_diet": 1.5,
        "vegan_diet": 0.8,
        "waste": 0.5,
        "water": 0.006
    }
    
    # Car type multipliers
    car_type_factors = {
        "compact": 0.8,   # More efficient than base
        "medium": 1.0,    # Base reference
        "suv": 1.5,       # Less efficient
        "luxury": 1.8     # Least efficient
    }
    
    # Fuel type multipliers
    fuel_type_factors = {
        "petrol": 1.0,    # Base reference
        "diesel": 1.1,    # Slightly higher emissions
        "electric": 0.3,  # Much lower emissions
        "hybrid": 0.7,    # Lower emissions
        "cng": 0.8        # Lower emissions than petrol
    }
    
    # Initialize footprint components
    transport_footprint = 0
    energy_footprint = 0
    
    # Calculate transport footprint for all transport entries
    for transport_item in data.get("transport", []):
        transport_mode = transport_item.get("mode", "none")
        distance = transport_item.get("distance", 0)
        
        if transport_mode == "car":
            # Get car type and fuel type from data
            car_type = transport_item.get("car_type", "medium")
            fuel_type = transport_item.get("fuel_type", "petrol")
            
            # Calculate adjusted emission factor for the specific car and fuel type
            car_factor = base_factors["car"] * car_type_factors.get(car_type, 1.0) * fuel_type_factors.get(fuel_type, 1.0)
            transport_footprint += distance * car_factor
        else:
            # For other transport modes, use the base factor
            transport_footprint += distance * base_factors.get(transport_mode, 0)
    
    # Calculate energy footprint for all energy entries
    for energy_item in data.get("energy", []):
        electricity_source = energy_item.get("electricity_source", "non_renewable")
        electricity_usage = energy_item.get("electricity", 0)
        cooking_fuel = energy_item.get("cooking_fuel", "lpg")
        cooking_time = energy_item.get("cooking_time", 0)
        
        # Calculate electricity footprint based on source
        electricity_factor = base_factors.get(f"{electricity_source}_electricity", base_factors["non_renewable_electricity"])
        electricity_footprint = electricity_usage * electricity_factor
        
        # Calculate cooking footprint
        cooking_factor = base_factors.get(cooking_fuel, 0.3)
        # For electric cooking, factor in the electricity source
        if cooking_fuel == "electric":
            cooking_factor *= electricity_factor / base_factors["non_renewable_electricity"]
        
        cooking_footprint = cooking_time * cooking_factor
        
        # Add to total energy footprint
        energy_footprint += electricity_footprint + cooking_footprint
    
    # Calculate other footprint components
    diet_type = data.get("food", {}).get("diet", "meat_diet")
    food_amount = data.get("food", {}).get("amount", 1)
    food_footprint = base_factors.get(diet_type, base_factors["meat_diet"]) * food_amount
    
    waste_footprint = data.get("waste", {}).get("amount", 0) * base_factors["waste"]
    water_footprint = data.get("water", {}).get("usage", 0) * base_factors["water"]
    
    total_footprint = transport_footprint + energy_footprint + food_footprint + waste_footprint + water_footprint
    
    return {
        "total": total_footprint, 
        "breakdown": {
            "transport": transport_footprint, 
            "energy": energy_footprint, 
            "food": food_footprint, 
            "waste": waste_footprint, 
            "water": water_footprint
        }
    }

# Add this new route to your Flask app
@app.route('/suggestions', methods=['GET'])
def suggestions():
    if "user" not in session:
        return redirect(url_for("login"))
    
    user = session["user"]
    
    
    # Fetch the user's latest footprint data
    latest_footprint = footprints_collection.find_one(
        {"user": user}, 
        sort=[("date", -1)]
    )
    
    if not latest_footprint:
        # If no footprint data exists, redirect to calculator
        flash("Please calculate your carbon footprint first to get personalized suggestions.")
        return redirect(url_for("calculator"))
    
    # Generate suggestions based on footprint data
    suggestions = generate_suggestions(latest_footprint)
    
    # Get user's footprint breakdown for display
    footprint_breakdown = latest_footprint.get("breakdown", {})
    total_footprint = latest_footprint.get("total_footprint", 0)
    
    return render_template(
        "suggestions.html", 
        suggestions=suggestions, 
        footprint_breakdown=footprint_breakdown,
        total_footprint=total_footprint
    )
def generate_suggestions(footprint_data):
    """Generate highly personalized suggestions based on user's carbon footprint data."""
    suggestions = {
        "transport": [],
        "energy": [],
        "food": [],
        "waste": [],
        "water": [],
        "general": []
    }
    
    breakdown = footprint_data.get("breakdown", {})
    raw_data = footprint_data.get("raw_data", {})
    total_footprint = footprint_data.get("total_footprint", 0)
    
    # Transport suggestions - more detailed and contextual
    transport_footprint = breakdown.get("transport", 0)
    transport_data = raw_data.get("transport", [])
    
    # Analyze transport patterns
    car_usage = False
    flight_usage = False
    car_type = None
    fuel_type = None
    total_car_distance = 0
    total_flight_distance = 0
    
    for transport_item in transport_data:
        mode = transport_item.get("mode")
        distance = transport_item.get("distance", 0)
        
        if mode == "car":
            car_usage = True
            total_car_distance += distance
            car_type = transport_item.get("car_type")
            fuel_type = transport_item.get("fuel_type")
        elif mode == "flight":
            flight_usage = True
            total_flight_distance += distance
    
    # Car-specific suggestions
    if car_usage:
        # High car usage suggestions
        if total_car_distance > 100:
            suggestions["transport"].append({
                "title": "Reduce car travel by carpooling",
                "description": f"You drive approximately {total_car_distance} km. Carpooling for just 2 days a week could reduce your emissions by up to 40%.",
                "impact": "high"
            })
        
        # Car type & fuel suggestions
        if fuel_type in ["petrol", "diesel"]:
            suggestions["transport"].append({
                "title": "Consider switching to an electric or hybrid vehicle",
                "description": f"Your {fuel_type}-powered {car_type} vehicle produces significant emissions. An electric vehicle could reduce your transport emissions by up to 70%.",
                "impact": "high"
            })
        elif fuel_type == "hybrid":
            suggestions["transport"].append({
                "title": "Maximize electric mode usage in your hybrid",
                "description": "Ensure you're charging your hybrid regularly and using electric-only mode for shorter trips to minimize fuel consumption.",
                "impact": "medium"
            })
        
        if car_type in ["suv", "luxury"]:
            suggestions["transport"].append({
                "title": "Consider downsizing your vehicle",
                "description": f"Your {car_type} vehicle consumes more fuel than necessary. A compact or mid-size car could reduce your emissions by 30-50% while meeting your needs.",
                "impact": "high"
            })
        
        # Short trip suggestions
        if total_car_distance < 30:
            suggestions["transport"].append({
                "title": "Replace short car trips with active transport",
                "description": "Your car journeys appear to be relatively short. Consider cycling or walking for trips under 5km, which can eliminate those emissions completely.",
                "impact": "medium"
            })
    
    # Flight suggestions
    if flight_usage:
        suggestions["transport"].append({
            "title": "Reduce air travel impact",
            "description": f"You've traveled {total_flight_distance} km by air. Consider carbon offsetting programs or choosing direct flights which have lower emissions than flights with connections.",
            "impact": "high"
        })
        
        if total_flight_distance > 5000:
            suggestions["transport"].append({
                "title": "Consider train travel for shorter journeys",
                "description": "For continental travel under 1000km, trains produce about 75% less carbon than flights and offer comparable journey times when including airport procedures.",
                "impact": "high"
            })
    
    # Public transport encouragement
    if transport_footprint > 5 and not any(item.get("mode") == "public_transport" for item in transport_data):
        suggestions["transport"].append({
            "title": "Integrate public transportation into your routine",
            "description": "Using public transit for your commute just 2-3 days per week could reduce your transport emissions by 20-30%.",
            "impact": "high"
        })
    
    # Energy suggestions - more detailed based on actual usage
    energy_footprint = breakdown.get("energy", 0)
    energy_data = raw_data.get("energy", [])
    
    # Analyze energy usage patterns
    total_electricity = 0
    using_renewable = False
    cooking_methods = set()
    
    for energy_item in energy_data:
        electricity_source = energy_item.get("electricity_source")
        electricity_usage = energy_item.get("electricity", 0)
        cooking_fuel = energy_item.get("cooking_fuel")
        
        total_electricity += electricity_usage
        if electricity_source in ["renewable_electricity", "mixed_electricity"]:
            using_renewable = True
        if cooking_fuel:
            cooking_methods.add(cooking_fuel)
    
    # Electricity suggestions
    if total_electricity > 0:
        if not using_renewable:
            suggestions["energy"].append({
                "title": "Switch to a renewable energy provider",
                "description": f"Your {total_electricity} kWh from non-renewable sources produces significant emissions. Switching to a green energy provider can reduce this by up to 90%.",
                "impact": "high"
            })
            
            suggestions["energy"].append({
                "title": "Install home solar panels",
                "description": "Based on your electricity usage, installing solar panels could pay for themselves within 5-8 years while significantly reducing your carbon footprint.",
                "impact": "high"
            })
        
        if total_electricity > 300:
            suggestions["energy"].append({
                "title": "Conduct a home energy audit",
                "description": "Your electricity usage is above average. An energy audit can identify specific areas to improve efficiency, potentially reducing usage by 20-30%.",
                "impact": "medium"
            })
            
            suggestions["energy"].append({
                "title": "Upgrade to energy-efficient appliances",
                "description": "Replace older appliances with Energy Star rated ones, which can reduce electricity consumption by 10-50% depending on the appliance.",
                "impact": "medium"
            })
    
    # Cooking suggestions
    if "lpg" in cooking_methods or "natural_gas" in cooking_methods:
        suggestions["energy"].append({
            "title": "Transition to induction cooking",
            "description": "Gas cooking contributes to your footprint. Induction cooking is 85-90% energy efficient compared to 40% for gas and produces no indoor air pollution.",
            "impact": "medium"
        })
    
    if "wood" in cooking_methods:
        suggestions["energy"].append({
            "title": "Replace wood cooking with cleaner alternatives",
            "description": "Wood burning for cooking produces significant emissions and particulate matter. Electric or induction cooking powered by renewable energy is much cleaner.",
            "impact": "high"
        })
    
    # Food suggestions - more nuanced based on diet
    food_footprint = breakdown.get("food", 0)
    diet_type = raw_data.get("food", {}).get("diet")
    food_amount = raw_data.get("food", {}).get("amount", 0)
    
    # Diet-specific suggestions
    if diet_type == "meat_diet":
        suggestions["food"].append({
            "title": "Adopt a 'flexitarian' approach",
            "description": "By reducing red meat consumption to 1-2 times per week and replacing with plant proteins or poultry, you could reduce your food footprint by 20-30%.",
            "impact": "high"
        })
        
        suggestions["food"].append({
            "title": "Try 'Meatless Mondays'",
            "description": "Starting with just one meat-free day per week can reduce your annual food carbon footprint by up to 15%.",
            "impact": "medium"
        })
    
    elif diet_type == "vegetarian_diet":
        suggestions["food"].append({
            "title": "Reduce dairy consumption",
            "description": "Dairy products have a high carbon footprint. Try plant-based milk alternatives and limit cheese consumption to further reduce your impact.",
            "impact": "medium"
        })
    
    # Food waste suggestions
    if food_amount > 2:
        suggestions["food"].append({
            "title": "Plan meals to reduce food waste",
            "description": "The average household wastes 30% of food purchased. Planning meals, proper storage, and using leftovers can significantly reduce your food carbon footprint.",
            "impact": "medium"
        })
    
    # Local food suggestions
    suggestions["food"].append({
        "title": "Shop at farmers markets and buy seasonal produce",
        "description": "Local, seasonal food can reduce the carbon footprint of your diet by up to 10% by minimizing transportation and storage emissions.",
        "impact": "medium"
    })
    
    # Waste suggestions - more actionable
    waste_footprint = breakdown.get("waste", 0)
    waste_amount = raw_data.get("waste", {}).get("amount", 0)
    
    if waste_amount > 0:
        # Tailored waste reduction suggestions
        if waste_amount > 1.5:
            suggestions["waste"].append({
                "title": "Implement a comprehensive recycling system",
                "description": f"Your waste output of {waste_amount} kg is above average. Setting up dedicated bins for different recyclables can reduce landfill waste by up to 70%.",
                "impact": "high"
            })
            
            suggestions["waste"].append({
                "title": "Start composting food scraps",
                "description": "Food waste in landfills produces methane. Composting can reduce your waste footprint while creating nutrient-rich soil for plants.",
                "impact": "high"
            })
        
        suggestions["waste"].append({
            "title": "Adopt zero-waste shopping practices",
            "description": "Using reusable bags, buying in bulk with your own containers, and choosing products with minimal packaging can reduce waste by up to 80%.",
            "impact": "medium"
        })
        
        suggestions["waste"].append({
            "title": "Focus on reducing single-use plastics",
            "description": "Replace disposable items with reusable alternatives: water bottles, coffee cups, straws, and food containers.",
            "impact": "medium"
        })
    
    # Water suggestions - more specific
    water_footprint = breakdown.get("water", 0)
    water_usage = raw_data.get("water", {}).get("usage", 0)
    
    if water_usage > 0:
        if water_usage > 150:
            suggestions["water"].append({
                "title": "Install water-efficient fixtures",
                "description": f"Your water usage of {water_usage} liters is high. Low-flow showerheads, faucet aerators, and dual-flush toilets can reduce water use by 40-50%.",
                "impact": "high"
            })
            
            suggestions["water"].append({
                "title": "Fix leaks and drips immediately",
                "description": "A single dripping faucet can waste over 11,000 liters of water annually. Check for and repair leaks in your home.",
                "impact": "medium"
            })
        
        if water_usage > 200:
            suggestions["water"].append({
                "title": "Install rainwater harvesting system",
                "description": "Your high water usage suggests potential for rainwater collection. A basic system can collect thousands of liters annually for garden use.",
                "impact": "high"
            })
        
        suggestions["water"].append({
            "title": "Take shorter showers",
            "description": "Reducing shower time by just 2 minutes can save up to 40 liters of water per shower.",
            "impact": "low"
        })
    
    # General suggestions - more actionable and measurable
    # Calculate carbon intensity (footprint per unit of activity)
    carbon_intensity = total_footprint / max(sum(breakdown.values()), 1)
    
    suggestions["general"].append({
        "title": "Track your progress with monthly carbon calculations",
        "description": "Regular monitoring helps identify which changes have the biggest impact. Aim to reduce your footprint by 5% each month.",
        "impact": "medium"
    })
    
    # Community engagement
    suggestions["general"].append({
        "title": "Join a local climate action group",
        "description": "Community efforts can provide support, amplify your impact, and create systemic change beyond individual actions.",
        "impact": "medium"
    })
    
    # Carbon offsetting for remaining emissions
    suggestions["general"].append({
        "title": "Consider carbon offsetting for unavoidable emissions",
        "description": f"For your {total_footprint:.1f} kg footprint, quality carbon offset projects cost about ${total_footprint*0.015:.2f} monthly and support renewable energy, reforestation, and more.",
        "impact": "medium"
    })
    
    # Technology suggestion
    suggestions["general"].append({
        "title": "Use smart home technology to reduce energy waste",
        "description": "Smart thermostats, lighting, and power strips can reduce your energy consumption by 10-15% by eliminating standby power and optimizing usage.",
        "impact": "medium"
    })
    
    # Prioritize suggestions based on highest impact areas
    sorted_breakdown = sorted(breakdown.items(), key=lambda x: x[1], reverse=True)
    priority_areas = [area for area, value in sorted_breakdown if value > 0]
    
    # Focus on high impact areas
    if priority_areas:
        top_area = priority_areas[0]
        area_percentage = (breakdown.get(top_area, 0) / total_footprint) * 100 if total_footprint > 0 else 0
        
        suggestions["general"].insert(0, {
            "title": f"Focus on your {top_area} footprint first",
            "description": f"Your {top_area} activities contribute {area_percentage:.1f}% of your total footprint. Prioritizing changes in this area will have the biggest impact.",
            "impact": "high"
        })
        
        # If there's a significant second contributor
        if len(priority_areas) > 1 and breakdown.get(priority_areas[1], 0) > (total_footprint * 0.2):
            second_area = priority_areas[1]
            suggestions["general"].append({
                "title": f"Next, address your {second_area} footprint",
                "description": f"After tackling your {top_area} footprint, focus on {second_area} for the next biggest impact reduction.",
                "impact": "medium"
            })
    
    # Personalized impact summary
    if total_footprint > 0:
        average_daily_footprint = 12  # kg CO2e, global average estimation
        comparison = (total_footprint / average_daily_footprint) * 100
        
        if comparison > 120:
            status = "significantly higher than"
        elif comparison > 80:
            status = "about average compared to"
        else:
            status = "lower than"
            
        suggestions["general"].append({
            "title": "Understand your current impact",
            "description": f"Your footprint is {status} the global average. Following our top 3 suggestions could reduce it by approximately {min(75, max(20, int(comparison - 70)))}%.",
            "impact": "medium"
        })
    
    return suggestions

@app.route('/offsetting_sites')
def offsetting_sites():
    return render_template('offsetting_sites.html')

# Define eco-friendly tasks and their Earth Coins
ECO_TASKS = {
    "use_public_transport": {"name": "Use Public Transportation for a Week", "points": 5},
    "carpool": {"name": "Carpool with Friends or Colleagues", "points": 3},
    "walk_or_bike": {"name": "Walk or Bike for Short Trips", "points": 2},
    "switch_to_electric_vehicle": {"name": "Switch to an Electric or Hybrid Vehicle", "points": 10},
    "switch_to_led_bulbs": {"name": "Switch to LED Bulbs", "points": 3},
    "unplug_electronics": {"name": "Unplug Electronics When Not in Use", "points": 2},
    "install_solar_panels": {"name": "Install Solar Panels", "points": 15},
    "use_programmable_thermostat": {"name": "Use a Programmable Thermostat", "points": 4},
    "reduce_meat_consumption": {"name": "Reduce Meat Consumption for a Week", "points": 7},
    "buy_local_produce": {"name": "Buy Local and Seasonal Produce", "points": 3},
    "compost_food_waste": {"name": "Compost Food Waste", "points": 4},
    "avoid_food_waste": {"name": "Avoid Food Waste", "points": 5},
    "recycle_waste": {"name": "Recycle 5 kg of Waste", "points": 4},
    "use_reusable_bags": {"name": "Use Reusable Bags and Containers", "points": 3},
    "donate_or_repurpose": {"name": "Donate or Repurpose Old Items", "points": 2},
    "avoid_single_use_plastics": {"name": "Avoid Single-Use Plastics", "points": 5},
    "reduce_shower_time": {"name": "Reduce Shower Time by 5 Minutes", "points": 2},
    "fix_leaky_faucets": {"name": "Fix Leaky Faucets", "points": 3},
    "install_water_saving_fixtures": {"name": "Install Water-Saving Fixtures", "points": 4},
    "collect_rainwater": {"name": "Collect Rainwater for Gardening", "points": 5},
    "plant_a_tree": {"name": "Plant a Tree", "points": 10},
    "community_cleanup": {"name": "Participate in a Community Cleanup", "points": 5},
    "start_home_garden": {"name": "Start a Home Garden", "points": 6},
    "support_renewable_energy": {"name": "Support Renewable Energy Projects", "points": 8},
    "educate_others": {"name": "Educate Others About Carbon Footprint", "points": 3},
    "calculate_carbon_footprint": {"name": "Calculate and Track Your Carbon Footprint", "points": 2},
    "switch_green_energy_provider": {"name": "Switch to a Green Energy Provider", "points": 7},
    "reduce_air_travel": {"name": "Reduce Air Travel", "points": 10},
    "adopt_zero_waste_lifestyle": {"name": "Adopt a Zero-Waste Lifestyle", "points": 15},
    "offset_carbon_emissions": {"name": "Offset Your Carbon Emissions", "points": 10},
    "upgrade_energy_efficient_appliances": {"name": "Upgrade to Energy-Efficient Appliances", "points": 8},
    "support_sustainable_brands": {"name": "Support Sustainable Brands", "points": 4},
}

@app.route('/tasks', methods=['GET', 'POST'])
def tasks():
    if "user" not in session:
        return redirect(url_for("login"))

    user = session["user"]

    if request.method == 'POST':
        task_id = request.form['task_id']
        quantity = float(request.form['quantity'])

        # Get task details from ECO_TASKS
        task = ECO_TASKS.get(task_id)
        if task:
            points_earned = task['points'] * quantity

            # Save the task completion to MongoDB
            tasks_collection.insert_one({
                "user": user,
                "task_id": task_id,
                "task_name": task['name'],
                "quantity": quantity,
                "points_earned": points_earned,
                "date": datetime.now()
            })

            return redirect(url_for('tasks'))

    # Fetch all tasks completed by the user
    user_tasks = list(tasks_collection.find({"user": user}))

    # Calculate total Earth Coins earned (default to 0 if no tasks)
    total_coins = sum(task.get('points_earned', 0) for task in user_tasks)

    return render_template("tasks.html", eco_tasks=ECO_TASKS, user_tasks=user_tasks, total_coins=total_coins)

@app.route('/leaderboard')
def leaderboard():
    # Fetch all users
    users = users_collection.find()

    leaderboard_data = []
    for user in users:
        user_email = user["email"]

        # Fetch all tasks completed by the user
        user_tasks = list(tasks_collection.find({"user": user_email}))

        # Calculate total Earth Coins earned (default to 0 if no tasks)
        total_coins = sum(task.get('points_earned', 0) for task in user_tasks)

        # Add user data to the leaderboard
        leaderboard_data.append({
            "username": user["username"],
            "email": user_email,
            "total_coins": total_coins  # Ensure this is always a number
        })

    # Sort users by total Earth Coins (highest first)
    leaderboard_data.sort(key=lambda x: x["total_coins"], reverse=True)

    return render_template("leaderboard.html", leaderboard_data=leaderboard_data)

if __name__ == '__main__':
    app.run(debug=True)