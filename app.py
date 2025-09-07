from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps

app = Flask(__name__)
app.secret_key = 'supersecretkey'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///canteen.db'
db = SQLAlchemy(app)

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(120), nullable=False)
    role = db.Column(db.String(10), nullable=False, default='user')

class Order(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user = db.Column(db.String(80), db.ForeignKey('user.username'))
    total = db.Column(db.Integer)
    items = db.relationship('OrderItem', backref='order', cascade="all,delete", lazy=True)

class OrderItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('order.id'))
    name = db.Column(db.String(80))
    qty = db.Column(db.Integer)
    price = db.Column(db.Integer)

MENU = [
    {"id": 1, "name": "Veg Sandwich", "price": 30},
    {"id": 2, "name": "Chicken Burger", "price": 50},
    {"id": 3, "name": "Coffee", "price": 20},
    {"id": 4, "name": "Tea", "price": 15},
    {"id": 5, "name": "French Fries", "price": 25},
    {"id": 6, "name": "Paneer Roll", "price": 40},
    {"id": 7, "name": "Egg Puff", "price": 18},
    {"id": 8, "name": "Masala Dosa", "price": 35},
    {"id": 9, "name": "Veg Noodles", "price": 45},
    {"id": 10, "name": "Samosa", "price": 12},
    {"id": 11, "name": "Cold Drink", "price": 25},
    {"id": 12, "name": "Chocolate Cake", "price": 30},
    {"id": 13, "name": "Pasta", "price": 55},
    {"id": 14, "name": "Spring Roll", "price": 30},
    {"id": 15, "name": "Idli Sambar", "price": 28}
]

def login_required(role=None):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if 'username' not in session:
                flash('You need to login first.')
                return redirect(url_for('login'))
            if role:
                user = User.query.filter_by(username=session['username']).first()
                if not user or user.role != role:
                    flash('Access denied.')
                    return redirect(url_for('index'))
            return f(*args, **kwargs)
        return decorated_function
    return decorator

@app.before_first_request
def create_tables():
    db.create_all()
    # Create default admin if not exists
    if not User.query.filter_by(username='admin').first():
        admin = User(username='admin', password_hash=generate_password_hash('adminpass'), role='admin')
        db.session.add(admin)
        db.session.commit()

@app.route("/")
@login_required()
def index():
    return render_template("index.html", menu=MENU, username=session['username'])

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form['username']
        password = request.form['password']
        if User.query.filter_by(username=username).first():
            flash("Username already exists.")
            return redirect(url_for('register'))
        user = User(username=username, password_hash=generate_password_hash(password), role='user')
        db.session.add(user)
        db.session.commit()
        flash("Registration successful. Please login.")
        return redirect(url_for('login'))
    return render_template("register.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password_hash, password):
            session['username'] = username
            return redirect(url_for('index'))
        else:
            flash('Invalid credentials')
    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route("/order", methods=["POST"])
@login_required()
def order():
    items = []
    total = 0
    for item in MENU:
        qty = int(request.form.get(f'qty_{item["id"]}', 0))
        if qty > 0:
            items.append({
                "name": item["name"],
                "qty": qty,
                "price": item["price"]
            })
            total += item["price"] * qty
    if items:
        order = Order(user=session['username'], total=total)
        db.session.add(order)
        db.session.commit()
        for i in items:
            order_item = OrderItem(order_id=order.id, name=i['name'], qty=i['qty'], price=i['price'])
            db.session.add(order_item)
        db.session.commit()
        return render_template("order_success.html", items=items, total=total, username=session['username'])
    else:
        flash('Please select at least one item.')
        return redirect(url_for('index'))

@app.route("/admin/orders")
@login_required(role='admin')
def admin_orders():
    orders = Order.query.order_by(Order.id.desc()).all()
    return render_template("admin_orders.html", orders=orders)

@app.route("/myorders")
@login_required()
def my_orders():
    orders = Order.query.filter_by(user=session['username']).order_by(Order.id.desc()).all()
    return render_template("my_orders.html", orders=orders, username=session['username'])

if __name__ == "__main__":
    app.run(debug=True)