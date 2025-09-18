# ICT703-Task2
A simple Python program for a mock Cyber Security Training System

## Setup Instructions
This project requires Python 3.x and uses external dependencies (mainly Flask).

### Option 1: Quick Setup
```bash
pip install -r requirements.txt
py AlexanderVezos_1154053_ICT703_Task2.py
```

### Option 2: Using Virtual Environment
```bash
# Create virtual environment
py -m venv [your venv name]

# Activate virtual environment
# Windows:
[your venv name]\Scripts\activate
# Mac/Linux:
source [your venv name]/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run the application
py AlexanderVezos_1154053_ICT703_Task2.py

# When finished, deactivate (optional)
deactivate
```

## How To Use
The program starts with two initial accounts (A user and an admin). You are also able to register new users.
### User Credentials:
```
Username: user1
Password: password123
```
### Admin Credentials:
```
Username: admin
Password: secret
```
User features:
- Complete training modules
- View incomplete/completed training

Admins features:
- Create new training modules
- View all users in the system
- View all modules in the system
- View individual reports of the incomplete/completed training of a user
- Reset the SQLite database

## Notes
- Tested in virtual environment built on Python 3.13.7
