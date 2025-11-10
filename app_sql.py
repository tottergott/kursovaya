from flask import Flask, render_template, request, redirect, url_for, flash, send_from_directory, jsonify
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from datetime import datetime
import sqlite3
import os

app = Flask(__name__, static_folder='static')
app.config['SECRET_KEY'] = 'healthcare-messenger-secret-key'
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

DATABASE = 'healthcare_new.db'

class User(UserMixin):
    def __init__(self, id, username, email, password_hash, department_id, position, is_active, created_at, department_name=None):
        self.id = id
        self.username = username
        self.email = email
        self.password_hash = password_hash
        self.department_id = department_id
        self.position = position
        # self.is_active = is_active
        self.created_at = created_at
        self.department = department_name

def init_db():
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS departments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL,
            description TEXT
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            department_id INTEGER NOT NULL,
            position TEXT NOT NULL,
            is_active BOOLEAN DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (department_id) REFERENCES departments (id)
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sender_id INTEGER NOT NULL,
            recipient_id INTEGER NOT NULL,
            content TEXT NOT NULL,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            is_read BOOLEAN DEFAULT 0,
            priority TEXT DEFAULT 'normal',
            FOREIGN KEY (sender_id) REFERENCES users (id),
            FOREIGN KEY (recipient_id) REFERENCES users (id)
        )
    ''')
    
    # Добавляем отделения
    departments = [
        ('Кардиология', 'Отделение кардиологии'),
        ('Неврология', 'Отделение неврологии'),
        ('Хирургия', 'Хирургическое отделение'),
        ('Терапия', 'Терапевтическое отделение'),
        ('Педиатрия', 'Детское отделение'),
        ('Реанимация', 'Отделение реанимации'),
        ('Администрация', 'Административный отдел')
    ]
    
    cursor.executemany('INSERT OR IGNORE INTO departments (name, description) VALUES (?, ?)', departments)
    
    conn.commit()
    conn.close()

@login_manager.user_loader
def load_user(user_id):
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute('''
        SELECT u.*, d.name 
        FROM users u 
        JOIN departments d ON u.department_id = d.id 
        WHERE u.id = ?
    ''', (user_id,))
    user_data = cursor.fetchone()
    conn.close()
    
    if user_data:
        return User(*user_data)
    return None

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
        
        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()
        cursor.execute('''
            SELECT u.*, d.name 
            FROM users u 
            JOIN departments d ON u.department_id = d.id 
            WHERE u.username = ?
        ''', (username,))
        user_data = cursor.fetchone()
        conn.close()
        
        if user_data and check_password_hash(user_data[3], password):
            user = User(*user_data)
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
        department_id = request.form['department']
        position = request.form['position']

        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()

        # Проверяем, существует ли пользователь
        cursor.execute('SELECT id FROM users WHERE username = ?', (username,))
        if cursor.fetchone():
            flash('Пользователь уже существует')
            conn.close()
            return render_template('register.html')

        # Хешируем пароль
        password_hash = generate_password_hash(password)

        # Добавляем пользователя
        cursor.execute('''
            INSERT INTO users (username, email, password_hash, department_id, position)
            VALUES (?, ?, ?, ?, ?)
        ''', (username, email, password_hash, department_id, position))
        
        user_id = cursor.lastrowid

        # Получаем название отдела ДО закрытия соединения
        cursor.execute('SELECT name FROM departments WHERE id = ?', (department_id,))
        dept_row = cursor.fetchone()
        dept_name = dept_row[0] if dept_row else None

        conn.commit()
        conn.close()

        # Создаём объект пользователя
        user = User(user_id, username, email, password_hash, department_id, position, True, datetime.utcnow(), dept_name)
        login_user(user)
        return redirect(url_for('dashboard'))

    # Если GET-запрос — получаем список отделов
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute('SELECT id, name FROM departments ORDER BY name')
    departments = cursor.fetchall()
    conn.close()

    return render_template('register.html', departments=departments)


@app.route('/dashboard')
@login_required
def dashboard():
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT m.*, u.username, d.name, u.position
        FROM messages m
        JOIN users u ON m.sender_id = u.id
        JOIN departments d ON u.department_id = d.id
        WHERE m.recipient_id = ?
        ORDER BY m.timestamp DESC
        LIMIT 10
    ''', (current_user.id,))
    
    messages_data = cursor.fetchall()
    
    cursor.execute('SELECT COUNT(*) FROM messages WHERE recipient_id = ? AND is_read = 0', (current_user.id,))
    unread_count = cursor.fetchone()[0]
    
    conn.close()
    
    messages = []
    for msg in messages_data:
        message = {
            'id': msg[0],
            'sender_id': msg[1],
            'recipient_id': msg[2],
            'content': msg[3],
            'timestamp': datetime.fromisoformat(msg[4]),
            'is_read': msg[5],
            'priority': msg[6],
            'file_path': msg[7] if len(msg) > 7 else None,
            'file_name': msg[8] if len(msg) > 8 else None,
            'sender': {
                'username': msg[9] if len(msg) > 9 else '',
                'department': msg[10] if len(msg) > 10 else '',
                'position': msg[11] if len(msg) > 11 else ''
            }
        }
        messages.append(message)
    
    return render_template('dashboard.html', messages=messages, unread_count=unread_count)

@app.route('/send_message', methods=['GET', 'POST'])
@login_required
def send_message():
    if request.method == 'POST':
        recipient_username = request.form['recipient']
        content = request.form['content']
        priority = request.form.get('priority', 'normal')
        
        file_path = None
        file_name = None
        
        if 'file' in request.files:
            file = request.files['file']
            if file and file.filename:
                file_name = secure_filename(file.filename)
                file_path = os.path.join(app.config['UPLOAD_FOLDER'], f"{datetime.now().timestamp()}_{file_name}")
                file.save(file_path)
        
        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()
        
        cursor.execute('SELECT id FROM users WHERE username = ?', (recipient_username,))
        recipient_data = cursor.fetchone()
        
        if not recipient_data:
            flash('Получатель не найден')
            conn.close()
            return render_template('send_message.html')
        
        cursor.execute('''
            INSERT INTO messages (sender_id, recipient_id, content, priority, file_path, file_name)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (current_user.id, recipient_data[0], content, priority, file_path, file_name))
        
        conn.commit()
        conn.close()
        
        flash('Сообщение отправлено')
        return redirect(url_for('dashboard'))
    
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute('''
        SELECT u.id, u.username, d.name, u.position 
        FROM users u 
        JOIN departments d ON u.department_id = d.id 
        WHERE u.id != ?
    ''', (current_user.id,))
    users_data = cursor.fetchall()
    conn.close()
    
    users = []
    for user_data in users_data:
        users.append({
            'id': user_data[0],
            'username': user_data[1],
            'department': user_data[2],
            'position': user_data[3]
        })
    
    return render_template('send_message.html', users=users)

@app.route('/messages')
@login_required
def messages():
    page = request.args.get('page', 1, type=int)
    per_page = 20
    offset = (page - 1) * per_page
    
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT m.*, u.username, d.name, u.position
        FROM messages m
        JOIN users u ON m.sender_id = u.id
        JOIN departments d ON u.department_id = d.id
        WHERE m.recipient_id = ?
        ORDER BY m.timestamp DESC
        LIMIT ? OFFSET ?
    ''', (current_user.id, per_page, offset))
    
    messages_data = cursor.fetchall()
    
    cursor.execute('SELECT COUNT(*) FROM messages WHERE recipient_id = ?', (current_user.id,))
    total = cursor.fetchone()[0]
    
    conn.close()
    
    messages_list = []
    for msg in messages_data:
        message = {
            'id': msg[0],
            'sender_id': msg[1],
            'recipient_id': msg[2],
            'content': msg[3],
            'timestamp': datetime.fromisoformat(msg[4]),
            'is_read': msg[5],
            'priority': msg[6],
            'file_path': msg[7] if len(msg) > 7 else None,
            'file_name': msg[8] if len(msg) > 8 else None,
            'sender': {
                'username': msg[9] if len(msg) > 9 else '',
                'department': msg[10] if len(msg) > 10 else '',
                'position': msg[11] if len(msg) > 11 else ''
            }
        }
        messages_list.append(message)
    
    has_prev = page > 1
    has_next = offset + per_page < total
    
    class MessagesObj:
        def __init__(self, items, has_prev, has_next, prev_num, next_num, page, pages):
            self.items = items
            self.has_prev = has_prev
            self.has_next = has_next
            self.prev_num = prev_num
            self.next_num = next_num
            self.page = page
            self.pages = pages
        
        def iter_pages(self):
            for i in range(1, self.pages + 1):
                yield i
    
    messages_obj = MessagesObj(
        messages_list,
        has_prev,
        has_next,
        page - 1 if has_prev else None,
        page + 1 if has_next else None,
        page,
        (total + per_page - 1) // per_page
    )
    
    return render_template('messages.html', messages=messages_obj)

@app.route('/mark_read/<int:message_id>')
@login_required
def mark_read(message_id):
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    
    cursor.execute('SELECT recipient_id FROM messages WHERE id = ?', (message_id,))
    message_data = cursor.fetchone()
    
    if message_data and message_data[0] == current_user.id:
        cursor.execute('UPDATE messages SET is_read = 1 WHERE id = ?', (message_id,))
        conn.commit()
    
    conn.close()
    return redirect(url_for('messages'))

@app.route('/api/notifications')
@login_required
def get_notifications():
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    
    cursor.execute('SELECT COUNT(*) FROM messages WHERE recipient_id = ? AND is_read = 0', (current_user.id,))
    unread_count = cursor.fetchone()[0]
    
    cursor.execute('''
        SELECT m.content, u.username, m.timestamp, m.priority
        FROM messages m
        JOIN users u ON m.sender_id = u.id
        WHERE m.recipient_id = ? AND m.is_read = 0
        ORDER BY m.timestamp DESC
        LIMIT 5
    ''', (current_user.id,))
    
    recent_messages = cursor.fetchall()
    conn.close()
    
    return jsonify({
        'unread_count': unread_count,
        'recent_messages': [{
            'content': msg[0][:50] + '...' if len(msg[0]) > 50 else msg[0],
            'sender': msg[1],
            'timestamp': msg[2],
            'priority': msg[3]
        } for msg in recent_messages]
    })

@app.route('/download/<path:filename>')
@login_required
def download_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename, as_attachment=True)

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

if __name__ == '__main__':
    init_db()
    app.run(debug=True)