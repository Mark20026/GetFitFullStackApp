import os
import re

from cs50 import SQL
from flask import Flask, flash, redirect, render_template, request, session
from flask_session import Session
from tempfile import mkdtemp
from werkzeug.security import check_password_hash, generate_password_hash
from functools import wraps
from datetime import datetime
from math import log10


# Setting up Flask and its configuration
app = Flask(__name__)

app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# This is a decorator function that you can apply to routes to require a user to be logged in.
def login_required(f):
    """
    Decorate routes to require login.

    http://flask.pocoo.org/docs/0.12/patterns/viewdecorators/
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get("user_id") is None:
            return redirect("/login")
        return f(*args, **kwargs)
    return decorated_function

# This function is called after each request to prevent responses from being cached.
@app.after_request
def after_request(response):
    """Ensure responses aren't cached"""
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response

# Adding the database
db = SQL("sqlite:///app.db")

# Creating database tables if they are not exists
db.execute('''CREATE TABLE IF NOT EXISTS users
              (id INTEGER PRIMARY KEY AUTOINCREMENT,
               username TEXT UNIQUE NOT NULL,
               hash TEXT NOT NULL)''')

db.execute('''CREATE TABLE IF NOT EXISTS calorie_intake (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    date TEXT,
    calorie_needs REAL,
    carbs REAL,
    protein REAL,
    fat REAL,
    weight_goal REAL,
    weight REAL
)''')

db.execute('''CREATE TABLE IF NOT EXISTS bodyfat (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    bodyfat REAL
)''')

db.execute('''CREATE TABLE IF NOT EXISTS trainings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    training TEXT,
    duration REAL,
    activity TEXT,
    breaks REAL,
    weight REAL,
    calories_burned REAL
)''')

# Making a history for the calculated calories
@app.route('/calories_history', methods=['GET'])
@login_required
def calories_history():
    rows = db.execute("SELECT * FROM calorie_intake WHERE user_id = ? ORDER BY date ASC", session["user_id"])
    return render_template("calorie_history.html", rows=rows)

# Making a history for the training calculations
@app.route('/training_results', methods=['GET'])
@login_required
def training_results():
    rows = db.execute("SELECT * FROM trainings WHERE user_id=?", session['user_id'])
    return render_template('training_results.html', rows=rows)

# Making a training slide where the user can calculate their burned calories
@app.route('/training_history', methods=['POST', 'GET'])
@login_required
def training_history():
    if request.method == "POST":
        training = request.form.get('training')
        duration = request.form.get('duration')
        activity = request.form.get('activity')
        breaks = request.form.get('breaks')
        weight = request.form.get('weight')

        if not training or not duration or not activity or not breaks or not weight: # Check if everything is filled
            flash("Fill out everything")
            return redirect('/training_history')

        if not duration.isdigit() or not breaks.isdigit() or not weight.isdigit(): # Check if the added fields are numbers
            flash("Give a number")
            return redirect('/training_history')

        # Calculating calories burned
        MET_values = {
            "low": 2.0,
            "medium": 4.0,
            "high": 8.0
        }
        MET = MET_values[activity] # Setting up a variable to the added activity

        calories_burned = MET * int(weight) * ((int(duration) / 60) - (int(breaks) / 60))  # duration needs to be in hours for this formula
        # Add the added values to the database
        db.execute("INSERT INTO trainings(user_id, training, duration, activity, breaks, calories_burned) VALUES (?, ?, ?, ?, ?, ?)", session['user_id'], training, duration, activity, breaks, calories_burned)

        return render_template("calorie_burned.html", calories_burned=calories_burned)

    else:
        return render_template("training_history.html")


# Make a site for the calculated bodyfats
@app.route('/bodyfat_history', methods=['GET'])
@login_required
def bodyfat_history():
    user_id = session['user_id']
    rows = db.execute("SELECT * FROM bodyfat WHERE user_id = ?", user_id)
    return render_template('bodyfat_history.html', rows=rows)


@app.route('/bodyfat', methods=['GET', 'POST'])
@login_required
def bodyfat():
    if request.method == 'POST':
        try:
            weight = float(request.form.get('weight'))
            waist = float(request.form.get('waist'))
            neck = float(request.form.get('neck'))
            height = float(request.form.get('height'))
        except ValueError:
            flash("Az összes számot lebegőpontos formátumban kell megadni.")

        gender = request.form.get('gender')

        if not weight or not waist or not neck or not height or not gender:
            flash("Fill out everything")
            return redirect("/bodyfat")

        # Calculate the bodyfat % for men
        if gender == 'male':
            bf = 495 / (1.0324 - 0.19077 * log10(waist - neck) + 0.15456 * log10(height)) - 450
        # Calculate the bodyfat % for women
        else:
            hip = float(request.form.get('hip'))
            bf = 495 / (1.29579 - 0.35004 * log10(waist + hip - neck) + 0.22100 * log10(height)) - 450

        db.execute("INSERT INTO bodyfat(user_id, bodyfat) VALUES (?, ?)", session['user_id'], bf)
        return render_template('bodyfat_result.html', bf=bf)
    return render_template('bodyfat_form.html')


@app.route('/')
@login_required
def index():
    return render_template('profile.html')


@app.route("/cal_calc", methods=["GET", "POST"])
@login_required
def cal_calc():
    if request.method == "POST":

        calorie_needs = 0

        gender = request.form.get("gender")
        weight = request.form.get("weight")
        height = request.form.get("height")
        age = request.form.get("age")
        activity = request.form.get("activity")

        if not gender or not weight or not height or not age or not activity:
            flash("Fill out everything")
            return redirect("/cal_calc")

        try:
            age = float(age)
            height = float(height)
            weight = float(weight)
        except ValueError:
            flash("Invalid age, height, or weight")
            return redirect("/cal_calc")

        if age <= 0 or height <= 0 or weight <= 0:
            flash("Age, height, and weight must be positive numbers")
            return redirect("/cal_calc")

        if gender == "male":
            if activity == "low":
                # Calculation of calorie requirements for men with low activity
                bmr = 10 * weight + 6.25 * height - 5 * age + 5
                calorie_needs = bmr * 1.2
            elif activity == "medium":
                # Calculation of calorie requirements for men with medium activity
                bmr = 10 * weight + 6.25 * height - 5 * age + 5
                calorie_needs = bmr * 1.55
            elif activity == "high":
                # Calculation of calorie requirements for men with high activity
                bmr = 10 * weight + 6.25 * height - 5 * age + 5
                calorie_needs = bmr * 1.9
        else:
            if activity == "low":
                # Calculation of calorie requirements for women with low activity
                bmr = 10 * weight + 6.25 * height - 5 * age - 161
                calorie_needs = bmr * 1.2
            elif activity == "medium":
                # Calculation of calorie requirements for women with medium activity
                bmr = 10 * weight + 6.25 * height - 5 * age - 161
                calorie_needs = bmr * 1.55
            elif activity == "high":
                # Calculation of calorie requirements for women with high activity
                bmr = 10 * weight + 6.25 * height - 5 * age - 161
                calorie_needs = bmr * 1.9

        # this field contains how much the user wants to gain or lose weight per week (in kg)
        weight_goal = request.form.get("weight_goal")


        try:
            weight_goal = float(weight_goal)
        except ValueError:
            flash("Invalid weight goal")
            return redirect("/cal_calc")

        # Calculate the calorie surplus or deficit based on the weight goal
        calorie_adjustment = weight_goal * 7700 / 7  # daily calorie requirement

        weight_goal += weight

        # If the user wants to lose weight, this is deducted from the daily calorie requirement
        # If you want to gain weight, then we add it
        calorie_needs += calorie_adjustment

        carbs = (calorie_needs/100)*55
        protein = (calorie_needs/100)*15
        fat = (calorie_needs/100)*30

        current_date = datetime.now().strftime('%Y-%m-%d')

        db.execute("INSERT INTO calorie_intake(user_id,weight,fat,carbs,protein,calorie_needs,weight_goal,date) VALUES (?, ?, ?, ?, ?, ?, ?, ?)", session['user_id'], weight, fat, carbs, protein, calorie_needs, weight_goal, current_date)
        return render_template("calorie_needs.html", calorie_needs=calorie_needs, carbs=carbs, protein=protein, fat=fat)
    else:
        return render_template("cal_calc.html")

@app.route('/change_password', methods=['POST','GET'])
@login_required
def change_password():
    if request.method == 'POST':
        username = request.form.get('username')
        current_password = request.form.get('current_password')
        new_password = request.form.get('new_password')
        confirmation = request.form.get('confirmation')

        if not username or not current_password or not new_password or not confirmation:
            flash("Fill out everything")
            return redirect("/change_password")

        # check if new_password and confirmation matches
        if new_password != confirmation:
            flash("New password and its confirmation must be the same!")
            return redirect("/change_password")

        # check if new_password contains at least one capital letter, symbol, and number
        if not re.search(r'[A-Z]', new_password) or not re.search(r'[!@#$%^&*(),.?":{}|<>]', new_password) or not re.search(r'\d', new_password):
            flash("Your new password must contain at least 1 capital letter, 1 symbol, and 1 number!")
            return redirect("/change_password")

        # Query user from database
        user = db.execute("SELECT * FROM users WHERE username = ?", username)

        # Check if current password matches with the one in the database
        if not check_password_hash(user[0]['hash'], current_password) or len(user) != 1:
            flash("Current password is incorrect!")
            return redirect("/change_password")

        new_hash = generate_password_hash(new_password)
        db.execute(
            "UPDATE users SET hash = ? WHERE username = ?", new_hash, username)
        flash("Password changed successfully")
        return redirect("/")
    else:
        return render_template('change_password.html')

@app.route('/register', methods=["GET","POST"])
def register():
    if request.method == "POST":

        username = request.form.get("username")
        password = request.form.get("password")
        confirmation = request.form.get("confirmation")

        """Check if the password and the confirmation matches"""
        if password != confirmation:
            flash("Passwords are not the same!")
            return redirect("/register")

        """Check if everything is filled"""
        if not password or not confirmation or not username:
            flash("Fill out everything")
            return redirect("/register")

        """Check if username exists"""
        rows = db.execute("SELECT * FROM users WHERE username=?", username)
        if len(rows) != 0:
            flash("Username already exists")
            return redirect("/register")

        """Check if password contains at least one capital letter, symbol, and number"""
        if not re.search(r'[A-Z]', password) or not re.search(r'[!@#$%^&*(),.?":{}|<>]', password) or not re.search(r'\d', password):
            flash("Your password must contain at least 1 capital letter, 1 symbol and 1 number!")
            return redirect("/register")

        """Add informations to the database"""
        """If all checks pass, hash the password and insert the new user into the db"""
        hash = generate_password_hash(password)
        db.execute(
            "INSERT INTO users (username, hash) VALUES (?, ?)", username, hash)
        flash("Registered successfully")
        return render_template("login.html")

    else:
        return render_template("/register.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""

    # Forget any user_id
    session.clear()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Ensure username was submitted
        if not request.form.get("username"):
            flash("must provide username")
            return redirect("/login")

        # Ensure password was submitted
        elif not request.form.get("password"):
            flash("must provide password")
            return redirect("/login")

        # Query database for username
        rows = db.execute("SELECT * FROM users WHERE username = ?",
                          request.form.get("username"))

        # Ensure username exists and password is correct
        if len(rows) != 1 or not check_password_hash(rows[0]["hash"], request.form.get("password")):
            flash("invalid username and/or password")
            return redirect("/login")

        # Remember which user has logged in
        session["user_id"] = rows[0]["id"]

        # Redirect user to home page
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html")




if __name__ == '__main__':
    app.run()