# News Pulse — Personalized News App (Streamlit + SQLite + GNews)

A complete starter to build a personalized news app using **Streamlit**, **SQLite**, **GNews API**, and **NLTK VADER** for sentiment analysis.

## Features
- 🔐 User authentication (register/login) with bcrypt-hashed passwords
- 👤 Personal profile (full name, bio)
- ⚙️ Preferences: categories, sources, keywords
- 🔎 Search bar to query news
- 🧠 Sentiment analysis per article (positive / neutral / negative + score)
- 🏷️ Named Entity Recognition (NER) to extract key people, places, and organizations from articles
- 🔖 Bookmarks (save/remove) + export to CSV
- 🏠 Home: Top headlines by your preferred categories
- 🕑 Search history

---

## 1) Prerequisites
- Python 3.9+
- A **GNews API key** (free tier available): https://gnews.io

## 2) Setup (Windows PowerShell)
```powershell
# 1) Go to your projects folder
cd C:\Users\<you>\Desktop

# 2) Create and activate a virtual environment
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# 3) Unzip this project (if you downloaded the zip) or clone your repo
#    Then cd into the project folder:
cd news_pulse_app

# 4) Install dependencies
pip install -r requirements.txt

# 5) Create a .env file from sample and add your GNews API key
copy .env.example .env
# open .env in a text editor and paste your key

# 6) Run the app
streamlit run app.py
```

## 3) First Run
- The app initializes `app.db` using `schema.sql` automatically.
- Register a new account, login, set your Preferences, and start searching!

## 4) Project Structure
```
news_pulse_app/
├─ app.py              # Streamlit app (UI + logic)
├─ db.py               # SQLite helpers (users, prefs, bookmarks, history)
├─ news_api.py         # GNews API wrapper
├─ sentiment.py        # VADER sentiment analysis
├─ utils.py            # Helpers (read-time, categories)
├─ schema.sql          # Database schema
├─ requirements.txt
├─ .env.example        # Copy to .env and set GNEWS_API_KEY
└─ assets/
```

## 5) Notes
- Sentiment uses the article **title + description** for a quick signal.
- NER highlights important entities (like companies, politicians, locations) to give richer context per article.
- Streamlit keeps login session in `st.session_state` (not secure for production).
- For production, add proper session management and HTTPS.

## 6) Extending
- Add per-user recommendation models.
- Add email digests of top stories.
- Add admin dashboard to manage users.
- Add per-article feedback to refine keyword prefs.
- Use NER results to auto-tag bookmarks and improve personalized news recommendations.
