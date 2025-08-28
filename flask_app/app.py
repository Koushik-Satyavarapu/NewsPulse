from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure, PyMongoError, ServerSelectionTimeoutError
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
import requests
import os
import logging
from bson.objectid import ObjectId
import socket
from datetime import datetime
from dateutil import parser
from authlib.integrations.flask_client import OAuth
from dotenv import load_dotenv
import os
load_dotenv()
client_id = os.getenv('GOOGLE_CLIENT_ID')
client_secret = os.getenv('GOOGLE_CLIENT_SECRET')
# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.secret_key = os.urandom(24)  # Or 'your_secret_key' for development

# OAuth setup for Google with OpenID Connect discovery
oauth = OAuth(app)
google = oauth.register(
    name='google',
    client_id=client_id,
    client_secret=client_secret,
    server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
    client_kwargs={
        'scope': 'openid profile email'
    },
    redirect_uri='http://127.0.0.1:5000/login/google/authorized'
)

# Verify templates exist
template_dir = os.path.join(os.path.dirname(__file__), 'templates')
required_templates = ['signup.html', 'login.html', 'dashboard.html', 'base.html', 'profile.html', 'home.html', 'analyze.html']
for template in required_templates:
    if not os.path.exists(os.path.join(template_dir, template)):
        logger.error(f"Template missing: {template}")
    else:
        logger.debug(f"Template found: {template}")

# Connect to MongoDB Atlas
try:
    client = MongoClient(
        'mongodb+srv://newspulse_user:CurBW0rHpZ3sOTKj@ac-97plfyc.oocp1sv.mongodb.net/newspulse_db?retryWrites=true&w=majority',
        serverSelectionTimeoutMS=30000,
        connectTimeoutMS=30000,
        socketTimeoutMS=30000
    )
    client.admin.command('ping')
    logger.info("Connected to MongoDB Atlas")
    db = client['newspulse_db']
except ServerSelectionTimeoutError as e:
    logger.error(f"MongoDB server selection failed: {str(e)}. Check cluster status or network settings.")
    raise Exception("Cannot connect to MongoDB Atlas. Server selection timeout.")
except ConnectionFailure as e:
    logger.error(f"MongoDB connection failed: {str(e)}. Check credentials or IP whitelist.")
    raise Exception("Cannot connect to MongoDB Atlas. Check connection string and network settings.")
except Exception as e:
    logger.error(f"Unexpected MongoDB connection error: {str(e)}")
    raise Exception("Unexpected error connecting to MongoDB Atlas.")

# Flask-Login setup
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

class User(UserMixin):
    def __init__(self, id):
        self.id = id

@login_manager.user_loader
def load_user(user_id):
    try:
        user = db.users.find_one({'_id': ObjectId(user_id)})
        if user:
            logger.debug(f"Loaded user: {user_id}")
            return User(str(user['_id']))
        logger.warning(f"User not found: {user_id}")
        return None
    except Exception as e:
        logger.error(f"Error loading user: {str(e)}")
        return None

# Custom Jinja2 filter for formatting ISO8601 dates
def format_datetime(value):
    try:
        dt = parser.parse(value)
        return dt.strftime('%b %d, %Y, %I:%M %p')
    except:
        return value

app.jinja_env.filters['datetimeformat'] = format_datetime

@app.route('/')
def home():
    logger.debug("Accessed home route")
    return render_template('home.html')

@app.route('/test')
def test():
    logger.debug("Accessing test route")
    return "Test route works!"

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    logger.debug("Accessing signup route")
    try:
        if request.method == 'POST':
            name = request.form.get('name')
            email = request.form.get('email')
            password = request.form.get('password')
            confirm_password = request.form.get('confirm_password')
            if not name or not email or not password or not confirm_password:
                flash('All fields are required')
                logger.warning("Signup failed: Missing fields")
                return redirect(url_for('signup'))
            if password != confirm_password:
                flash('Passwords do not match')
                logger.warning("Signup failed: Passwords do not match")
                return redirect(url_for('signup'))
            hashed_pw = generate_password_hash(password, method='pbkdf2:sha256')
            if db.users.find_one({'email': email}):
                flash('Email already exists')
                logger.warning(f"Signup failed: Email {email} already exists")
                return redirect(url_for('signup'))
            db.users.insert_one({'name': name, 'email': email, 'password': hashed_pw})
            flash('Signup successful! Please login.')
            logger.info(f"User {email} signed up successfully")
            return redirect(url_for('login'))
        return render_template('signup.html')
    except PyMongoError as e:
        flash(f'Database error: {str(e)}')
        logger.error(f"Signup database error: {str(e)}")
        return redirect(url_for('signup'))
    except Exception as e:
        flash('An unexpected error occurred during signup')
        logger.error(f"Unexpected signup error: {str(e)}")
        return redirect(url_for('signup'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    logger.debug("Accessing login route")
    try:
        if request.method == 'POST':
            email = request.form.get('email')
            password = request.form.get('password')
            if not email or not password:
                flash('Email and password are required')
                logger.warning("Login failed: Missing email or password")
                return redirect(url_for('login'))
            user = db.users.find_one({'email': email})
            if user and check_password_hash(user['password'], password):
                login_user(User(str(user['_id'])))
                logger.info(f"User {email} logged in successfully")
                return redirect(url_for('home'))
            flash('Invalid credentials')
            logger.warning(f"Login failed for {email}: Invalid credentials")
            return redirect(url_for('login'))
        return render_template('login.html')
    except PyMongoError as e:
        flash(f'Database error: {str(e)}')
        logger.error(f"Login database error: {str(e)}")
        return redirect(url_for('login'))
    except Exception as e:
        flash('An unexpected error occurred during login')
        logger.error(f"Unexpected login error: {str(e)}")
        return redirect(url_for('login'))

@app.route('/login/google')
def login_google():
    redirect_uri = url_for('authorized_google', _external=True)
    return google.authorize_redirect(redirect_uri)

@app.route('/login/google/authorized')
def authorized_google():
    token = google.authorize_access_token()
    resp = google.get('https://www.googleapis.com/userinfo/v2/me')
    user_info = resp.json()
    name = user_info.get('name')
    email = user_info.get('email')
    if not email:
        flash('Unable to fetch email from Google')
        return redirect(url_for('login'))
    user = db.users.find_one({'email': email})
    if not user:
        # Create new user if not exists
        db.users.insert_one({'name': name, 'email': email, 'password': ''})  # No password for Google users
        user = db.users.find_one({'email': email})
    login_user(User(str(user['_id'])))
    logger.info(f"User {email} logged in with Google")
    return redirect(url_for('home'))

@app.route('/logout')
@login_required
def logout():
    logger.debug("Accessing logout route")
    try:
        logout_user()
        flash('Logged out successfully')
        logger.info("User logged out")
        return redirect(url_for('login'))
    except Exception as e:
        flash('Error during logout')
        logger.error(f"Logout error: {str(e)}")
        return redirect(url_for('login'))

@app.route('/dashboard')
@login_required
def dashboard():
    logger.debug("Accessing dashboard route")
    try:
        return render_template('dashboard.html')
    except Exception as e:
        flash('Error loading dashboard')
        logger.error(f"Dashboard error: {str(e)}")
        return redirect(url_for('home'))

@app.route('/profile')
@login_required
def profile():
    logger.debug("Accessing profile route")
    try:
        user = db.users.find_one({'_id': ObjectId(current_user.id)})
        if user:
            return render_template('profile.html', username=user['name'], email=user['email'])
        flash('User data not found')
        logger.error(f"Profile error: User data not found for {current_user.id}")
        return redirect(url_for('dashboard'))
    except Exception as e:
        flash('Error loading profile')
        logger.error(f"Profile error: {str(e)}")
        return redirect(url_for('dashboard'))

@app.route('/profile/update', methods=['POST'])
@login_required
def update_profile():
    logger.debug("Accessing profile update route")
    try:
        data = request.get_json()
        new_username = data.get('username')
        new_email = data.get('email')
        if not new_email or not new_username:
            return jsonify({'success': False, 'message': 'All fields are required'}), 400
        user = db.users.find_one({'_id': ObjectId(current_user.id)})
        if user:
            update_data = {}
            if new_username != user['name']:
                update_data['name'] = new_username
            if new_email != user['email']:
                update_data['email'] = new_email
            if update_data:
                db.users.update_one({'_id': ObjectId(current_user.id)}, {'$set': update_data})
                logger.info(f"Profile updated for user {current_user.id}")
            return jsonify({'success': True})
        return jsonify({'success': False, 'message': 'User not found'}), 404
    except Exception as e:
        logger.error(f"Profile update error: {str(e)}")
        return jsonify({'success': False, 'message': 'An error occurred'}), 500

@app.route('/search', methods=['POST'])
@login_required
def search():
    logger.debug("Accessing search route")
    try:
        # Check if FastAPI service is reachable
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(2)
        result = sock.connect_ex(('127.0.0.1', 8000))
        sock.close()
        if result != 0:
            flash("News service is not running. Please start the news service and try again.")
            logger.error("FastAPI service unreachable on port 8000")
            return redirect(url_for('dashboard'))

        region = request.form.get('region', '')
        topic = request.form.get('topic', '')
        keyword = request.form.get('keyword', '')
        logger.debug(f"Search parameters: region={region}, topic={topic}, keyword={keyword}")
        response = requests.get('http://127.0.0.1:8000/fetch-news', params={'topic': topic, 'city': '', 'keyword': keyword, 'region': region}, timeout=10)
        response.raise_for_status()
        data = response.json()
        if 'error' in data:
            flash(f"Error fetching news: {data['error']}")
            logger.warning(f"Search failed: {data['error']}")
            return redirect(url_for('dashboard'))
        if not data.get('articles'):
            flash(data.get('message', 'No articles found for the given parameters.'))
            logger.warning("No articles returned from FastAPI")
            return redirect(url_for('dashboard'))
        logger.info("Search successful, rendering dashboard with data")
        return render_template('dashboard.html', data={
            'articles': data['articles'],
            'sentiments': data.get('sentiments', {}),
            'trends': data.get('trends', {}),
            'region': region,
            'topic': topic,
            'keyword': keyword
        })
    except requests.RequestException as e:
        flash("Unable to fetch news. Please ensure the news service is running and try again.")
        logger.error(f"Search request error: {str(e)}")
        return redirect(url_for('dashboard'))
    except Exception as e:
        flash(f"An unexpected error occurred during search: {str(e)}")
        logger.error(f"Unexpected search error: {str(e)}")
        return redirect(url_for('dashboard'))

@app.route('/analyze', methods=['GET', 'POST'])
@login_required
def analyze():
    logger.debug("Accessing analyze route")
    try:
        if request.method == 'POST':
            text = request.form.get('text')
            if not text:
                flash('Text input is required')
                logger.warning("Analyze failed: Missing text input")
                return redirect(url_for('analyze'))
            response = requests.post('http://127.0.0.1:8000/analyze-text', json={'text': text}, timeout=10)
            response.raise_for_status()
            result = response.json()
            if 'error' in result:
                flash(f"Error analyzing text: {result['error']}")
                logger.warning(f"Analyze failed: {result['error']}")
                return redirect(url_for('analyze'))
            logger.info("Text analysis successful")
            return render_template('analyze.html', result=result)
        return render_template('analyze.html')
    except requests.RequestException as e:
        flash("Unable to analyze text. Please ensure the news service is running and try again.")
        logger.error(f"Analyze request error: {str(e)}")
        return redirect(url_for('analyze'))
    except Exception as e:
        flash(f"An unexpected error occurred during analysis: {str(e)}")
        logger.error(f"Unexpected analyze error: {str(e)}")
        return redirect(url_for('analyze'))

if __name__ == '__main__':
    logger.info("Starting Flask server")
    app.run(debug=True, host='0.0.0.0', port=5000)