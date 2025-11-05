from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import os

app = Flask(__name__, static_folder='static')
app.config['SECRET_KEY'] = 'healthcare-messenger-secret-key'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///healthcare_messenger.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# Модели базы данных
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(120), nullable=False)
    department = db.Column(db.String(100), nullable=False)
    position = db.Column(db.String(100), nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    sent_messages = db.relationship('Message', foreign_keys='Message.sender_id', backref='sender')
    received_messages = db.relationship('Message', foreign_keys='Message.recipient_id', backref='recipient')

class Message(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    sender_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    recipient_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    content = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    is_read = db.Column(db.Boolean, default=False)
    priority = db.Column(db.String(20), default='normal')  # normal, urgent, emergency

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Маршруты
@app.route('/')
def index():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()
        
        if user and check_password_hash(user.password_hash, password):
            login_user(user)
            return redirect(url_for('dashboard'))
        flash('Неверные учетные данные')
    
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        department = request.form['department']
        position = request.form['position']
        
        if User.query.filter_by(username=username).first():
            flash('Пользователь уже существует')
            return render_template('register.html')
        
        user = User(
            username=username,
            email=email,
            password_hash=generate_password_hash(password),
            department=department,
            position=position
        )
        db.session.add(user)
        db.session.commit()
        
        login_user(user)
        return redirect(url_for('dashboard'))
    
    return render_template('register.html')

@app.route('/dashboard')
@login_required
def dashboard():
    recent_messages = Message.query.filter_by(recipient_id=current_user.id)\
                                 .order_by(Message.timestamp.desc())\
                                 .limit(10).all()
    unread_count = Message.query.filter_by(recipient_id=current_user.id, is_read=False).count()
    return render_template('dashboard.html', messages=recent_messages, unread_count=unread_count)

@app.route('/send_message', methods=['GET', 'POST'])
@login_required
def send_message():
    if request.method == 'POST':
        recipient_username = request.form['recipient']
        content = request.form['content']
        priority = request.form.get('priority', 'normal')
        
        recipient = User.query.filter_by(username=recipient_username).first()
        if not recipient:
            flash('Получатель не найден')
            return render_template('send_message.html')
        
        message = Message(
            sender_id=current_user.id,
            recipient_id=recipient.id,
            content=content,
            priority=priority
        )
        db.session.add(message)
        db.session.commit()
        
        flash('Сообщение отправлено')
        return redirect(url_for('dashboard'))
    
    users = User.query.filter(User.id != current_user.id).all()
    return render_template('send_message.html', users=users)

@app.route('/messages')
@login_required
def messages():
    page = request.args.get('page', 1, type=int)
    messages = Message.query.filter_by(recipient_id=current_user.id)\
                           .order_by(Message.timestamp.desc())\
                           .paginate(page=page, per_page=20, error_out=False)
    return render_template('messages.html', messages=messages)

@app.route('/mark_read/<int:message_id>')
@login_required
def mark_read(message_id):
    message = Message.query.get_or_404(message_id)
    if message.recipient_id == current_user.id:
        message.is_read = True
        db.session.commit()
    return redirect(url_for('messages'))

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)