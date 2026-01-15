from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from datetime import datetime
import os
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-change-this-in-prod' # Change this!
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///aluminium.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'admin_login'

# --- Models ---
class Admin(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class Category(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    products = db.relationship('Product', backref='category', lazy=True)

class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=True)
    image_url = db.Column(db.String(200), nullable=True)
    price_per_sqft = db.Column(db.Float, nullable=False)
    category_id = db.Column(db.Integer, db.ForeignKey('category.id'), nullable=False)

class LaborCost(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    rate_per_sqft = db.Column(db.Float, default=0.0)

class Invoice(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    customer_name = db.Column(db.String(100), nullable=False)
    customer_phone = db.Column(db.String(20), nullable=False)
    customer_address = db.Column(db.Text, nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=False)
    product_name = db.Column(db.String(100)) # Store snapshot of name
    height_ft = db.Column(db.Float, nullable=False)
    width_ft = db.Column(db.Float, nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    sqft_price_at_booking = db.Column(db.Float, nullable=False) # Snapshot of price
    total_amount = db.Column(db.Float, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    product = db.relationship('Product')


@login_manager.user_loader
def load_user(user_id):
    return Admin.query.get(int(user_id))

# --- Database Initialization ---
def init_database():
    """Initialize database tables and create default admin if needed."""
    with app.app_context():
        db.create_all()
        # Create default admin if not exists
        if not Admin.query.filter_by(username='admin').first():
            print("Creating default admin...")
            admin = Admin(username='admin')
            admin.set_password('admin123')
            db.session.add(admin)
            # Initialize Labor Cost if not exists
            if not LaborCost.query.first():
                db.session.add(LaborCost(rate_per_sqft=50.0))
            db.session.commit()
            print("Database initialized successfully.")

# Initialize database on startup
init_database()

# --- CLI Commands ---
@app.cli.command("create-admin")
def create_admin():
    """Creates the admin user."""
    db.create_all()
    if not Admin.query.filter_by(username='admin').first():
        admin = Admin(username='admin')
        admin.set_password('admin123')
        db.session.add(admin)
        
        # Initialize Labor Cost if not exists
        if not LaborCost.query.first():
            db.session.add(LaborCost(rate_per_sqft=50.0))
            
        db.session.commit()
        print("Admin user created.")
    else:
        print("Admin already exists.")

@app.cli.command("init-db")
def init_db_command():
    """Clear existing data and create new tables."""
    db.create_all()
    print("Initialized the database.")

# --- Routes ---

# Public Routes
@app.route('/')
def home():
    categories = Category.query.all()
    # Fetch some featured products or all products
    products = Product.query.all()
    return render_template('index.html', categories=categories, products=products)

@app.route('/product/<int:product_id>')
def product_detail(product_id):
    product = Product.query.get_or_404(product_id)
    labor_cost = LaborCost.query.first()
    labor_rate = labor_cost.rate_per_sqft if labor_cost else 0
    return render_template('product.html', product=product, labor_rate=labor_rate)

# Admin Routes
@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if current_user.is_authenticated:
        return redirect(url_for('admin_dashboard'))
    
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        admin = Admin.query.filter_by(username=username).first()
        
        if admin and admin.check_password(password):
            login_user(admin)
            return redirect(url_for('admin_dashboard'))
        else:
            flash('Invalid username or password')
            
    return render_template('admin/login.html')

@app.route('/admin/logout')
@login_required
def admin_logout():
    logout_user()
    return redirect(url_for('admin_login'))

@app.route('/admin')
@login_required
def admin_dashboard():
    categories = Category.query.all()
    products = Product.query.all()
    labor_cost = LaborCost.query.first()
    invoices = Invoice.query.order_by(Invoice.created_at.desc()).all()
    return render_template('admin/dashboard.html', 
                         categories=categories, 
                         products=products, 
                         labor_cost=labor_cost,
                         invoices=invoices)

# Admin API / Actions (Simplified for MVP) - ideally use REST API or separate routes
@app.route('/admin/category/add', methods=['POST'])
@login_required
def add_category():
    name = request.form.get('name')
    if name:
        db.session.add(Category(name=name))
        db.session.commit()
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/product/add', methods=['POST'])
@login_required
def add_product():
    name = request.form.get('name')
    price = float(request.form.get('price'))
    category_id = int(request.form.get('category_id'))
    description = request.form.get('description')
    image_url = request.form.get('image_url') # For now, just a URL string
    
    product = Product(name=name, price_per_sqft=price, category_id=category_id, 
                      description=description, image_url=image_url)
    db.session.add(product)
    db.session.commit()
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/labor/update', methods=['POST'])
@login_required
def update_labor():
    rate = float(request.form.get('rate'))
    labor = LaborCost.query.first()
    if not labor:
        labor = LaborCost(rate_per_sqft=rate)
        db.session.add(labor)
    else:
        labor.rate_per_sqft = rate
    db.session.commit()
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/invoice/create', methods=['POST'])
@login_required
def create_invoice():
    try:
        product_id = int(request.form.get('product_id'))
        customer_name = request.form.get('customer_name')
        customer_phone = request.form.get('customer_phone')
        customer_address = request.form.get('customer_address')
        height = float(request.form.get('height'))
        width = float(request.form.get('width'))
        quantity = int(request.form.get('quantity'))
        
        product = Product.query.get(product_id)
        if not product:
            flash("Product not found")
            return redirect(url_for('admin_dashboard'))

        # Calculate total
        sqft = height * width
        total = sqft * product.price_per_sqft * quantity
        
        invoice = Invoice(
            customer_name=customer_name,
            customer_phone=customer_phone,
            customer_address=customer_address,
            product_id=product_id,
            product_name=product.name,
            height_ft=height,
            width_ft=width,
            quantity=quantity,
            sqft_price_at_booking=product.price_per_sqft,
            total_amount=total
        )
        db.session.add(invoice)
        db.session.commit()
        
        return redirect(url_for('view_invoice', invoice_id=invoice.id))
    except Exception as e:
        flash(str(e))
        return redirect(url_for('admin_dashboard'))

@app.route('/admin/invoice/<int:invoice_id>')
@login_required
def view_invoice(invoice_id):
    invoice = Invoice.query.get_or_404(invoice_id)
    return render_template('admin/invoice_view.html', invoice=invoice, now=datetime.utcnow())

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        # Create default admin if not exists (for dev convenience)
        if not Admin.query.filter_by(username='admin').first():
            print("Creating default admin...")
            admin = Admin(username='admin')
            admin.set_password('admin123')
            db.session.add(admin)
            if not LaborCost.query.first():
                 db.session.add(LaborCost(rate_per_sqft=50.0))
            db.session.commit()
            
    app.run(debug=True)
