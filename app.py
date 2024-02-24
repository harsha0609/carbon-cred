from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your_secret_key'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///carbon_footprint.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'


class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password = db.Column(db.String(100), nullable=False)
    carbon_footprints = db.relationship('CarbonFootprint', backref='user', lazy=True)


class CarbonFootprint(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    electricity = db.Column(db.Float, nullable=False)
    transportation = db.Column(db.String(20), nullable=False)
    miles = db.Column(db.Float)
    carbon_footprint = db.Column(db.Float, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

class FoodDonation(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    food_description = db.Column(db.String(200), nullable=False)
    donor_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    donor = db.relationship('User', backref='donations', lazy=True)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


@app.route('/')
def index():
    return render_template('index.html', user=current_user)


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()
        if user and user.password == password:
            login_user(user)
            flash('Login successful!', 'success')
            return redirect(url_for('index'))
        else:
            flash('Login failed. Please check your username and password.', 'danger')
    return render_template('login.html')


@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Logout successful!', 'success')
    return redirect(url_for('index'))


@app.route('/calculate', methods=['POST'])
@login_required
def calculate():
    electricity = float(request.form['electricity'])
    transportation = request.form['transportation']

    # Sample carbon emission factors (in kg CO2 per unit)
    electricity_factor = 0.4  # kg CO2 per kWh
    transportation_factors = {
        'car': 2.0,  # kg CO2 per mile
        'bus': 0.5,
        'bike': 0.0,
        # Add more transportation methods as needed
    }

    carbon_footprint = electricity * electricity_factor

    if transportation in transportation_factors:
        miles = float(request.form['miles'])
        carbon_footprint += miles * transportation_factors[transportation]

    with app.app_context():
        new_entry = CarbonFootprint(
            electricity=electricity,
            transportation=transportation,
            miles=miles,
            carbon_footprint=carbon_footprint,
            user=current_user
        )

        db.session.add(new_entry)
        db.session.commit()

    flash('Carbon footprint calculated and saved successfully!', 'success')
    return redirect(url_for('result'))



# Donate Food Page (requires login)
@app.route('/donate', methods=['GET', 'POST'])
@login_required
def donate():
    if request.method == 'POST':
        food_description = request.form['food_description']

        with app.app_context():
            new_donation = FoodDonation(food_description=food_description, donor=current_user)
            db.session.add(new_donation)
            db.session.commit()

        flash('Food donation added successfully!', 'success')
        return redirect(url_for('dashboard'))

    return render_template('donate.html')

@app.route('/result')
@login_required
def result():
    # You can add additional information or processing related to the result page
    return render_template('result.html')

@app.route('/history')
@login_required
def history():
    with app.app_context():
        carbon_entries = CarbonFootprint.query.filter_by(user=current_user).all()

    return render_template('history.html', entries=carbon_entries)

# Dashboard (requires login)
@app.route('/dashboard')
@login_required
def dashboard():
    carbon_footprints = CarbonFootprint.query.filter_by(user=current_user).all()
    donations = FoodDonation.query.filter_by(donor=current_user).all()
    total_carbon_footprint = sum([entry.carbon_footprint for entry in carbon_footprints])
    return render_template('dashboard.html', carbon_footprints=carbon_footprints, donations=donations, total_carbon_footprint=total_carbon_footprint)


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        confirm_password = request.form['confirm_password']

        if password == confirm_password:
            with app.app_context():
                new_user = User(username=username, password=password)
                db.session.add(new_user)
                db.session.commit()

            flash('Registration successful! You can now log in.', 'success')
            return redirect(url_for('login'))
        else:
            flash('Password and confirm password do not match. Please try again.', 'danger')

    return render_template('register.html')


if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)
