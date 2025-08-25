from flask import Flask, render_template, request, redirect, url_for, flash
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure, PyMongoError, ServerSelectionTimeoutError
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
import requests
import os
import logging
from bson.objectid import ObjectId
import socket

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.secret_key = os.urandom(24)  # Or 'your_secret_key' for development

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
            username = request.form.get('username')
            password = request.form.get('password')
            if not username or not password:
                flash('Username and password are required')
                logger.warning("Signup failed: Missing username or password")
                return redirect(url_for('signup'))
            hashed_pw = generate_password_hash(password, method='pbkdf2:sha256')
            if db.users.find_one({'username': username}):
                flash('Username already exists')
                logger.warning(f"Signup failed: Username {username} already exists")
                return redirect(url_for('signup'))
            db.users.insert_one({'username': username, 'password': hashed_pw})
            flash('Signup successful! Please login.')
            logger.info(f"User {username} signed up successfully")
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
            username = request.form.get('username')
            password = request.form.get('password')
            if not username or not password:
                flash('Username and password are required')
                logger.warning("Login failed: Missing username or password")
                return redirect(url_for('login'))
            user = db.users.find_one({'username': username})
            if user and check_password_hash(user['password'], password):
                login_user(User(str(user['_id'])))
                logger.info(f"User {username} logged in successfully")
                return redirect(url_for('home'))
            flash('Invalid credentials')
            logger.warning(f"Login failed for {username}: Invalid credentials")
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

@app.route('/logout')
@login_required
def logout():
    logger.debug("Accessing logout route")
    try:
        logout_user()
        flash('Logged out successfully')
        logger.info("User logged out")
        return redirect(url_for('home'))
    except Exception as e:
        flash('Error during logout')
        logger.error(f"Logout error: {str(e)}")
        return redirect(url_for('home'))

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
        username = user['username'] if user else 'Unknown'
        return render_template('profile.html', username=username)
    except Exception as e:
        flash('Error loading profile')
        logger.error(f"Profile error: {str(e)}")
        return redirect(url_for('dashboard'))

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

        topic = request.form.get('topic', '')
        city = request.form.get('city', '')
        keyword = request.form.get('keyword', '')
        region = request.form.get('region', '')
        logger.debug(f"Search parameters: topic={topic}, city={city}, keyword={keyword}, region={region}")
        response = requests.get('http://127.0.0.1:8000/fetch-news', params={'topic': topic, 'city': city, 'keyword': keyword, 'region': region}, timeout=10)
        response.raise_for_status()
        data = response.json()
        if 'error' in data:
            flash(f"Error fetching news: {data['error']}")
            logger.warning(f"Search failed: {data['error']}")
            return redirect(url_for('dashboard'))
        if not data.get('articles'):
            flash("No articles found for the given parameters.")
            logger.warning("No articles returned from FastAPI")
            return redirect(url_for('dashboard'))
        logger.info("Search successful, rendering dashboard with data")
        return render_template('dashboard.html', data=data)
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