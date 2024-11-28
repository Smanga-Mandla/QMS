from flask import Flask, render_template, request, redirect, url_for, session, jsonify
import firebase_admin
from firebase_admin import credentials, initialize_app, auth, storage, firestore
import uuid
from flask_mail import Mail, Message
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger

from dotenv import load_dotenv
import requests
import re
from google.cloud.firestore_v1 import ArrayUnion
from functools import wraps
from datetime import timedelta, datetime
from werkzeug.utils import secure_filename
import os
from flask import send_from_directory, abort
load_dotenv()
app = Flask(__name__)
app.config['TESTING'] = True
# Secret Key
app.secret_key = b'\x9dQ\x920\xce\x03\x13\x9f\xe2\xb0\xb14\xd0Fg\xbd\x08VQ\xff\xb8\xa7@\xa0'



import requests
def download_json(url, filename):
    """
    Download a JSON file from a URL and save it to the current directory.
    Args:
        url (str): The URL of the JSON file.
        filename (str): The name of the file to save.
    """
    response = requests.get(url)
    if response.status_code == 200:
        with open(filename, 'w') as file:
            file.write(response.text)
        print(f"File downloaded and saved as {filename}")
    else:
        print(f"Failed to download file. Status code: {response.status_code}")
# Example usage:
url = 'https://media.nextgensell.com/files/mandla/qms-flask-firebase.json'
filename = 'qms-flask-firebase.json'
download_json(url, filename)


# Set the session lifetime
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(minutes=4)  # Session will expire after 30 minutes

# Initialize Firebase Admin SDK
cred = credentials.Certificate('qms-flask-firebase.json')
initialize_app(cred, {'storageBucket': 'qms-flask.appspot.com'})
db = firestore.client()


scheduler = BackgroundScheduler()
scheduler.start()

# Schedule periodic reminder emails
def schedule_event_reminder(lecturer_email, module_name, event_name, closing_date):
    def send_reminder():
        if datetime.now().date() < datetime.strptime(closing_date, '%Y-%m-%d').date():
            send_event_notification_email(lecturer_email, module_name, event_name, closing_date)
    
    # Schedule a job to run daily
    scheduler.add_job(
        send_reminder,
        trigger=IntervalTrigger(days=1),
        id=f"reminder_{event_name}_{module_name}",
        replace_existing=True,
    )





# Configure Flask-Mail
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = 'smangamandla05@gmail.com'
app.config['MAIL_PASSWORD'] = 'imejpgwajlguzihi'  # Use the app password
app.config['MAIL_DEFAULT_SENDER'] = ('Quality Management System(QMS)', 'smangamandla05@gmail.com')

mail = Mail(app)




# Firebase Web API Key
FIREBASE_WEB_API_KEY = os.getenv('FIREBASE_WEB_API_KEY')

# Function to verify user credentials using Firebase Authentication REST API
def verify_user_credentials(email, password):
    url = f'https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key={FIREBASE_WEB_API_KEY}'
    payload = {
        "email": email,
        "password": password,
        "returnSecureToken": True
    }
    response = requests.post(url, json=payload)
    return response.json()

# Decorator to protect routes that require login
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('sign_in_page', message='Please log in first'))
        return f(*args, **kwargs)
    return decorated_function

@app.route('/extend_session', methods=['POST'])
def extend_session():
    if 'user_id' in session:
        session.permanent = True  # Extend the session for another 30 minutes
        return jsonify({"message": "Session extended successfully", "status": "extended"})
    return jsonify({"message": "Session expired", "status": "expired"}), 401
 

# Sign in route
@app.route('/sign_in', methods=['GET', 'POST'])
def sign_in():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        selected_role = request.form.get('role')  # Get the selected role from the form

        # Email format validation
        if not re.match(r'\d{9}@ump\.ac\.za$', email):
            return render_template('signin.html', message='Invalid email format. Please use the format: Enter_Staff_number@ump.ac.za')

        # Strong password validation
        if not re.match(r'^(?=.*[A-Z])(?=.*[a-z])(?=.*\d)(?=.*[@$!%*?&])[A-Za-z\d@$!%*?&]{8,}$', password):
            return render_template('signin.html', message='Password must be at least 8 characters long and include at least one uppercase letter, one lowercase letter, one number, and one special character.')

        try:
            # Verify user credentials using Firebase Authentication
            response = verify_user_credentials(email, password)
            if 'error' in response:
                return render_template('signin.html', message=response['error']['message'])

            # Fetch all users with the given email from Firestore
            user_docs = db.collection('users').where('email', '==', email).stream()

            # Match the selected role with one of the users
            matched_user = None
            for user_doc in user_docs:
                user_data = user_doc.to_dict()
                if user_data.get('role') == selected_role:
                    matched_user = user_data
                    matched_user['uid'] = user_doc.id
                    break

            if not matched_user:
                return render_template('signin.html', message='User is not authorized for the selected role.')

            # Set session for the matched user
            session['user_id'] = matched_user['uid']
            session['email'] = matched_user['email']
            session['name'] = matched_user['name']
            session['surname'] = matched_user['surname']
            session['role'] = matched_user['role']

            # Redirect based on role
            if selected_role == 'admin':
                return redirect(url_for('admin_dashboard'))
            elif selected_role == 'lecturer':
                return redirect(url_for('lecture_dashboard'))
            elif selected_role == 'program_leader':
                return redirect(url_for('program_leader_dashboard'))
            else:
                return render_template('signin.html', message='Invalid role selected.')

        except Exception as e:
            return render_template('signin.html', message=str(e))

    return render_template('signin.html')

# Logout route
@app.route('/logout')
def logout():
    session.clear()  # Destroy the session
    return redirect(url_for('sign_in_page'))


@app.route('/admin_home', methods=['GET'])
@login_required
def admin_home():
    user_initials = (session.get('name', '')[0] + session.get('surname', '')[0]).upper()
    # Fetch all users
    users_ref = db.collection('users').stream()
    users = [{'id': user.id, **user.to_dict()} for user in users_ref]

    # Group users by role
    program_leaders = [user for user in users if user['role'] == 'program_leader']
    lecturers = [user for user in users if user['role'] == 'lecturer']

    # Fetch all modules and map associated users
    modules_ref = db.collection('modules').stream()
    modules = []

    for module in modules_ref:
        module_data = module.to_dict()

        # Find the program leader and lecturers for this module
        module_program_leaders = [
            {
                'name': leader['name'],
                'surname': leader['surname'],
                'qualification': leader.get('qualification', 'N/A')
            } 
            for leader in program_leaders if leader['email'] == module_data.get('program_leader_email')
        ]
        module_lecturers = [
            {
                'name': lecturer['name'],
                'surname': lecturer['surname'],
                'qualification': lecturer.get('qualification', 'N/A')
            } 
            for lecturer in lecturers if lecturer['email'] == module_data.get('lecturer_email')
        ]

        # Add grouped users to the module
        modules.append({
            'id': module.id,
            'module_name': module_data.get('module_name'),
            'module_code': module_data.get('module_code'),
            'program_leaders': module_program_leaders,
            'lecturers': module_lecturers
        })

    return render_template('admin_home.html', users=users, modules=modules, user_initials=user_initials)

@app.route('/add_slot/<module_id>', methods=['GET', 'POST'])
def add_slot(module_id):
    user_initials = (session.get('name', '')[0] + session.get('surname', '')[0]).upper()
    if request.method == 'POST':
        title = request.form.get('title')
        description = request.form.get('description')
        closing_date = request.form.get('closing_date')

        # Add the event to Firestore
        event_ref = db.collection('events').add({
            'title': title,
            'description': description,
            'closing_date': closing_date,
            'module_id': module_id
        })

        # Update the module with the new event ID
        module_ref = db.collection('modules').document(module_id)
        module = module_ref.get().to_dict()
        module_events = module.get('events', [])
        module_events.append(event_ref[1].id)
        module_ref.update({'events': module_events})

        return redirect(url_for('admin_home'))

    return render_template('add_slot.html', module_id=module_id, user_initials=user_initials)


from datetime import datetime

@app.route('/view_sub/<module_id>', methods=['GET'])
def view_sub(module_id):
    # Fetch module details
    module_ref = db.collection('modules').document(module_id).get()
    if not module_ref.exists:
        return f"Module with ID {module_id} does not exist.", 404
    module_data = module_ref.to_dict()

    # Fetch submissions for the module
    submissions_ref = db.collection('submissions') \
        .where('module_id', '==', module_id).stream()
    submissions = []
    for sub in submissions_ref:
        submission_data = sub.to_dict()
        
        # Format submission_date as 'YYYY-MM-DD HH:MM:SS'
        submission_date = submission_data.get('submission_date')
        if submission_date:
            submission_data['submission_date'] = submission_date.strftime('%Y-%m-%d %H:%M:%S')
        else:
            submission_data['submission_date'] = 'N/A'

        # Fetch associated event
        event_ref = db.collection('events').document(submission_data['event_id']).get()
        if event_ref.exists:
            event_data = event_ref.to_dict()
            submission_data['event_title'] = event_data.get('title', 'Unknown Event')
            submission_data['qualification'] = event_data.get('qualification', 'Unknown Qualification')
        else:
            submission_data['event_title'] = 'Unknown Event'
            submission_data['qualification'] = 'Unknown Qualification'

        submissions.append({'id': sub.id, **submission_data})

    return render_template(
        'view_sub.html',
        module_id=module_id,
        module_name=module_data.get('module_name'),
        module_code=module_data.get('module_code'),
        submissions=submissions
    )





















## Protecting lecture dashboard with login check
from datetime import datetime
from calendar import monthrange
from flask import render_template, session
from datetime import datetime

@app.route('/lecture_dashboard')
@login_required
def lecture_dashboard():
    if 'role' in session and session['role'] == 'lecturer':
        user_email = session.get('email')
        user_initials = (session.get('name', '')[0] + session.get('surname', '')[0]).upper()

        # Fetch lecturer's modules
        modules = db.collection('modules').where('lecturer_email', '==', user_email).stream()
        modules_data = [{'id': module.id, **module.to_dict()} for module in modules]

        # Fetch all events related to these modules
        events = []
        for module in modules_data:
            events_ref = db.collection('events').where('module_id', '==', module['id']).stream()
            for event in events_ref:
                event_data = event.to_dict()
                event_data['id'] = event.id
                event_data['module_id'] = module['id']
                event_data['module_name'] = module.get('module_name')
                events.append(event_data)


         # Aggregate events and include module info with each event
        events = []
        events_by_date = {}
        for module in modules_data:
            events_ref = db.collection('events').where('module_id', '==', module['id']).stream()
            for event in events_ref:
                event_data = event.to_dict()
                event_data['id'] = event.id
                event_data['module_id'] = module['id']  # Add module ID to each event
                event_data['module_name'] = module.get('module_name')  # Optional: Add module name if needed
                events.append(event_data)

        # Group events by date for calendar rendering
        events_by_date = {}
        for event in events:
            closing_date = event.get('closing_date')
            if closing_date:
                parsed_date = datetime.strptime(closing_date, '%Y-%m-%d').strftime('%Y-%m-%d')
                if parsed_date not in events_by_date:
                    events_by_date[parsed_date] = []
                events_by_date[parsed_date].append(event['title'])

        # Pass events and modules to the dashboard template
        return render_template(
            'lecture_dashboard.html',
            modules=modules_data,
            events=events,
            events_by_date=events_by_date,
            user_initials=user_initials
        )

    return redirect(url_for('sign_in_page'))

from flask import jsonify, request

@app.route('/api/events', methods=['GET'])
def get_events():
    year = request.args.get('year', type=int)
    month = request.args.get('month', type=int)

    if not year or not month:
        return jsonify({'error': 'Invalid year or month'}), 400

    # Filter events by the specified year and month
    events_ref = db.collection('events').stream()
    events_by_date = {}

    for event in events_ref:
        event_data = event.to_dict()
        closing_date = event_data.get('closing_date')

        if closing_date:
            parsed_date = datetime.strptime(closing_date, '%Y-%m-%d')
            if parsed_date.year == year and parsed_date.month == month:
                date_key = parsed_date.strftime('%Y-%m-%d')
                if date_key not in events_by_date:
                    events_by_date[date_key] = []
                events_by_date[date_key].append(event_data['title'])

    return jsonify(events_by_date)




def get_days_in_month(year, month):
    from calendar import monthrange
    return range(1, monthrange(year, month)[1] + 1)

 

@app.route('/program_leader_dashboard')
@login_required
def program_leader_dashboard():
    if 'role' in session and session['role'] == 'program_leader':
        user_initials = (session['name'][0] + session['surname'][0]).upper()
        user_email = session.get('email')

        # Fetch the modules associated with the program leader
        modules = db.collection('modules').where('program_leader_email', '==', user_email).stream()
        modules_data = [{'id': module.id, **module.to_dict()} for module in modules]

        # Dictionary to store the latest submission for each event_id
        submissions = {}
        submissions_by_date = {}  # New dictionary to group submissions by submission_date

        for module in modules_data:
            events_ref = db.collection('events').where('module_id', '==', module['id']).stream()
            for event in events_ref:
                event_data = event.to_dict()
                event_title = event_data.get('title')  # Get the event title
                event_id = event.id  # Get the event ID

                # Fetch submissions for this event
                submissions_ref = db.collection('submissions').where('event_id', '==', event_id).stream()
                for submission in submissions_ref:
                    submission_data = submission.to_dict()
                    submission_data['event_title'] = event_title  # Add event title to submission
                    submission_data['event_id'] = event_id  # Include event_id

                    # Store or replace the latest submission for this event
                    submissions[event_id] = submission_data

                    # Add submission to submissions_by_date
                    submission_date = submission_data.get('submission_date')
                    if submission_date:
                        # Format submission_date to 'YYYY-MM-DD'
                        formatted_date = submission_date.strftime('%Y-%m-%d')
                        if formatted_date not in submissions_by_date:
                            submissions_by_date[formatted_date] = []
                        submissions_by_date[formatted_date].append({
                            "file_url": submission_data.get('file_url'),
                            "submitted_by": submission_data.get('submitted_by'),
                            "event_title": event_title
                        })

        return render_template(
            'program_leader_dashboard.html',
            modules=modules_data,
            submissions=submissions.values(),
            submissions_by_date=submissions_by_date,  # New data passed for calendar grouping
            initials=user_initials
        )

    return redirect(url_for('sign_in_page'))




from flask import jsonify, request
from datetime import datetime
from flask import jsonify, request
from datetime import datetime

@app.route('/api/submissions', methods=['GET'])
def get_submissions():
    year = request.args.get('year', type=int)
    month = request.args.get('month', type=int)

    # Fetch submissions and group them by date
    submissions_by_date = {}
    submissions_ref = db.collection('submissions').stream()
    
    for submission in submissions_ref:
        data = submission.to_dict()
        submission_date = data.get('submission_date')  # Timestamp field
        event_id = data.get('event_id')
        
        if submission_date:
            # Convert submission_date (timestamp) to 'YYYY-MM-DD' format
            submission_date_obj = submission_date  # This should already be a timestamp object
            formatted_date = submission_date_obj.strftime('%Y-%m-%d')
            
            # Ensure we're within the requested year and month
            if submission_date_obj.year == year and submission_date_obj.month == month:
                # Fetch the event title using the event_id
                event_ref = db.collection('events').document(event_id).get()
                event_title = event_ref.to_dict().get('title', 'Unknown Event') if event_ref.exists else 'Unknown Event'
                
                # Group submissions by formatted_date
                if formatted_date not in submissions_by_date:
                    submissions_by_date[formatted_date] = []
                
                submissions_by_date[formatted_date].append({
                    'event_title': event_title,
                    'submitted_by': data.get('submitted_by'),
                    'file_url': data.get('file_url')
                })
    
    return jsonify(submissions_by_date)







# Protecting admin dashboard with login check
@app.route('/admin_dashboard')
@login_required
def admin_dashboard():
    if 'role' in session and session['role'] == 'admin':
        user_initials = (session['name'][0] + session['surname'][0]).upper()
        return render_template('admin_dashboard.html', initials=user_initials)
    return redirect(url_for('sign_in_page'))




@app.route('/add_module', methods=['POST'])
@login_required
def add_module():
    module_name = request.form.get('module_name')
    module_code = request.form.get('module_code')
    qualification = request.form.get('qualification')
    lecturer_email = request.form.get('lecturer_email')
    program_leader_email = request.form.get('program_leader_email')

    module_data = {
        'module_name': module_name,
        'module_code': module_code,
        'qualification': qualification,
        'lecturer_email': lecturer_email,
        'program_leader_email': program_leader_email,
        'events': []
    }

    db.collection('modules').add(module_data)
    return redirect(url_for('manage_user'))



@app.route('/manage_user', methods=['GET', 'POST'])
def manage_user():
    if 'role' in session and session['role'] == 'admin':
        user_initials = (session['name'][0] + session['surname'][0]).upper()
    users_ref = db.collection('users') 
    users = [user.to_dict() for user in users_ref.stream()]

    return render_template('manage_user.html', users=users, initials=user_initials)

from flask import Flask, request, redirect, render_template, url_for
from firebase_admin import firestore, auth

# Initialize Firebase Firestore
db = firestore.client()
import re

@app.route('/add_user', methods=['POST'])
def add_user():
    name = request.form['name']
    surname = request.form['surname']
    email = request.form['email']
    password = request.form['password']
    role = request.form['role']
    

    # Check if the email ends with @ump.ac.za
    if not email.endswith('@ump.ac.za'):
        return render_template('manage_user.html', message='Email must end with @ump.ac.za')

    # Strong password validation
    password_pattern = r"^(?=.*[A-Z])(?=.*[a-z])(?=.*\d)(?=.*[@$!%*?&])[A-Za-z\d@$!%*?&]{8,}$"
    if not re.match(password_pattern, password):
        return render_template(
            'manage_user.html',
            message='Password must be at least 8 characters long, include an uppercase letter, a lowercase letter, a number, and a special character.'
        )

    try:
        # Check how many users with this email already exist in Firestore
        user_entries = db.collection('users').where('email', '==', email).stream()
        user_count = sum(1 for _ in user_entries)

        if user_count >= 3:
            return render_template('manage_user.html', message='User with this email has already been added 3 times.')

        # If it's the first user, register it with Firebase Authentication
        if user_count == 0:
            auth.create_user(
                email=email,
                password=password
            )

        # Add user data to Firestore, allowing duplicates
        db.collection('users').add({
            'name': name,
            'surname': surname,
            'email': email,
            'role': role,
            
            'is_approved': True,  # Automatically approved
        })

        return redirect(url_for('account'))

    except Exception as e:
        return render_template('account.html', message=str(e))

@app.route('/delete_user', methods=['POST'])
def delete_user():
    email = request.form['email']
    role = request.form['role']  # Get the role from the form

    try:
        # Delete the specific Firestore document based on email and role
        user_documents = db.collection('users').where('email', '==', email).where('role', '==', role).stream()
        for doc in user_documents:
            db.collection('users').document(doc.id).delete()

        # Check if there are other Firestore documents with the same email
        remaining_users = db.collection('users').where('email', '==', email).stream()
        if not any(remaining_users):  # If no more documents exist for the email
            try:
                user = auth.get_user_by_email(email)
                auth.delete_user(user.uid)  # Delete the user from Firebase Auth
            except Exception:
                pass  # Ignore if the user is already deleted or doesn't exist in Auth

        return redirect(url_for('account'))

    except Exception as e:
        return render_template('account.html', message=str(e))




@app.route('/account')
def account():
    if 'role' in session and session['role'] == 'admin':
     user_initials = (session['name'][0] + session['surname'][0]).upper()
    # Fetch users from Firestore
    users_ref = db.collection('users')
    users = users_ref.stream()
    user_data = [
        {'id': user.id, **user.to_dict()}
        for user in users
    ]
    return render_template('account.html', users=user_data, initials=user_initials )



# Other routes (my_courses, profile, etc.)
@app.route('/my_courses_lecture')
@login_required
def my_courses_lecture():
    user_email = session.get('email')
    modules = db.collection('modules').where('lecturer_email', '==', user_email).stream()
    modules_data = [{'id': module.id, **module.to_dict()} for module in modules]
    user_initials = (session['name'][0] + session['surname'][0]).upper()

    return render_template('my_courses_lecture.html', modules=modules_data, initials=user_initials)


@app.route('/my_courses_leader')
@login_required
def my_courses_leader():
    user_email = session.get('email')
    modules = db.collection('modules').where('program_leader_email', '==', user_email).stream()
    modules_data = [{'id': module.id, **module.to_dict()} for module in modules]

    # Calculate user initials
    user_initials = (session['name'][0] + session['surname'][0]).upper()

    return render_template('my_courses_leader.html', modules=modules_data, initials=user_initials)

@app.route('/profile_lecture')
@login_required
def profile_lecture():
    if 'role' in session:
        user_id = session.get('user_id')  # Use an ID or email to fetch user data if needed
        user_data = db.collection('users').document(user_id).get().to_dict()

        # Set values in session or directly pass to the template
        session['qualification'] = user_data.get('qualification', 'N/A')
        session['access_time'] = user_data.get('access_time', 'N/A')  # Make sure to set access time when user logs in

        user_initials = (session['name'][0] + session['surname'][0]).upper()
        return render_template(
            'profile_lecture.html',
            initials=user_initials,
            role=session['role'],
            qualification=session['qualification'],
            access_time=session['access_time']
        )
    return redirect(url_for('sign_in_page'))

@app.route('/profile_leaders')
@login_required
def profile_leaders():
    if 'role' in session:
        user_id = session.get('user_id')  # Use an ID or email to fetch user data if needed
        user_data = db.collection('users').document(user_id).get().to_dict()

        # Set values in session or directly pass to the template
        session['qualification'] = user_data.get('qualification', 'N/A')
        session['access_time'] = user_data.get('access_time', 'N/A')  # Make sure to set access time when user logs in

        user_initials = (session['name'][0] + session['surname'][0]).upper()
        return render_template(
            'profile_leaders.html',
            initials=user_initials,
            role=session['role'],
            qualification=session['qualification'],
            access_time=session['access_time']
        )

    return redirect(url_for('sign_in_page'))

@app.route('/admin_profile')
@login_required
def admin_profile():
    if 'role' in session:
        user_id = session.get('user_id')  # Use an ID or email to fetch user data if needed
        user_data = db.collection('users').document(user_id).get().to_dict()

        # Set values in session or directly pass to the template
        session['qualification'] = user_data.get('qualification', 'N/A')
        session['access_time'] = user_data.get('access_time', 'N/A')  # Make sure to set access time when user logs in

        user_initials = (session['name'][0] + session['surname'][0]).upper()
        return render_template(
            'admin_profile.html',
            initials=user_initials,
            role=session['role'],
            qualification=session['qualification'],
            access_time=session['access_time']
        )

    return redirect(url_for('sign_in_page'))






# Forgot password route
@app.route('/forgot_pass', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        email = request.form['email']

        try:
            url = f'https://identitytoolkit.googleapis.com/v1/accounts:sendOobCode?key={FIREBASE_WEB_API_KEY}'
            payload = {
                "requestType": "PASSWORD_RESET",
                "email": email
            }
            response = requests.post(url, json=payload)
            response_data = response.json()

            if 'error' in response_data:
                message = response_data['error']['message']
            else:
                message = 'A password reset email has been sent to your email address.'
        except Exception as e:
            message = str(e)
        return render_template('forgot_pass.html', message=message)

    return render_template('forgot_pass.html')

 



# Admin modify page route
 
# Profile leaders route

# Add event route
from datetime import datetime
import requests
from flask import request, redirect, url_for

from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime, timedelta

# Initialize the scheduler
scheduler = BackgroundScheduler()
scheduler.start()

@app.route('/add_event', methods=['POST'])
def add_event():
    title = request.form['title']
    description = request.form['description']
    closing_date_str = request.form.get('closing_date')
    module_id = request.form['module_id']
    
    try:
        # Convert closing date to datetime for validation and formatting
        closing_date = datetime.strptime(closing_date_str, '%Y-%m-%d')
    except ValueError:
        print(f"Invalid closing date format: {closing_date_str}")
        return "Invalid closing date format. Please use YYYY-MM-DD.", 400

    # Store event details in Firestore
    event_data = {
        'title': title,
        'description': description,
        'closing_date': closing_date.strftime('%Y-%m-%d'),  # Save as string
        'module_id': module_id,
    }
    event_ref = db.collection('events').add(event_data)

    # Fetch module details
    module_doc = db.collection('modules').document(module_id).get()
    if not module_doc.exists:
        print(f"Module with ID {module_id} does not exist in Firestore.")
        return "Module not found.", 404

    module = module_doc.to_dict()
    module_name = module.get('module_name', 'Unknown Module')
    module_code = module.get('module_code', 'Unknown Code')
    lecturer_email = module.get('lecturer_email')

    # Debugging output
    print(f"Module ID: {module_id}, Name: {module_name}, Code: {module_code}")
    print(f"Lecturer Email: {lecturer_email}")

    # Send notification email if lecturer email exists
    if lecturer_email:
        try:
            print("Sending notification email...")
            send_event_notification_email(
                lecturer_email=lecturer_email,
                module_code=module_code,
                module_name=module_name,
                event_name=title,
                closing_date=closing_date.strftime('%Y-%m-%d')
            )
            print("Notification email sent successfully.")

            # Schedule reminders
            schedule_2_min_reminders(lecturer_email, module_code, module_name, title, closing_date)
        except Exception as e:
            print(f"Error sending notification email: {e}")

    return redirect(url_for('view_module', module_id=module_id))

def schedule_2_min_reminders(lecturer_email, module_code, module_name, event_name, closing_date):
    """Schedules reminders every 2 minutes until the closing date."""
    now = datetime.now()
    while now < closing_date:
        next_reminder = now + timedelta(minutes=2)  # Change interval to 2 minutes

        # Add a job to the scheduler for each reminder
        scheduler.add_job(
            func=send_reminder_email,
            args=[lecturer_email, module_code, module_name, event_name, closing_date.strftime('%Y-%m-%d')],
            trigger='date',
            run_date=next_reminder
        )
        now = next_reminder


def send_reminder_email(lecturer_email, module_code, module_name, event_name, closing_date):
    """Sends a reminder email."""
    subject = f"Reminder: Submission Slot for {event_name} in {module_code}:{module_name}"
    body = f"""
    Dear Lecturer,

    This is a reminder about the submission slot for {event_name} 
    in {module_code}:{module_name}. The closing date is {closing_date}.

    Please ensure you complete your tasks on time.

    Regards,
    Program Leader
    """

    email_data = {
        "email": lecturer_email,
        "message": body,
        "subject": subject,
        "validation": "Secure123"
    }

    try:
        response = requests.post(
            'https://ai.nextgensell.com/send-email',
            json=email_data,
            headers={'Content-Type': 'application/json'}
        )

        if response.status_code == 200:
            print("Reminder email sent successfully.")
        else:
            print(f"Failed to send reminder email. Response: {response.text}")
    except requests.RequestException as e:
        print(f"Error sending reminder email: {e}")

def send_event_notification_email(lecturer_email, module_code, module_name, event_name, closing_date):
    """Sends the initial notification email."""
    subject = f"New Submission Slot Added: {event_name} in {module_code}:{module_name}"
    body = f"""
    Dear Lecturer,

    A new submission slot for {event_name} 
    has been added to {module_code}:{module_name}.
    Closing Date:{closing_date}

    Please review this event on your dashboard.

    Regards,  
    Program Leader
    """

    email_data = {
        "email": lecturer_email,
        "message": body,
        "subject": subject,
        "validation": "Secure123"
    }

    try:
        response = requests.post(
            'https://ai.nextgensell.com/send-email',
            json=email_data,
            headers={'Content-Type': 'application/json'}
        )

        if response.status_code == 200:
            print("Email sent successfully.")
        else:
            print(f"Failed to send email. Response: {response.text}")
    except requests.RequestException as e:
        print(f"Error while sending email: {e}")



@app.route('/event_details/<event_id>')
def event_details(event_id):
    user_initials = (session.get('name', '')[0] + session.get('surname', '')[0]).upper()
    
    # Retrieve event details
    event_ref = db.collection('events').document(event_id)
    event = event_ref.get()

    if event.exists:
        event_data = event.to_dict()
        
        # Get module details
        module_id = event_data.get('module_id')
        module_data = db.collection('modules').document(module_id).get().to_dict() if module_id else None

        # Fetch submissions related to the event
        submissions = []
        submissions_ref = db.collection('submissions').where('event_id', '==', event_id).stream()
        for submission in submissions_ref:
            submission_data = submission.to_dict()
            submission_data['event_title'] = event_data.get('title')
            submission_data['event_id'] = event_id
            submissions.append(submission_data)

        # Render template with data
        return render_template(
            'event_details.html',
            event=event_data,
            module=module_data,
            submissions=submissions,
            initials=user_initials
        )
    else:
        # Event not found
        return render_template('error.html', message="Event not found.")











@app.route('/view_module_l/<module_id>')
def view_module_l(module_id):
    user_initials = (session['name'][0] + session['surname'][0]).upper()

    # Retrieve events associated with the module
    events_ref = db.collection('events').where('module_id', '==', module_id)
    events = [
        {'id': event.id, **event.to_dict()} for event in events_ref.stream()
    ]

    # Retrieve module details by module_id
    module = db.collection('modules').document(module_id).get().to_dict()

    if module:
        # Render the template with module details, events, event_ids, and user initials
        return render_template(
            'view_module_l.html', 
            events=events, 
            module=module, 
            module_id=module_id, 
            initials=user_initials
        )
    else:
        return "Module not found", 404


# View module route
@app.route('/view_module/<module_id>')
@login_required
def view_module(module_id):
    user_initials = (session['name'][0] + session['surname'][0]).upper()



    module = db.collection('modules').document(module_id).get().to_dict()
    if module:


        return render_template('view_module.html', module=module, module_id=module_id, initials=user_initials)
    else:
        return "Module not found", 404

@app.route('/delete_event/<module_id>/<event_id>', methods=['POST'])
def delete_event(module_id, event_id):
    # Reference to the events collection
    event_ref = db.collection('events').document(event_id)
    
    # Delete the event document
    event_ref.delete()

    # Redirect to the view_event page, filtered by module_id
    return redirect(url_for('view_event', module_id=module_id))


@app.route('/view_event/<module_id>')
def view_event(module_id):
    user_initials = (session.get('name', '')[0] + session.get('surname', '')[0]).upper()
    events_ref = db.collection('events').where('module_id', '==', module_id)  # Filter by module_id
    events = []

    for event_doc in events_ref.stream():
        event_data = event_doc.to_dict()
        event_data['id'] = event_doc.id  # Include the document ID as 'id'

        # Retrieve module data based on module_id in the event
        module_ref = db.collection('modules').document(module_id)
        module_doc = module_ref.get()
        if module_doc.exists:
            module_data = module_doc.to_dict()
            event_data['module_name'] = module_data.get('module_name', 'Unknown')
            event_data['module_code'] = module_data.get('module_code', 'Unknown')
        else:
            event_data['module_name'] = 'Unknown Module'
            event_data['module_code'] = 'N/A'

        events.append(event_data)

    return render_template('view_event.html', events=events, initials=user_initials, module_id=module_id)





@app.route('/admin_submit/<module_id>/<event_id>')
def admin_submit(module_id, event_id):
    
    # Fetch event title (optional if needed for display)
    event = db.collection('events').document(event_id).get()
    event_title = event.to_dict().get('title') if event.exists else "Event"

    return render_template('admin_submission.html', module_id=module_id, event_id=event_id, event_title=event_title,)





@app.route('/submit_document/<module_id>/<event_id>')
def submit_document(module_id, event_id):
    user_initials = (session['name'][0] + session['surname'][0]).upper()
    # Fetch event title (optional if needed for display)
    event = db.collection('events').document(event_id).get()
    event_title = event.to_dict().get('title') if event.exists else "Event"

    return render_template('submission.html', module_id=module_id, event_id=event_id, event_title=event_title, initials=user_initials)
@app.route('/process_submission/<module_id>/<event_id>', methods=['POST'])
def process_submission(module_id, event_id):
    user_id = session.get('user_id')
    file = request.files['document']

    # Generate unique file path and upload document
    file_path = f"submissions/{module_id}/{event_id}/{uuid.uuid4()}_{file.filename}"
    bucket = storage.bucket()
    blob = bucket.blob(file_path)
    blob.upload_from_file(file)
    file_url = blob.public_url

    # Check if a submission for this event already exists for the user
    submissions_ref = db.collection('submissions') \
                        .where('event_id', '==', event_id) \
                        .where('submitted_by', '==', user_id) \
                        .limit(1) \
                        .stream()

    existing_submission = next((sub for sub in submissions_ref), None)

    # Prepare submission data
    submission_data = {
        'event_id': event_id,
        'file_url': file_url,
        'submitted_by': user_id,
        'submission_date': firestore.SERVER_TIMESTAMP,
        'module_id': module_id,
    }

    if existing_submission:
        # Update the existing submission
        db.collection('submissions').document(existing_submission.id).update(submission_data)
    else:
        # Add a new submission if none exists
        db.collection('submissions').add(submission_data)

    # Fetch program leader's email and module details
    module_doc = db.collection('modules').document(module_id).get()
    if module_doc.exists:
        module_data = module_doc.to_dict()
        program_leader_email = module_data.get('program_leader_email')
        module_code = module_data.get('module_code')  # Correct field for module code
        module_name = module_data.get('module_name')  # Correct field for module name
        event_title = module_data.get('event_title', 'Event')

        if program_leader_email:
            send_submission_notification_email(
                program_leader_email,
                module_name,
                module_code,
                event_title,
                user_id
            )

    return redirect(url_for('view_module_l', module_id=module_id))


def send_submission_notification_email(program_leader_email, module_name, module_code, event_name, lecturer_email):
    """Sends email notification to the program leader after submission."""
    subject = f"New Submission for Event: {event_name}"
    body = f"""
    Dear Program Leader,

    A new submission has been made  in module {module_code}:{module_name} 
    
    
    Please review the submission on the  dashboard.

    Regards,
    QMS System
    """

    email_data = {
        "email": program_leader_email,
        "message": body,
        "subject": subject,
        "validation": "Secure123"
    }

    try:
        response = requests.post(
            'https://ai.nextgensell.com/send-email',
            json=email_data,
            headers={'Content-Type': 'application/json'}
        )

        if response.status_code == 200:
            print("Notification email sent to program leader successfully.")
        else:
            print(f"Failed to send email. Response: {response.text}")
    except requests.RequestException as e:
        print(f"Error while sending email: {e}")




@app.route('/process_sub/<module_id>/<event_id>', methods=['POST'])
def process_sub(module_id, event_id):
    user_id = session.get('user_id')
    file = request.files['document']

    # Generate unique file path and upload document
    file_path = f"submissions/{module_id}/{event_id}/{uuid.uuid4()}_{file.filename}"
    bucket = storage.bucket()
    blob = bucket.blob(file_path)
    blob.upload_from_file(file)
    file_url = blob.public_url

    # Check if a submission for this event already exists for the user
    submissions_ref = db.collection('submissions') \
                        .where('event_id', '==', event_id) \
                        .where('submitted_by', '==', user_id) \
                        .limit(1) \
                        .stream()

    existing_submission = next((sub for sub in submissions_ref), None)

    # Prepare submission data
    submission_data = {
        'event_id': event_id,
        'file_url': file_url,
        'submitted_by': user_id,
        'submission_date': firestore.SERVER_TIMESTAMP,
        'module_id': module_id,
    }

    if existing_submission:
        # Update the existing submission
        db.collection('submissions').document(existing_submission.id).update(submission_data)
    else:
        # Add a new submission if none exists
        db.collection('submissions').add(submission_data)

    return redirect(url_for('view_sub', module_id=module_id))

@app.route('/view_submission/<module_id>/<event_id>')
def view_submission(module_id, event_id):
    user_initials = (session['name'][0] + session['surname'][0]).upper()
    # Retrieve submission for the current user and specified event
    submission_ref = db.collection('submissions') \
                       .where('module_id', '==', module_id) \
                       .where('event_id', '==', event_id) \
                       .where('submitted_by', '==', session.get('user_id')) \
                       .limit(1).stream()

    submission = next((sub.to_dict() for sub in submission_ref), None)

    if submission:
        # Fetch event title (optional, for better display)
        event = db.collection('events').document(event_id).get()
        event_title = event.to_dict().get('title') if event.exists else "Event"
        submission['event_title'] = event_title
    else:
        submission = None  # No submission found

    return render_template('view_submission.html', module_id=module_id, event_id=event_id, submission=submission,initials=user_initials)


 

@app.route('/view_submissions/<module_id>')
@login_required
def view_submissions(module_id):
    user_initials = (session['name'][0] + session['surname'][0]).upper()

    # Retrieve module details
    module_ref = db.collection('modules').document(module_id)
    module = module_ref.get().to_dict()
    module_name = module.get('module_name', 'Unknown Module')
    module_code = module.get('module_code', 'N/A')

    # Get all events for the module
    events_ref = db.collection('events').where('module_id', '==', module_id).stream()
    event_details = {event.id: event.to_dict().get('title', 'Untitled Event') for event in events_ref}

    # Retrieve all submissions for events in this module
    submissions = []
    for event_id, event_title in event_details.items():
        submissions_ref = db.collection('submissions').where('event_id', '==', event_id).stream()
        for submission in submissions_ref:
            submission_data = submission.to_dict()
            submission_data['event_title'] = event_title  # Include event title
            
            # Fetch the user who made the submission
            user_id = submission_data.get('submitted_by')
            if user_id:
                user_ref = db.collection('users').document(user_id).get()
                if user_ref.exists:
                    user_data = user_ref.to_dict()
                    submission_data['submitted_by_email'] = user_data.get('email', 'Unknown Email')
                else:
                    submission_data['submitted_by_email'] = 'Unknown Email'
            else:
                submission_data['submitted_by_email'] = 'Unknown Email'
                
            submissions.append(submission_data)

    # Pass data to the template
    return render_template(
        'leader_submissions.html',
        submissions=submissions,
        initials=user_initials,
        module_id=module_id,
        module_name=module_name,
        module_code=module_code
    )


 

 


 

 









@app.route('/sign_up_page')
def sign_up_page():
    return render_template('signup.html')

@app.route('/sign_in_page')
def sign_in_page():
    return render_template('signin.html')

if __name__ == '__main__':
    app.run(debug=True)
