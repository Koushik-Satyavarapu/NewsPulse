# NewsPulse — Personalized News Dashboard

A dynamic news aggregation and analysis dashboard built with **Flask**, **MongoDB Atlas**, **GNews API**, **Hugging Face Transformers** for sentiment analysis, and **SpaCy** for Named Entity Recognition (NER). This project provides a personalized news experience with user authentication, sentiment insights, and visualizations.

## Features
- 🔐 User authentication (register/login) with bcrypt-hashed passwords and Google OAuth
- 👤 User profile management (name, email updates)
- ⚙️ News search by region, topic, and keyword
- 🧠 Sentiment analysis per article using Hugging Face Transformers (positive/negative/neutral + score)
- 🏷️ NER to extract key entities (people, organizations, locations)
- 📊 Insights dashboard with sentiment and source distribution charts
- 🕒 Real-time news updates from GNews API

## 1) Prerequisites
- Python 3.9+
- A **GNews API key** (free tier available): https://gnews.io
- MongoDB Atlas account (for database hosting)

## 2) Setup (Windows PowerShell)
```powershell
# 1) Go to your projects folder
cd C:\Users\<you>\Desktop

# 2) Create and activate a virtual environment
python -m venv venv
.\venv\Scripts\Activate.ps1

# 3) Clone or copy your project folder
#    Then cd into the project folder:
cd NewsPulse

# 4) Install dependencies
pip install -r requirements.txt

# 5) Set up environment variables
#    Create a .env file and add your GNews API key:
#    GNEWS_API_KEY=your_api_key_here
#    GOOGLE_CLIENT_ID=your_google_client_id
#    GOOGLE_CLIENT_SECRET=your_google_client_secret

# 6) Run the app
python app.py
```

## 3) First Run
- The app connects to MongoDB Atlas automatically using the connection string in `app.py`.
- Register a new account, log in (via email/password or Google), and start searching news!
- Initial runs may download the Hugging Face model (~500 MB), so ensure a stable internet connection.

## 4) Project Structure
```
NewsPulse/
├─ app.py              # Flask app (routes, logic, and API integration)
├─ templates/          # HTML templates (dashboard.html, login.html, etc.)
├─ static/             # CSS and JS (if added)
├─ requirements.txt    # Python dependencies
├─ .env                # Environment variables (API keys, secrets)
└─ README.md           # This file
```

## 5) Notes
- Sentiment analysis uses Hugging Face’s `distilbert-base-uncased-finetuned-sst-2-english` model on article titles and descriptions for accurate insights.
- NER leverages SpaCy’s `en_core_web_sm` model to identify entities, enhancing article context.
- The free GNews API limits results to 10 articles per search; visualizations (pie and donut charts) reflect this limit.
- User sessions are managed with Flask-Login; for production, add HTTPS and secure session handling.
- Cards on the dashboard are customizable (recently adjusted for size and spacing).

## 6) Extending
- Upgrade to a paid GNews plan or switch to NewsAPI for 12+ articles per search.
- Add user feedback to refine sentiment analysis.
- Implement a recommendation system based on search history.
- Enhance the dashboard with additional visualizations (e.g., trend lines).
- Add export functionality for search results or bookmarks.

## 7) Troubleshooting
- **10 Cards Limit**: Due to the GNews free tier cap, only 10 articles are displayed. Upgrade your API plan for more.
- **Hugging Face Errors**: Ensure internet access for model download; check logs for failures.
- **MongoDB Connection**: Verify your Atlas connection string and IP whitelist.

---
