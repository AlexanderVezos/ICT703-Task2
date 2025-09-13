# Imports
import os
import ssl # For secure connection to DB
import redis # Cloud NoSQL Service to store user information
from flask import Flask, render_template # GUI front end using HTML
from dotenv import load_dotenv # Securely store DB credentials
import webbrowser
import threading

# Load secured DB credentials
load_dotenv() 

# Connect to NoSQL server
redis_url = f"redis://{os.getenv('REDIS_USERNAME')}:{os.getenv('REDIS_PASSWORD')}@{os.getenv('REDIS_HOST')}:{os.getenv('REDIS_PORT')}/0"
r = redis.from_url(redis_url, decode_responses=True)

# Initialize  the GUI
gui = Flask(__name__)

@gui.route('/')
def home():
    return render_template('index.html')

# Run the script
if __name__ == '__main__':
    print(f"Connecting to Redis at: {os.getenv('REDIS_HOST')}:{os.getenv('REDIS_PORT')}")
    
    # Test DB connection on startup
    try:
        r.ping()
        print("Redis connection successful!")
    except Exception as e:
        print(f"Redis connection failed: {e}")
    
        # Auto-open browser after a short delay
    def open_browser():
        webbrowser.open('http://localhost:5000')
    
    timer = threading.Timer(1.5, open_browser)
    timer.daemon = True
    timer.start()
    
    gui.run(debug=False, host='0.0.0.0', port=5000)