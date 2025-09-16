# Imports
import os
import sqlite3 # For local SQL Database for data storage
import hashlib # For keeping passwords secure
import threading
import webbrowser
import re # Import the regular expression module
from flask import Flask, render_template, request, redirect, session # For GUI front end using HTML

DATABASE = 'ict703-task2.db'

# Hashes passwords using SHA-256
def hash_password(password):
    return hashlib.sha256(password.encode('utf-8')).hexdigest()

# Helper function to get database connection
def get_db_connection():
    return sqlite3.connect(DATABASE)

# Helper function to check if user is admin
def is_user_admin(user_id):
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT is_admin FROM users WHERE id = ?', (user_id,))
        result = cursor.fetchone()
        return result[0] if result else False

# Ensure user has progress records for all modules
def ensure_user_progress_records(user_id):
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT id FROM training_modules')
        all_modules = cursor.fetchall()
        
        # Insert a progress record for each module if one doesn't exist
        for module in all_modules:
            cursor.execute('''
                INSERT OR IGNORE INTO user_training_progress (user_id, module_id, completed, completed_at) 
                VALUES (?, ?, 0, NULL)
            ''', (user_id, module[0]))
        conn.commit()

# Create default users and modules if they don't exist
def create_default_data(cursor):
    # Create default admin user (username: 'admin', password: 'secret')
    cursor.execute("SELECT id FROM users WHERE username = ?", ('admin',))
    if not cursor.fetchone():
        admin_password_hash = hash_password('secret')
        cursor.execute('''
            INSERT INTO users (username, password_hash, is_admin) 
            VALUES (?, ?, ?)
        ''', ('admin', admin_password_hash, 1))

    # Fill database with test user
    test_users = [('user1', 'password123')]
    for username, password in test_users:
        # Check if user exists before inserting
        cursor.execute("SELECT id FROM users WHERE username = ?", (username,))
        if not cursor.fetchone():
            password_hash = hash_password(password)
            cursor.execute('''
                INSERT INTO users (username, password_hash, is_admin) 
                VALUES (?, ?, ?)
            ''', (username, password_hash, 0))

    # Check if training modules already exist before inserting
    cursor.execute('SELECT COUNT(*) FROM training_modules')
    if cursor.fetchone()[0] == 0: # Only insert if no modules exist
        cursor.execute('''
            INSERT INTO training_modules (title, length, quiz_question, quiz_answer) 
            VALUES (?, ?, ?, ?)
        ''', ('Database 101', '10 minutes', 'What does SQL stand for?', 'Structured Query Language'))

# Initialise the database
def init_db():
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        # Users table - stores both regular users and admin
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                is_admin BOOLEAN DEFAULT 0,
                created_at DATE DEFAULT (datetime('now','localtime'))
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
                created_at DATE DEFAULT (datetime('now','localtime'))
            )
        ''')
        
        # Create user_training_progress table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_training_progress (
                user_id INTEGER,
                module_id INTEGER,
                completed BOOLEAN NOT NULL DEFAULT 0,
                completed_at TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id),
                FOREIGN KEY (module_id) REFERENCES training_modules(id),
                PRIMARY KEY (user_id, module_id)
            );
        ''')

        create_default_data(cursor)
        conn.commit()

# Initialise the GUI
gui = Flask(__name__)
gui.secret_key = 'La Li Lu Le Lo'

# Home Page (Both user/admin)
@gui.route('/')
def index():
    if 'user_id' not in session:
        return redirect('/login')
    
    user_id = session['user_id']
    
    # Get error from the request arguments if it exists
    error = request.args.get('error', None)

    if is_user_admin(user_id):
        # Show admin dashboard
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM users WHERE is_admin = 0 ORDER BY id ASC')
            all_users = cursor.fetchall()
            cursor.execute('SELECT * FROM training_modules ORDER BY id ASC')
            all_modules = cursor.fetchall()
        
        # Pass the is_admin_page variable as True
        return render_template('admin.html', users=all_users, modules=all_modules, 
                            is_admin_page=True, error=error)
    else:
        # User dashboard - ensure progress records exist
        ensure_user_progress_records(user_id)
        
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT tm.title, tm.length, utp.completed, utp.completed_at, tm.created_at, tm.id
                FROM user_training_progress utp
                JOIN training_modules tm ON utp.module_id = tm.id
                WHERE utp.user_id = ?
                ORDER BY utp.completed ASC, tm.created_at ASC
            ''', (user_id,))
            training_data = cursor.fetchall()
        
        incomplete_training = [row for row in training_data if row[2] == 0]
        completed_training = [row for row in training_data if row[2] == 1]
        
        return render_template('index.html', 
                            incomplete_training=incomplete_training, 
                            completed_training=completed_training, 
                            is_admin_page=False)

# Login Page
@gui.route('/login', methods=['GET', 'POST'])
def login():
    error = None

    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        password_hash = hash_password(password)
        
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM users WHERE username = ? AND password_hash = ?', 
                        (username, password_hash))
            user = cursor.fetchone()
        
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
            with get_db_connection() as conn:
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
    
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM training_modules WHERE id = ?', (module_id,))
        module = cursor.fetchone()
    
    return render_template('training.html', module=module)

# Buffer page for completing training
@gui.route('/submit_training/<int:module_id>', methods=['POST'])
def submit_training(module_id):
    if 'user_id' not in session:
        return redirect('/login')

    user_answer = request.form['answer']
    user_id = session['user_id']
    
    # Get the correct answer from database
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT quiz_answer FROM training_modules WHERE id = ?', (module_id,))
        correct_answer = cursor.fetchone()[0]
        
        # Check if answer is correct (case-insensitive and trimmed)
        if user_answer.lower().strip() == correct_answer.lower().strip():
            # Correctly update the existing record
            cursor.execute('''
                UPDATE user_training_progress 
                SET completed = 1, completed_at = CURRENT_TIMESTAMP 
                WHERE user_id = ? AND module_id = ?
            ''', (user_id, module_id))
            conn.commit()
            return redirect('/')
        else:
            # Get module info again to show error
            cursor.execute('SELECT * FROM training_modules WHERE id = ?', (module_id,))
            module = cursor.fetchone()
            error = "Incorrect answer. Please try again."
            return render_template('training.html', module=module, error=error)

# Buffer page for adding training
@gui.route('/admin/add_module', methods=['POST'])
def admin_add_module():
    if 'user_id' not in session:
        return redirect('/login')

    user_id = session['user_id']
    if not is_user_admin(user_id):
        return redirect('/')

    title = request.form['title']
    length = request.form['length']
    question = request.form['question']
    answer = request.form['answer']
    
    # Regex validation for length format
    length_regex = r'^\d+\s(second|seconds|minute|minutes|hour|hours)$'
    if not re.match(length_regex, length):
        error = "Invalid length format. Please use 'number unit' (e.g., '10 minutes')."
        return redirect(f'/?error={error}')
    
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO training_modules (title, length, quiz_question, quiz_answer) 
                VALUES (?, ?, ?, ?)
            ''', (title, length, question, answer))
            
            module_id = cursor.lastrowid
            
            # Add progress records for all non-admin users
            cursor.execute('SELECT id FROM users WHERE is_admin = 0')
            users = cursor.fetchall()
            
            for user in users:
                cursor.execute('''
                    INSERT OR IGNORE INTO user_training_progress (user_id, module_id, completed, completed_at) 
                    VALUES (?, ?, 0, NULL)
                ''', (user[0], module_id))
            
            conn.commit()
        
        return redirect('/') # Redirect to the admin page on successful addition

    except sqlite3.IntegrityError:
        error = "A module with this title already exists."
        return redirect(f'/?error={error}')

# Page for printing a user's progress
@gui.route('/admin/user_report/<int:user_id>')
def user_report(user_id):
    if 'user_id' not in session:
        return redirect('/login')

    # Check if current user is admin
    if not is_user_admin(session['user_id']):
        return redirect('/')

    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        # Get user info
        cursor.execute('SELECT username FROM users WHERE id = ?', (user_id,))
        report_user = cursor.fetchone()
        
        if not report_user:
            return "User not found", 404

        # Get all training data for the user
        cursor.execute('''
            SELECT tm.title, tm.length, utp.completed_at, tm.created_at
            FROM user_training_progress utp
            JOIN training_modules tm ON utp.module_id = tm.id
            WHERE utp.user_id = ? AND utp.completed = 1
            ORDER BY utp.completed_at DESC
        ''', (user_id,))
        completed_courses = cursor.fetchall()
        
        cursor.execute('''
            SELECT tm.title, tm.length, tm.created_at
            FROM user_training_progress utp
            JOIN training_modules tm ON utp.module_id = tm.id
            WHERE utp.user_id = ? AND utp.completed = 0
            ORDER BY tm.title ASC
        ''', (user_id,))
        incomplete_courses = cursor.fetchall()
    
    return render_template('user_report.html',
                        username=report_user[0],
                        incomplete_courses=incomplete_courses,
                        completed_courses=completed_courses,
                        is_admin_page=True)

# Nukes the database
@gui.route('/admin/reset_db')
def admin_reset_db():
    if 'user_id' not in session:
        return redirect('/login')

    # Check if current user is admin
    if not is_user_admin(session['user_id']):
        return redirect('/')  # Redirect non-admins

    # Delete the database file
    if os.path.exists(DATABASE):
        os.remove(DATABASE)
    
    # Recreate fresh database
    init_db()
    
    # Clear session and redirect to login
    session.clear()
    return redirect('/login')

# Logging out functionality
@gui.route('/logout')
def logout():
    session.clear()  # Clear all session data including user_id
    return redirect('/login')

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