from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, date
import csv
import io
from flask import Response

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///expense_manager.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = 'arpit123secretkey'

db = SQLAlchemy(app)

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    monthly_budget = db.Column(db.Float, default=0)

class Expense(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, nullable=False)
    amount = db.Column(db.Float, nullable=False)
    category = db.Column(db.String(50), nullable=False)
    date = db.Column(db.String(20), nullable=False)
    description = db.Column(db.String(200))

class Income(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, nullable=False)
    amount = db.Column(db.Float, nullable=False)
    source = db.Column(db.String(100), nullable=False)
    date = db.Column(db.String(20), nullable=False)
    description = db.Column(db.String(200))

with app.app_context():
    db.create_all()

@app.route('/')
def home():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    return render_template('home.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            flash('Email already registered.', 'danger')
            return redirect(url_for('register'))
        hashed_password = generate_password_hash(password)
        new_user = User(username=username, email=email, password=hashed_password)
        db.session.add(new_user)
        db.session.commit()
        flash('Registration successful! Please login.', 'success')
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        user = User.query.filter_by(email=email).first()
        if user and check_password_hash(user.password, password):
            session['user_id'] = user.id
            session['username'] = user.username
            session['email'] = user.email
            flash('Login successful!', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid email or password.', 'danger')
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    user = User.query.get(session['user_id'])
    if user is None:
        session.clear()
        flash('Session expired. Please login again.', 'warning')
        return redirect(url_for('login'))
    today = date.today()
    current_month = today.strftime('%Y-%m')

    all_expenses = Expense.query.filter_by(user_id=session['user_id']).all()
    all_incomes = Income.query.filter_by(user_id=session['user_id']).all()

    month_expenses = [e for e in all_expenses if e.date.startswith(current_month)]
    month_incomes = [i for i in all_incomes if i.date.startswith(current_month)]

    total_expense = round(sum(e.amount for e in all_expenses), 2)
    total_income = round(sum(i.amount for i in all_incomes), 2)
    month_expense = round(sum(e.amount for e in month_expenses), 2)
    month_income = round(sum(i.amount for i in month_incomes), 2)
    savings = round(total_income - total_expense, 2)
    budget = user.monthly_budget or 0
    budget_left = round(budget - month_expense, 2) if budget > 0 else 0
    savings_rate = round((savings / total_income * 100), 1) if total_income > 0 else 0

    category_data = {}
    for e in month_expenses:
        category_data[e.category] = category_data.get(e.category, 0) + e.amount
    categories = list(category_data.keys())
    amounts = [round(v, 2) for v in category_data.values()]

    monthly_data = {}
    for e in all_expenses:
        month = e.date[:7]
        monthly_data[month] = monthly_data.get(month, 0) + e.amount
    sorted_months = sorted(monthly_data.keys())[-6:]
    monthly_labels = sorted_months
    monthly_amounts = [round(monthly_data[m], 2) for m in sorted_months]

    recent_expenses = Expense.query.filter_by(user_id=session['user_id']).order_by(Expense.date.desc()).limit(5).all()
    recent_incomes = Income.query.filter_by(user_id=session['user_id']).order_by(Income.date.desc()).limit(5).all()

    return render_template('dashboard.html',
        total_expense=total_expense,
        total_income=total_income,
        month_expense=month_expense,
        month_income=month_income,
        savings=savings,
        savings_rate=savings_rate,
        budget=budget,
        budget_left=budget_left,
        categories=categories,
        amounts=amounts,
        monthly_labels=monthly_labels,
        monthly_amounts=monthly_amounts,
        recent_expenses=recent_expenses,
        recent_incomes=recent_incomes,
        count=len(all_expenses)
    )

@app.route('/add-expense', methods=['GET', 'POST'])
def add_expense():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    if request.method == 'POST':
        new_expense = Expense(
            user_id=session['user_id'],
            amount=float(request.form['amount']),
            category=request.form['category'],
            date=request.form['date'],
            description=request.form['description']
        )
        db.session.add(new_expense)
        db.session.commit()
        flash('Expense added successfully!', 'success')
        return redirect(url_for('view_expenses'))
    return render_template('add_expense.html')

@app.route('/expenses')
def view_expenses():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    search = request.args.get('search', '')
    category_filter = request.args.get('category', '')
    query = Expense.query.filter_by(user_id=session['user_id'])
    if search:
        query = query.filter(Expense.description.contains(search))
    if category_filter:
        query = query.filter_by(category=category_filter)
    expenses = query.order_by(Expense.date.desc()).all()
    total = round(sum(e.amount for e in expenses), 2)
    return render_template('expenses.html', expenses=expenses, total=total, search=search, category_filter=category_filter)

@app.route('/edit-expense/<int:expense_id>', methods=['GET', 'POST'])
def edit_expense(expense_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    expense = Expense.query.get_or_404(expense_id)
    if request.method == 'POST':
        expense.amount = float(request.form['amount'])
        expense.category = request.form['category']
        expense.date = request.form['date']
        expense.description = request.form['description']
        db.session.commit()
        flash('Expense updated!', 'success')
        return redirect(url_for('view_expenses'))
    return render_template('edit_expense.html', expense=expense)

@app.route('/delete-expense/<int:expense_id>')
def delete_expense(expense_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    expense = Expense.query.get_or_404(expense_id)
    db.session.delete(expense)
    db.session.commit()
    flash('Expense deleted.', 'success')
    return redirect(url_for('view_expenses'))

@app.route('/income')
def view_income():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    incomes = Income.query.filter_by(user_id=session['user_id']).order_by(Income.date.desc()).all()
    total = round(sum(i.amount for i in incomes), 2)
    return render_template('income.html', incomes=incomes, total=total)

@app.route('/add-income', methods=['GET', 'POST'])
def add_income():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    if request.method == 'POST':
        new_income = Income(
            user_id=session['user_id'],
            amount=float(request.form['amount']),
            source=request.form['source'],
            date=request.form['date'],
            description=request.form['description']
        )
        db.session.add(new_income)
        db.session.commit()
        flash('Income added successfully!', 'success')
        return redirect(url_for('view_income'))
    return render_template('add_income.html')

@app.route('/delete-income/<int:income_id>')
def delete_income(income_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    income = Income.query.get_or_404(income_id)
    db.session.delete(income)
    db.session.commit()
    flash('Income deleted.', 'success')
    return redirect(url_for('view_income'))

@app.route('/profile', methods=['GET', 'POST'])
def profile():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    user = User.query.get(session['user_id'])
    if request.method == 'POST':
        user.monthly_budget = float(request.form['budget'] or 0)
        db.session.commit()
        flash('Budget updated successfully!', 'success')
    return render_template('profile.html', user=user)

@app.route('/export-csv')
def export_csv():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    expenses = Expense.query.filter_by(user_id=session['user_id']).all()
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['Date', 'Category', 'Description', 'Amount'])
    for e in expenses:
        writer.writerow([e.date, e.category, e.description or '', e.amount])
    output.seek(0)
    return Response(output, mimetype='text/csv',
        headers={'Content-Disposition': 'attachment;filename=expenses.csv'})

if __name__ == '__main__':
    app.run(debug=True)