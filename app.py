from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash

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

class Expense(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, nullable=False)
    amount = db.Column(db.Float, nullable=False)
    category = db.Column(db.String(50), nullable=False)
    date = db.Column(db.String(20), nullable=False)
    description = db.Column(db.String(200))

with app.app_context():
    db.create_all()

@app.route('/')
def home():
    return render_template('home.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            flash('Email already registered. Please login.', 'danger')
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
            flash('Login successful!', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid email or password.', 'danger')
    return render_template('login.html')

@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    expenses = Expense.query.filter_by(user_id=session['user_id']).all()
    total = round(sum(e.amount for e in expenses), 2)
    count = len(expenses)

    category_data = {}
    for e in expenses:
        category_data[e.category] = category_data.get(e.category, 0) + e.amount

    categories = list(category_data.keys())
    amounts = [round(v, 2) for v in category_data.values()]

    recent = Expense.query.filter_by(user_id=session['user_id']).order_by(Expense.date.desc()).limit(5).all()

    return render_template('dashboard.html',
        total=total,
        count=count,
        categories=categories,
        amounts=amounts,
        recent=recent
    )

@app.route('/logout')
def logout():
    session.clear()
    flash('Logged out successfully.', 'success')
    return redirect(url_for('login'))

@app.route('/add-expense', methods=['GET', 'POST'])
def add_expense():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    if request.method == 'POST':
        amount = request.form['amount']
        category = request.form['category']
        date = request.form['date']
        description = request.form['description']
        new_expense = Expense(
            user_id=session['user_id'],
            amount=float(amount),
            category=category,
            date=date,
            description=description
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
    expenses = Expense.query.filter_by(user_id=session['user_id']).order_by(Expense.date.desc()).all()
    total = sum(e.amount for e in expenses)
    total = round(total, 2)
    return render_template('expenses.html', expenses=expenses, total=total)

@app.route('/delete-expense/<int:expense_id>')
def delete_expense(expense_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    expense = Expense.query.get_or_404(expense_id)
    if expense.user_id != session['user_id']:
        flash('Unauthorized action.', 'danger')
        return redirect(url_for('view_expenses'))
    db.session.delete(expense)
    db.session.commit()
    flash('Expense deleted.', 'success')
    return redirect(url_for('view_expenses'))
@app.route('/edit-expense/<int:expense_id>', methods=['GET', 'POST'])
def edit_expense(expense_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))

    expense = Expense.query.get_or_404(expense_id)

    if expense.user_id != session['user_id']:
        flash('Unauthorized action.', 'danger')
        return redirect(url_for('view_expenses'))

    if request.method == 'POST':
        expense.amount = float(request.form['amount'])
        expense.category = request.form['category']
        expense.date = request.form['date']
        expense.description = request.form['description']
        db.session.commit()
        flash('Expense updated successfully!', 'success')
        return redirect(url_for('view_expenses'))

    return render_template('edit_expense.html', expense=expense)

if __name__ == '__main__':
    app.run(debug=True)