# Imports
import sqlite3 # Using a SQL database for data storage
import hashlib # Hash password for security
import threading
import webbrowser
from flask import Flask, render_template, request, redirect, session  # Making a GUI front end using HTML

DATABASE = 'ict703-task2.db'

# Hashes passwords using SHA-256
def hash_password(password):
    return hashlib.sha256(password.encode('utf-8')).hexdigest()

# Initialise the database
def init_db():
    with sqlite3.connect(DATABASE) as conn:
        cursor = conn.cursor()

        # Users table - stores both regular users and admin
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                is_admin BOOLEAN DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Training modules table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS training_modules (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT UNIQUE NOT NULL,
                length TEXT NOT NULL,
                quiz_question TEXT NOT NULL,
                quiz_answer TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # User training progress table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_training_progress (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                module_id INTEGER,
                completed BOOLEAN DEFAULT 0,
                completed_at TIMESTAMP NULL,
                FOREIGN KEY (user_id) REFERENCES users (id),
                FOREIGN KEY (module_id) REFERENCES training_modules (id),
                UNIQUE(user_id, module_id)
            )
        ''')

        # Create default admin user (username: 'admin', password: 'secret')
        admin_password_hash = hash_password('secret')
        cursor.execute('''
            INSERT OR IGNORE INTO users (username, password_hash, is_admin) 
            VALUES ('admin', ?, 1)
        ''', (admin_password_hash,))

        test_users = [
            ('user1', 'password123', 0),
            ('user2', 'password456', 0)
        ]

        # Fill database with test users 
        for username, password, is_admin in test_users:
            password_hash = hash_password(password)
            cursor.execute('''
                INSERT OR IGNORE INTO users (username, password_hash, is_admin) 
                VALUES (?, ?, ?)
            ''', (username, password_hash, is_admin))

        # Check if training modules already exist before inserting
        cursor.execute('SELECT COUNT(*) FROM training_modules')
        module_count = cursor.fetchone()[0]

        if module_count == 0: # Only insert if no modules exist
            cursor.execute('''
                INSERT OR IGNORE INTO training_modules (title, length, quiz_question, quiz_answer) 
                VALUES (?, ?, ?, ?)
            ''', ('Database 101', '10 minutes',
                'What does SQL stand for?', 
                'Structured Query Language'))

        conn.commit()

# Initialise the GUI
gui = Flask(__name__)
gui.secret_key = 'La Li Lu Le Lo'

# Home Page
@gui.route('/')
def index():
    if 'user_id' not in session:
        return redirect('/login')
    
    user_id = session['user_id']
    
    conn = sqlite3.connect('ict703-task2.db')
    cursor = conn.cursor()
    
    # Get incomplete training
    cursor.execute('''
        SELECT tm.title, tm.length, tm.quiz_question, tm.id, tm.created_at
        FROM training_modules tm
        LEFT JOIN user_training_progress utp ON tm.id = utp.module_id AND utp.user_id = ?
        WHERE utp.completed IS NULL OR utp.completed = 0
        ORDER BY tm.created_at DESC
    ''', (user_id,))
    incomplete_training = cursor.fetchall()
    
    # Get completed training
    cursor.execute('''
        SELECT tm.title, utp.completed_at
        FROM training_modules tm
        JOIN user_training_progress utp ON tm.id = utp.module_id
        WHERE utp.user_id = ? AND utp.completed = 1
        ORDER BY utp.completed_at DESC
    ''', (user_id,))
    completed_training = cursor.fetchall()
    
    conn.close()
    
    return render_template('index.html', 
                        incomplete_training=incomplete_training,
                        completed_training=completed_training)

# Login Page
@gui.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        password_hash = hash_password(password)
        
        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM users WHERE username = ? AND password_hash = ?', 
                    (username, password_hash))
        user = cursor.fetchone()
        conn.close()
        
        if user:
            session['user_id'] = user[0]  # Store user ID in session
            return redirect('/') # Home page if successful
        else:
            error = "Invalid username or password!"
    
    return render_template('login.html', error=error) # Show login form

# Register page
@gui.route('/register', methods=['GET', 'POST'])
def register():
    error = None
    
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        password_hash = hash_password(password)
        
        try:
            with sqlite3.connect(DATABASE) as conn:
                cursor = conn.cursor()
                cursor.execute('INSERT INTO users (username, password_hash) VALUES (?, ?)', 
                            (username, password_hash))
                conn.commit()
            return redirect('/login') # Go back to login after success
        except sqlite3.IntegrityError:
            error = "Username already exists!"
    
    return render_template('register.html', error=error)

# Training module page
@gui.route('/training/<int:module_id>')
def take_training(module_id):
    if 'user_id' not in session:
        return redirect('/login')
    
    conn = sqlite3.connect('ict703-task2.db')
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM training_modules WHERE id = ?', (module_id,))
    module = cursor.fetchone()
    conn.close()
    
    return render_template('training.html', module=module)

# Buffer page for completing training
@gui.route('/submit_training/<int:module_id>', methods=['POST'])
def submit_training(module_id):
    if 'user_id' not in session:
        return redirect('/login')
    
    user_answer = request.form['answer']
    user_id = session['user_id']
    
    # Get the correct answer from database
    conn = sqlite3.connect('ict703-task2.db')
    cursor = conn.cursor()
    cursor.execute('SELECT quiz_answer FROM training_modules WHERE id = ?', (module_id,))
    correct_answer = cursor.fetchone()[0]
    
    # Check if answer is correct (case-insensitive and trimmed)
    if user_answer.lower().strip() == correct_answer.lower().strip():
        # Mark as completed
        cursor.execute('''
            INSERT OR REPLACE INTO user_training_progress 
            (user_id, module_id, completed, completed_at) 
            VALUES (?, ?, 1, CURRENT_TIMESTAMP)
        ''', (user_id, module_id))
        conn.commit()
        conn.close()
        return redirect('/')
    else:
        conn.close()
        # Get module info again to show error
        conn = sqlite3.connect('ict703-task2.db')
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM training_modules WHERE id = ?', (module_id,))
        module = cursor.fetchone()
        conn.close()
        
        error = "Incorrect answer. Please try again."
        return render_template('training.html', module=module, error=error)

# Run the script
if __name__ == '__main__':
    init_db()

    # Auto-open browser after a short delay
    def open_browser():
        webbrowser.open('http://localhost:5000/login')
    
    timer = threading.Timer(1.5, open_browser)
    timer.daemon = True
    timer.start()
    
    gui.run(debug=False, host='0.0.0.0', port=5000)