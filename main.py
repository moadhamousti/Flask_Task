from flask import Flask, render_template, jsonify, request, redirect, url_for,session
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
# from google.oauth2 import id_token
# from google.auth.transport import requests
from urllib.parse import urlencode
from sqlalchemy import Table, Column, Integer, ForeignKey
from sqlalchemy.orm import relationship
from flask_socketio import SocketIO, emit
import os
from werkzeug.utils import secure_filename
import base64
from flask_sse import sse
from flask_wtf.file import FileField
from uuid import uuid1
from flask_wtf import CSRFProtect, csrf
from flask_wtf.csrf import CSRFProtect, generate_csrf
from datetime import datetime, timedelta
from sqlalchemy import func
import json
from collections import Counter


















app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///data.db'
app.config['SECRET_KEY'] = 'thisisasecretkey'
db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'
socketio = SocketIO(app)

app.config['UPLOAD_FOLDER'] = r'C:\Users\hp\Desktop\trr\static\images'

# BLUEPRINT 
app.register_blueprint(sse, url_prefix='/stream')




friendship = db.Table(
    'friendship',
    db.Column('user_id', db.Integer, db.ForeignKey('user.id'), primary_key=True),
    db.Column('friend_id', db.Integer, db.ForeignKey('user.id'), primary_key=True)
)


class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(80), nullable=False)
    fullname = db.Column(db.String(120), nullable=True)
    profile_picture = db.Column(db.String(), nullable=True)
    friends = relationship('User',
                           secondary='friendship',
                           primaryjoin=('User.id == friendship.c.user_id'),
                           secondaryjoin=('User.id == friendship.c.friend_id'),
                           backref='friendships')

class Task(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    task = db.Column(db.String(100), nullable=False)
    color = db.Column(db.String(7), nullable=True)
    start_date = db.Column(db.Date, nullable=True)
    end_date = db.Column(db.Date, nullable=True)

    def __repr__(self):
        return f"<Task {self.id}>"




class Message(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    sender = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    recipient = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    message = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    def __repr__(self):
        return f"<Message {self.id}>"







@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


@app.route('/')
def index():
    return render_template('index.html')





# ===========================================================================
# ===========================================================================




@app.route('/sso/')
def sso():
    return render_template('sso.html')



# @app.route('/signup_with_gmail', methods=['GET'])
# def signup_with_gmail():
#     # Render a template with a Gmail signup button
#     return render_template('gmail_signup.html')



# @app.route('/authorize_google')
# def authorize_google():
#     # Generate a Google OAuth 2.0 authorization URL
#     google_auth_url = "https://accounts.google.com/o/oauth2/v2/auth"
#     google_auth_params = {
#         "client_id": "698145444255-hje1lp1hvveag73bpgo2orhnf31int19.apps.googleusercontent.com",
#         "redirect_uri": url_for("google_callback", _external=True),
#         "response_type": "code",
#         "scope": "email profile",
#     }

#     # Append the parameters to the authorization URL
#     google_auth_url += '?' + urlencode(google_auth_params)

#     # Redirect the user to the Google OAuth 2.0 authorization URL
#     return redirect(google_auth_url)


# @app.route('/google_callback')
# def google_callback():
#     # Obtain the authorization code from the callback request
#     auth_code = request.args.get('code')

#     # Exchange the authorization code for an access token
#     token_url = "https://oauth2.googleapis.com/token"
#     token_params = {
#         "code": auth_code,
#         "client_id": "698145444255-hje1lp1hvveag73bpgo2orhnf31int19.apps.googleusercontent.com",
#         "redirect_uri": "http://localhost:5000/authorize_google",
#         "redirect_uri": url_for("google_callback", _external=True),
#         "grant_type": "authorization_code",
#     }
#     response = requests.post(token_url, data=token_params)
#     token_data = response.json()
#     access_token = token_data.get('access_token')

#     # Use the access token to obtain user information
#     user_info_url = "https://www.googleapis.com/oauth2/v1/userinfo"
#     headers = {"Authorization": "Bearer " + access_token}
#     response = requests.get(user_info_url, headers=headers)
#     user_info = response.json()

#     # Extract the relevant user information
#     email = user_info.get('email')
#     full_name = user_info.get('name')

#     # Check if the user already exists in the database
#     existing_user = User.query.filter_by(email=email).first()
#     if existing_user:
#         # User already exists, log them in
#         login_user(existing_user)
#         return redirect(url_for('dashboard'))
#     else:
#         # User doesn't exist, create a new user with Gmail information
#         new_user = User(fullname=full_name, email=email, password='')
#         db.session.add(new_user)
#         db.session.commit()
#         login_user(new_user)
#         return redirect(url_for('dashboard'))

# --------------------------------------------------------
        

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        user = User.query.filter_by(email=email).first()

        if user and user.password == password:
            login_user(user)
            return redirect(url_for('dashboard'))
        else:
            error = 'Invalid email or password'
            return render_template('login.html', error=error)

    return render_template('login.html')


@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        fullname = request.form['fullname']
        email = request.form['email']
        password = request.form['password']
        user = User.query.filter_by(email=email).first()

        if user:
            return render_template('signup.html', error='Email already exists')

        new_user = User(fullname=fullname, email=email, password=password)
        db.session.add(new_user)
        db.session.commit()
        login_user(new_user)
        return redirect(url_for('dashboard'))

    return render_template('signup.html')


@app.route('/logout', methods=['GET'])
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

# ====================================================================================================
# ====================================================================================================
# ====================================================================================================
# dashboard
@app.route('/dashboard')
@login_required
def dashboard():
    today = datetime.now().date()
    last_week = today - timedelta(days=7)
    last_month = today - timedelta(days=30)
    
    task_count = Task.query.filter(
        Task.user_id == current_user.id
    ).count()

    new_added_task_count = Task.query.filter(
        Task.user_id == current_user.id,
        Task.start_date >= last_week,
        Task.end_date < datetime.now().date()
    ).count()

    finished_task_count = Task.query.filter(
        Task.user_id == current_user.id,
        Task.end_date < today
    ).count()

    next_task = Task.query.filter(
        Task.user_id == current_user.id,
        Task.end_date >= today
    ).order_by(Task.start_date.asc()).first()

    # Fetch the previous task for the user
    previous_task = Task.query.filter(
        Task.user_id == current_user.id,
        Task.end_date < today
    ).order_by(Task.end_date.desc()).first()

    completed_tasks_data = get_completed_tasks_data(current_user.id)

    # Convert the data to JSON format
    completed_tasks_data_json = json.dumps(completed_tasks_data)

    user = User.query.get(current_user.id)
    friends = list(user.friends)

    completed_percentage = int((new_added_task_count / task_count) * 100) if new_added_task_count > 0 else 0
    new_percentage = int((new_added_task_count / 7) * 100) if new_added_task_count > 0 else 0

    start_dates_data = get_task_count_by_start_dates(current_user.id, today, last_month)

    timeline_data = get_timeline_data(min_duration=2) 



    return render_template('dashboard.html', timeline_data = timeline_data ,user=current_user, task_count=task_count, 
                           new_added_task_count=new_added_task_count, finished_task_count=finished_task_count, 
                           completed_percentage=completed_percentage, new_percentage=new_percentage, 
                           completed_tasks_data=completed_tasks_data_json, next_task=next_task,
                           previous_task=previous_task, friends=friends, current_user=current_user,
                           start_dates_data=start_dates_data)


def get_completed_tasks_data(user_id):
    # Query the database to retrieve the completed tasks data
    completed_tasks = Task.query.filter(
        Task.user_id == user_id,
        Task.end_date < datetime.now().date()
    ).all()

    # Prepare the data in the required format
    completed_tasks_data = {}
    for task in completed_tasks:
        date_str = task.end_date.strftime('%Y-%m-%d')
        if date_str in completed_tasks_data:
            completed_tasks_data[date_str] += 1
        else:
            completed_tasks_data[date_str] = 1

    # Convert the data to a list of objects
    completed_tasks_list = [{'date': date, 'count': count} for date, count in completed_tasks_data.items()]

    return completed_tasks_list


def get_task_count_by_start_dates(user_id, today, last_month):
    # Query the database to retrieve the tasks
    tasks = Task.query.filter(
        Task.user_id == user_id,
        Task.start_date >= last_month,
        Task.end_date < today
    ).all()

    # Count the tasks by start dates
    task_count_by_start_dates = Counter(task.start_date for task in tasks)

    # Prepare the data in the required format
    start_dates_data = [{'date': date.strftime('%Y-%m-%d'), 'count': count} for date, count in task_count_by_start_dates.items()]

    return start_dates_data


def get_timeline_data():
    # Query the database or perform any necessary data processing to retrieve the timeline data
    tasks = Task.query.filter(
        Task.user_id == current_user.id
    ).all()

    timeline_data = []
    for task in tasks:
        timeline_data.append(task.start_date.strftime('%Y-%m-%d'))

    return timeline_data

def get_timeline_data(min_duration):
    # Query the database or perform any necessary data processing to retrieve the timeline data
    tasks = Task.query.filter(
        Task.user_id == current_user.id
    ).all()

    timeline_data = []
    for task in tasks:
        duration = (task.end_date - task.start_date).days
        if duration >= min_duration:
            timeline_data.append({
                'task': task.task,
                'start_date': task.start_date.strftime('%Y-%m-%d'),
                'end_date': task.end_date.strftime('%Y-%m-%d')
            })

    return timeline_data
# ===========================================================================================
# =============================================================================================


@app.route('/dashboard/add_user', methods=['GET', 'POST'])
@login_required
def add_user():
    if request.method == 'POST':
        email = request.form['email']
        user = User.query.filter_by(email=email).first()
        if user:
            current_user.friends.append(user)
            db.session.commit()

            # Emit a Socket.IO event to notify the friend
            socketio.emit('friend_added', {'friend': current_user.fullname}, room=user.id)

            return redirect(url_for('dashboard'))
        else:
            error = 'User not found'
            return render_template('add_user.html', error=error)

    friends = current_user.friends
    return render_template('add_user.html', friends=friends,user=current_user)


@app.route('/dashboard/add_user/remove_friend', methods=['POST'])
@login_required
def remove_friend():
    email = request.form['email']
    friend = User.query.filter_by(email=email).first()
    if friend:
        current_user.friends.remove(friend)
        db.session.commit()  # Commit the changes to the database
        session['friends'] = [friend.email for friend in current_user.friends]  # Update friends in session
        return jsonify({'message': f'Friend {friend.fullname} removed successfully'})
    else:
        return jsonify({'message': 'Friend not found'})




# @app.route('/dashboard/add_user/send_message', methods=['POST'])
# def send_message(data):
#     recipient_email = data['recipient_email']
#     message = data['message']

#     # Store the message in the database
#     # ...

#     # Emit the message to the recipient
#     emit('receive_message', {
#         'sender_email': current_user.email,
#         'message': message,
#         'recipient_email': recipient_email
#     }, broadcast=True)



# ===================================================================================================================
# ===================================================================================================================
# PROFIL 



@app.route('/dashboard/profil', methods=['GET', 'POST'])
@login_required
def profil():
    if request.method == 'POST':
        # Update user's information
        user = current_user

        # Check if the 'name' field exists in the request
        if 'name' in request.form:
            user.fullname = request.form['name']
        user.email = request.form['email']
        user.password = request.form['password']

        # Save the uploaded profile picture, if provided
        if 'profile_picture' in request.files:
            profile_picture = request.files['profile_picture']
            if profile_picture.filename != '':
                filename = secure_filename(profile_picture.filename)
                pic_name = str(uuid1()) + "_" + filename
                profile_picture.save(os.path.join(app.config['UPLOAD_FOLDER'], pic_name))
                user.profile_picture = pic_name

        db.session.commit()
        return redirect(url_for('profil'))

    # Render the template with the user's information
    default_profile_picture = 'images/Def.png'  # Set the filename of the default profile picture
    return render_template('profil.html', user=current_user, profile_picture=current_user.profile_picture or default_profile_picture)


    





    



# =============================================================================
# =============================================================================
# calendar

@app.route('/dashboard/calendar', methods=['GET', 'POST'])
@login_required
def calendar():
    if request.method == 'POST':
        task_name = request.form['task']
        color = request.form['color']  # Add this line to get the color value
        start_date = datetime.strptime(request.form['start_date'], '%Y-%m-%d').date()
        end_date = datetime.strptime(request.form['end_date'], '%Y-%m-%d').date()
        user_id = current_user.id

        task = Task(task=task_name, color=color, start_date=start_date, end_date=end_date, user_id=user_id)

        db.session.add(task)
        db.session.commit()

        return redirect(url_for('calendar'))

    tasks = Task.query.filter_by(user_id=current_user.id).all()
    return render_template('calendar.html', user=current_user, tasks=tasks)



@app.route('/dashboard/calendar/delete/<int:task_id>', methods=['DELETE'])
@login_required
def delete_task(task_id):
    task = Task.query.get_or_404(task_id)

    # Check if the task belongs to the current user
    if task.user_id != current_user.id:
        abort(403)  # Return a forbidden error if the task doesn't belong to the user

    db.session.delete(task)
    db.session.commit()

    # Return a JSON response indicating the success of the deletion
    return jsonify({'success': True})




# =================================================================================
# ================================================================================

# settings 

@app.route('/dashboard/settings')
@login_required
def settings():
    return render_template('settings.html',user=current_user)



@app.route('/dashboard/stats', methods=['GET', 'POST'])
@login_required
def stats():
    limit = 3  # Set the desired limit for the number of repeated tasks
    repeated_tasks = fetch_repeated_tasks_from_database(current_user.id, limit)
    
    return render_template('stats.html', user=current_user, repeated_tasks=repeated_tasks)


def fetch_repeated_tasks_from_database(user_id, limit):
    task_counts = db.session.query(Task.task, func.count(Task.task).label('repeatCount')).filter_by(user_id=user_id).group_by(Task.task).order_by(
        func.count(Task.task).desc()).limit(limit).all()
    repeated_tasks = [{'taskName': task_name, 'repeatCount': repeat_count} for task_name, repeat_count in task_counts]
    return repeated_tasks







if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    socketio.run(app, debug=True,host='0.0.0.0')
