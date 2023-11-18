from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import func, desc, distinct
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
from sqlalchemy.orm import relationship  # Add this import

db = SQLAlchemy()

def create_app():
    app = Flask(__name__)
    app.config['SECRET_KEY'] = 'your_secret_key'
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///users.db'
    db.init_app(app)
    return app

app = create_app()

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password = db.Column(db.String(100), nullable=False)

class Employee(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(100), nullable=False)
    employee_id = db.Column(db.String(20), unique=True, nullable=False)
    position = db.Column(db.String(50))
    department = db.Column(db.String(50))
    email = db.Column(db.String(50), unique=True, nullable=False)

    # Add a relationship to the DailyAttendance model
    daily_attendances = relationship('DailyAttendance', backref='employee')

class DailyAttendance(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.Date, nullable=False, default=datetime.utcnow)
    employee_id = db.Column(db.Integer, db.ForeignKey('employee.id'), nullable=False)

class Salary(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.Date, nullable=False, default=datetime.utcnow)
    employee_id = db.Column(db.Integer, db.ForeignKey('employee.id'), nullable=False)
    cumulative_amount = db.Column(db.Float, nullable=False, default=0.0)

    # Add a relationship to the Employee model
    employee = relationship('Employee', backref='salaries')

@app.route('/')
def home():
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        user = User.query.filter_by(username=username).first()

        if user and check_password_hash(user.password, password):
            session['user_id'] = user.id
            return redirect(url_for('dashboard'))

    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        hashed_password = generate_password_hash(password, method='pbkdf2:sha256')

        new_user = User(username=username, password=hashed_password)
        db.session.add(new_user)
        db.session.commit()

        return redirect(url_for('login'))

    return render_template('register.html')

@app.route('/dashboard')
def dashboard():
    if 'user_id' in session:
        user = User.query.filter_by(id=session['user_id']).first()
        return render_template('dashboard.html', username=user.username)

    return redirect(url_for('login'))

@app.route('/logout')
def logout():
    session.pop('user_id', None)
    return redirect(url_for('home'))

@app.route('/employee')
def employee_management():
    employees = Employee.query.all()
    return render_template('employee_management.html', employees=employees)

@app.route('/add_employee', methods=['GET', 'POST'])
def add_employee():
    if request.method == 'POST':
        full_name = request.form['full_name']
        employee_id = request.form['employee_id']
        position = request.form['position']
        department = request.form['department']
        email = request.form['email']

        new_employee = Employee(
            full_name=full_name,
            employee_id=employee_id,
            position=position,
            department=department,
            email=email
        )

        db.session.add(new_employee)
        db.session.commit()

        return redirect(url_for('employee_management'))

    return render_template('add_employee.html')

@app.route('/edit_employee/<int:id>', methods=['GET', 'POST'])
def edit_employee(id):
    employee = Employee.query.get(id)

    if request.method == 'POST':
        employee.full_name = request.form['full_name']
        employee.employee_id = request.form['employee_id']
        employee.position = request.form['position']
        employee.department = request.form['department']
        employee.email = request.form['email']

        db.session.commit()

        return redirect(url_for('employee_management'))

    return render_template('edit_employee.html', employee=employee)

@app.route('/delete_employee/<int:id>', methods=['GET', 'POST'])
def delete_employee(id):
    employee = Employee.query.get(id)
    
    if request.method == 'POST':
        db.session.delete(employee)
        db.session.commit()
        return redirect(url_for('employee_management'))

    return render_template('delete_employee.html', employee=employee)

@app.route('/attendance', methods=['GET', 'POST'])
def attendance():
    employee = None
    attendance_records = []

    if request.method == 'POST':
        employee_id = request.form['employee_id']
        employee = Employee.query.filter_by(employee_id=employee_id).first()

        if employee:
            try:
                current_date = datetime.utcnow().date()

                existing_attendance = DailyAttendance.query.filter_by(
                    employee_id=employee.id, date=current_date
                ).first()

                if not existing_attendance:
                    new_attendance = DailyAttendance(employee_id=employee.id, date=current_date)
                    db.session.add(new_attendance)
                    db.session.commit()

                    flash('Attendance marked for today.')
                else:
                    flash('Attendance already marked for today.')

            except Exception as e:
                flash(f'Error marking attendance: {str(e)}', 'error')

    if employee:
        # Use SQLalchemy func.max to get the latest date and func.count to get the attendance count
        attendance_records = db.session.query(
            DailyAttendance.employee_id,
            func.max(DailyAttendance.date).label('latest_date'),
            func.count(DailyAttendance.id).label('attendance_count')
        ).filter(DailyAttendance.employee_id == employee.id).group_by(DailyAttendance.employee_id).all()

    return render_template('attendance.html', employee=employee, attendance_records=attendance_records)

@app.route('/salary', methods=['GET', 'POST'])
def salary():
    daily_salary = 20.0  # Set your actual daily salary here

    if request.method == 'POST':
        employee_id = request.form['employee_id']
        employee = Employee.query.filter_by(employee_id=employee_id).first()

        if employee:
            try:
                # Get the count of distinct dates for the employee
                new_daily_attendance_count = db.session.query(
                    func.count(distinct(DailyAttendance.date))
                ).filter(
                    DailyAttendance.employee_id == employee.id
                ).scalar()

                # Calculate the daily salary amount only if there are new attendance records
                if new_daily_attendance_count > 0:
                    # Calculate the daily salary amount
                    daily_amount = daily_salary * new_daily_attendance_count

                    # Update the cumulative salary amount in the Salary table
                    existing_salary = Salary.query.filter_by(employee_id=employee.id).order_by(Salary.date.desc()).first()

                    if existing_salary:
                        # Update the existing salary entry if it already exists
                        existing_salary.cumulative_amount += daily_amount
                    else:
                        # Create a new salary entry if it doesn't exist
                        new_salary = Salary(employee_id=employee.id, cumulative_amount=daily_amount)
                        db.session.add(new_salary)

                    db.session.commit()
                    flash('Salary calculated and updated.', 'success')
                else:
                    flash('No new attendance records to calculate salary.', 'info')
            except Exception as e:
                flash(f'Error calculating salary: {str(e)}', 'error')

    # Calculate total_salary as daily_salary * total_attendance
    salary_report = db.session.query(
        Employee, func.sum(Salary.cumulative_amount), func.count(distinct(DailyAttendance.date))
    ).join(
        Salary, Employee.id == Salary.employee_id
    ).join(
        DailyAttendance, Employee.id == DailyAttendance.employee_id
    ).group_by(
        Employee.id
    ).all()

    return render_template('salary.html', salary_report=salary_report, daily_salary=daily_salary)
@app.route('/statistics')
def statistics():
    attendance_records = DailyAttendance.query.all()
    salary_report = Salary.query.all()

    return render_template('statistics.html', attendance_records=attendance_records, salary_report=salary_report)

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)