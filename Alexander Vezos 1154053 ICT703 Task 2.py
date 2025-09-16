# Imports
import os
import sqlite3
import hashlib
import threading
import webbrowser
import re # Import the regular expression module
from flask import Flask, render_template, request, redirect, session

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
        admin_user = ('admin', 'secret', 1)
        # Check for admin first
        cursor.execute("SELECT id FROM users WHERE username = ?", (admin_user[0],))
        if not cursor.fetchone():
            admin_password_hash = hash_password(admin_user[1])
            cursor.execute('''
                INSERT INTO users (username, password_hash, is_admin) 
                VALUES (?, ?, ?)
            ''', (admin_user[0], admin_password_hash, admin_user[2]))

        test_users = [
            ('user1', 'password123', 0),
            ('user2', 'password456', 0)
        ]

        # Fill database with test users 
        for username, password, is_admin in test_users:
            # Check if user exists before inserting
            cursor.execute("SELECT id FROM users WHERE username = ?", (username,))
            if not cursor.fetchone():
                password_hash = hash_password(password)
                cursor.execute('''
                    INSERT INTO users (username, password_hash, is_admin) 
                    VALUES (?, ?, ?)
                ''', (username, password_hash, is_admin))

        # Check if training modules already exist before inserting
        cursor.execute('SELECT COUNT(*) FROM training_modules')
        module_count = cursor.fetchone()[0]

        if module_count == 0: # Only insert if no modules exist
            cursor.execute('''
                INSERT INTO training_modules (title, length, quiz_question, quiz_answer) 
                VALUES (?, ?, ?, ?)
            ''', ('Database 101', '10 minutes',
                'What does SQL stand for?', 
                'Structured Query Language'))

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
    
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()

    # Check if the user is an admin
    cursor.execute('SELECT is_admin FROM users WHERE id = ?', (user_id,))
    is_admin = cursor.fetchone()[0]
    
    # Get error from the request arguments if it exists
    error = request.args.get('error', None)

    if is_admin:
        # Show admin dashboard
        cursor.execute('SELECT * FROM users WHERE is_admin = 0 ORDER BY id ASC')
        all_users = cursor.fetchall()
        
        cursor.execute('SELECT * FROM training_modules ORDER BY id ASC')
        all_modules = cursor.fetchall()
        
        conn.close()
        # Pass the is_admin_page variable as True
        return render_template('admin.html', users=all_users, modules=all_modules, is_admin_page=True, error=error)
    
    else:
        # Get incomplete training
        cursor.execute('''
            SELECT tm.title, tm.length, utp.completed, tm.id, tm.created_at
            FROM training_modules tm
            LEFT JOIN user_training_progress utp ON tm.id = utp.module_id AND utp.user_id = ?
            WHERE utp.completed IS NULL OR utp.completed = 0
            ORDER BY tm.created_at ASC
        ''', (user_id,))
        incomplete_training = cursor.fetchall()
        
        # Get completed training
        cursor.execute('''
            SELECT tm.title, utp.completed_at
            FROM training_modules tm
            JOIN user_training_progress utp ON tm.id = utp.module_id
            WHERE utp.user_id = ? AND utp.completed = 1
            ORDER BY utp.completed_at ASC
        ''', (user_id,))
        completed_training = cursor.fetchall()
        
        conn.close()
        
        # Pass the is_admin_page variable as False
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
    
    conn = sqlite3.connect(DATABASE)
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
    conn = sqlite3.connect(DATABASE)
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
        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM training_modules WHERE id = ?', (module_id,))
        module = cursor.fetchone()
        conn.close()
        
        error = "Incorrect answer. Please try again."
        return render_template('training.html', module=module, error=error)

# Buffer page for adding training
@gui.route('/admin/add_module', methods=['POST'])
def admin_add_module():
    if 'user_id' not in session:
        return redirect('/login')

    user_id = session['user_id']
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute('SELECT is_admin FROM users WHERE id = ?', (user_id,))
    is_admin = cursor.fetchone()[0]

    if not is_admin:
        conn.close()
        return redirect('/')

    title = request.form['title']
    length = request.form['length']
    question = request.form['question']
    answer = request.form['answer']
    
    error = None

    # Regex validation for length field
    length_regex = r'^\d+\s(second|seconds|minute|minutes|hour|hours)$'
    if not re.match(length_regex, length):
        error = "Invalid length format. Please use 'number unit' (e.g., '10 minutes')."
    
    # If the regex validation passes, proceed with the database transaction
    if error is None:
        try:
            cursor.execute('''
                INSERT INTO training_modules (title, length, quiz_question, quiz_answer) 
                VALUES (?, ?, ?, ?)
            ''', (title, length, question, answer))
            
            module_id = cursor.lastrowid
            cursor.execute('SELECT id FROM users WHERE is_admin = 0')
            users = cursor.fetchall()
            
            for user in users:
                cursor.execute('''
                    INSERT OR IGNORE INTO user_training_progress (user_id, module_id, completed) 
                    VALUES (?, ?, 0)
                ''', (user[0], module_id))
            
            conn.commit()
            conn.close()
            return redirect('/')

        except sqlite3.IntegrityError:
            error = "A module with this title already exists."
    
    # If there was an error (either from regex or IntegrityError), this code will run
    if error is not None:
        cursor.execute('SELECT * FROM users WHERE is_admin = 0 ORDER BY id ASC')
        all_users = cursor.fetchall()
        cursor.execute('SELECT * FROM training_modules ORDER BY id ASC')
        all_modules = cursor.fetchall()
        conn.close()
        return render_template('admin.html', 
                                users=all_users, 
                                modules=all_modules, 
                                error=error)

# Page for printing a user's progress
@gui.route('/admin/user_report/<int:user_id>')
def user_report(user_id):
    if 'user_id' not in session:
        return redirect('/login')
    
    # Check if current user is admin
    current_user_id = session['user_id']
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute('SELECT is_admin FROM users WHERE id = ?', (current_user_id,))
    is_admin = cursor.fetchone()[0]
    
    if not is_admin:
        conn.close()
        return redirect('/')
    
    # Get user info
    cursor.execute('SELECT username FROM users WHERE id = ?', (user_id,))
    username = cursor.fetchone()[0]
    
    # Get the view type from the URL, default to 'incomplete'
    view = request.args.get('view', 'incomplete')

    completed_courses = []
    incomplete_courses = []

    # Get completed courses (sorted by completion date)
    if view == 'completed' or view == 'all':
        cursor.execute('''
            SELECT tm.title, tm.length, utp.completed_at
            FROM training_modules tm
            JOIN user_training_progress utp ON tm.id = utp.module_id
            WHERE utp.user_id = ? AND utp.completed = 1
            ORDER BY utp.completed_at ASC
        ''', (user_id,))
        completed_courses = cursor.fetchall()
    
    # Get incomplete courses (sorted by creation date)
    if view == 'incomplete' or view == 'all':
        cursor.execute('''
            SELECT tm.title, tm.length, tm.created_at
            FROM training_modules tm
            LEFT JOIN user_training_progress utp ON tm.id = utp.module_id AND utp.user_id = ?
            WHERE utp.completed IS NULL OR utp.completed = 0
            ORDER BY tm.created_at ASC
        ''', (user_id,))
        incomplete_courses = cursor.fetchall()
    
    conn.close()
    
    return render_template('user_report.html', 
                        username=username, 
                        user_id=user_id,
                        completed_courses=completed_courses,
                        incomplete_courses=incomplete_courses,
                        view=view)

# Nukes the database
@gui.route('/admin/reset_db')
def admin_reset_db():
    if 'user_id' not in session:
        return redirect('/login')

    # Check if current user is admin
    user_id = session['user_id']
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute('SELECT is_admin FROM users WHERE id = ?', (user_id,))
    user_data = cursor.fetchone()

    if not user_data or not user_data[0]:
        conn.close()
        return redirect('/')  # Redirect non-admins

    # Delete the database file
    conn.close()
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