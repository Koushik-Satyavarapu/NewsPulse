import os
import time
from typing import List, Dict, Any
from dotenv import load_dotenv

import streamlit as st
from passlib.hash import bcrypt
import spacy

# Load spaCy model for NER (download 'en_core_web_sm' if not already installed)
nlp = spacy.load("en_core_web_sm")

import db
from news_api import search_news, top_headlines
from sentiment import analyze_sentiment
from utils import estimate_read_time, CATEGORIES

# ---------- Gemini Integration ----------
from google import genai

load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    st.error("GEMINI_API_KEY not found in .env file!")
client = genai.Client(api_key=api_key)

def summarize_text(text: str) -> str:
    response = client.models.generate_content(
        model="gemini-2.0-flash",
        contents=f"Summarize the following text:\n{text}"
    )
    return response.text

def generate_questions(text: str) -> str:
    response = client.models.generate_content(
        model="gemini-2.0-flash",
        contents=f"Generate 3 questions based on the following text:\n{text}"
    )
    return response.text

def ask_question(context: str, question: str) -> str:
    response = client.models.generate_content(
        model="gemini-2.0-flash",
        contents=f"Context: {context}\nQuestion: {question}\nAnswer:"
    )
    return response.text

# ---------- App Setup ----------
st.set_page_config(page_title="News Pulse - Personalized News", page_icon="📰", layout="wide")

# Initialize DB
db.init_db()

# ---------- Session Helpers ----------
def login(username: str, password: str) -> bool:
    user = db.get_user_by_username(username)
    if not user:
        return False
    return bcrypt.verify(password, user["password_hash"])

def register(username: str, email: str, password: str) -> (bool, str):
    if not username or not email or not password:
        return False, "All fields are required."
    if len(password) < 6:
        return False, "Password must be at least 6 characters."
    password_hash = bcrypt.hash(password[:72])
    ok, err = db.create_user(username, email, password_hash)
    if not ok:
        return False, err or "Registration failed."
    return True, "Account created! Please log in."

def ensure_logged_in():
    if "user" not in st.session_state:
        st.session_state.user = None

def do_logout():
    st.session_state.user = None
    st.success("Logged out.")

# ---------- UI Components ----------
def show_header():
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.title("📰 News Pulse")
        st.caption("Personalized news with sentiment analysis and bookmarks.")

def auth_view():
    st.markdown(
        """
        <style>
        .np-auth-outer { display:flex; justify-content:center; }
        .np-auth-card {
            width:100%; max-width:520px;
            border-radius: 16px;
            box-shadow: 0 18px 48px rgba(8,15,36,0.10);
        }
        .np-auth-head { text-align:center; margin-bottom:8px; }
        .np-auth-sub { text-align:center; color:#6b7280; margin-bottom:18px; }
        </style>
        """,
        unsafe_allow_html=True,
    )

    col_left, col_center, col_right = st.columns([1, 2, 1])
    with col_center:
        st.markdown('<div class="np-auth-outer"><div class="np-auth-card">', unsafe_allow_html=True)

        tab_login, tab_register = st.tabs(["Login", "Create Account"])

        with tab_login:
            with st.form(key="login_form"):
                st.markdown('<div class="np-auth-head"><h2 style="margin:0;color:#4b1fb8;text-align:center;">Welcome back</h2></div>', unsafe_allow_html=True)
                st.markdown('<div class="np-auth-sub">Sign in to access your personalized news</div>', unsafe_allow_html=True)

                lg_user = st.text_input("Username", key="login_user")
                lg_pass = st.text_input("Password", type="password", key="login_pass")

                submit_login = st.form_submit_button("Login")
                if submit_login:
                    if login(lg_user, lg_pass):
                        st.session_state.user = dict(db.get_user_by_username(lg_user))
                        st.success(f"Welcome, {st.session_state.user['username']}!")
                        st.rerun()
                    else:
                        st.error("Invalid username or password.")

        with tab_register:
            with st.form(key="register_form"):
                st.markdown('<div class="np-auth-head"><h2 style="margin:0;color:#4b1fb8;text-align:center;">Create account</h2></div>', unsafe_allow_html=True)
                st.markdown('<div class="np-auth-sub">Join News Pulse — personalize your feed</div>', unsafe_allow_html=True)

                rg_user = st.text_input("Username", key="rg_user")
                rg_email = st.text_input("Email", key="rg_email")
                rg_pass = st.text_input("Password", type="password", key="rg_pass")

                submit_register = st.form_submit_button("Create Account")
                if submit_register:
                    ok, msg = register(rg_user, rg_email, rg_pass)
                    if ok:
                        st.success(msg)
                    else:
                        st.error(msg)

        st.markdown('</div></div>', unsafe_allow_html=True)

def sidebar_menu():
    ensure_logged_in()
    if st.session_state.user:
        st.sidebar.success(f"Logged in as: {st.session_state.user['username']}")
        choice = st.sidebar.radio("Navigate", ["Home", "Search", "Bookmarks", "Profile", "Preferences", "About", "Logout"])
    else:
        choice = "Login"
    return choice

# ---------- FIXED FUNCTION ----------
def render_article_card(article: Dict[str, Any], user_id: int):
    import hashlib

    title = article.get("title", "")
    desc = article.get("description", "") or ""
    combined_text = title + ". " + desc
    label, score = analyze_sentiment(combined_text)
    read_min = estimate_read_time(desc or title)

    doc = nlp(combined_text)
    entities = [(ent.text, ent.label_) for ent in doc.ents]
    entity_list = [f"{text} ({label})" for text, label in sorted(entities, key=lambda x: x[0])]

    # unique hash for widget keys
    url_hash = hashlib.md5((article.get("url") or str(time.time())).encode()).hexdigest()[:8]

    with st.container(border=True):
        cols = st.columns([1, 3])
        if article.get("image_url"):
            cols[0].image(article["image_url"], use_container_width=True)
        else:
            cols[0].markdown("🖼️")
        cols[1].markdown(f"### [{title}]({article.get('url','')})")
        meta = f"**Source:** {article.get('source','Unknown')} | **Published:** {article.get('published_at','')} | **Read:** ~{read_min} min"
        cols[1].markdown(meta)
        cols[1].markdown(desc)

        sentiment_badge = f"**Sentiment:** :{'smile:' if label=='positive' else 'neutral_face:' if label=='neutral' else 'slightly_frowning_face:'} **{label.title()}** ({score:.2f})"
        cols[1].markdown(sentiment_badge)

        if entity_list:
            cols[1].markdown(f"**Named Entities:** {', '.join(entity_list)}")

        save_col, open_col = st.columns([1,1])
        if save_col.button("🔖 Save", key=f"save_{url_hash}"):
            ok, err = db.save_article(user_id, article)
            if ok:
                st.toast("Saved to bookmarks!")
            else:
                st.warning(err or "Unable to save.")
        open_col.link_button("Open Link", url=article.get("url",""), help="Open the full article")

        chat_col = st.columns([1,1,1])[0]
        if chat_col.button("💬 Discuss", key=f"chatbtn_{url_hash}"):
            st.session_state.setdefault("open_chats", {})
            st.session_state["open_chats"][article.get("url")] = True

        if st.session_state.get("open_chats", {}).get(article.get("url")):
            with st.expander("Discussion (answers powered by Gemini)", expanded=True):
                session_chats = st.session_state.setdefault("article_chats", {})
                msgs = session_chats.setdefault(article.get("url"), [])
                for m in msgs:
                    role = m.get("role")
                    content = m.get("content")
                    if role == "user":
                        st.markdown(f"**You:** {content}")
                    else:
                        st.markdown(f"**Assistant:** {content}")

                if st.button("Suggest Questions", key=f"suggest_{url_hash}"):
                    try:
                        qs = generate_questions((article.get("title","") + "\n\n" + (article.get("description","") or "")))
                        st.markdown(qs)
                    except Exception as e:
                        st.error(f"Gemini suggest error: {e}")

                user_q = st.text_input("Ask a question about this article", key=f"input_{url_hash}")
                if st.button("Send", key=f"send_{url_hash}") and user_q:
                    msgs.append({"role":"user","content": user_q})
                    convo_map = st.session_state.setdefault('convo_map', {})
                    convo_key = f"convo_{url_hash}"
                    convo_id = convo_map.get(convo_key)
                    try:
                        if not convo_id:
                            convo_id = db.create_conversation(user_id, article.get('url'))
                            convo_map[convo_key] = convo_id
                        db.save_message(convo_id, 'user', user_q)
                    except Exception as e:
                        st.warning(f"DB save (user message) failed: {e}")
                    try:
                        answer = ask_question(article.get("title","") + "\n\n" + (article.get("description","") or ""), user_q)
                    except Exception as e:
                        answer = f"Error calling Gemini: {e}"
                    msgs.append({"role":"assistant","content": answer})
                    try:
                        if convo_id:
                            db.save_message(convo_id, 'assistant', answer)
                    except Exception as e:
                        st.warning(f"DB save (assistant) failed: {e}")
                    session_chats[article.get("url")] = msgs
                    st.rerun()

# ---------- Pages ----------
def page_home():
    st.subheader("Top Headlines for You")
    prefs = db.get_preferences(st.session_state.user["id"]) if st.session_state.user else None
    preferred_categories = (prefs["categories"].split(",") if prefs and prefs["categories"] else []) or ["technology", "business", "science"]
    cols = st.columns(3)
    for i, cat in enumerate(preferred_categories[:3]):
        with cols[i]:
            st.markdown(f"#### {cat.title()}")
            try:
                headlines = top_headlines(topic=cat, max_results=5)
                for art in headlines:
                    st.markdown(f"- [{art['title']}]({art['url']})")
            except Exception as e:
                st.warning(str(e))

    st.divider()
    st.subheader("Latest Picks")
    try:
        latest = top_headlines(max_results=10)
        for art in latest:
            render_article_card(art, st.session_state.user["id"])
    except Exception as e:
        st.error(str(e))

def page_search():
    st.subheader("Search News")
    query = st.text_input("Search by topic, keyword, company, etc.", key="q")
    lang = st.selectbox("Language", ["en", "hi", "te", "ta", "ml", "bn"], index=0)
    country = st.selectbox("Country", ["in", "us", "gb", "au", "ca"], index=0)
    limit = st.slider("Max results", 5, 50, 15)

    if st.button("Search", type="primary") and query.strip():
        db.add_search_history(st.session_state.user["id"], query)
        try:
            results = search_news(query=query, lang=lang, country=country, max_results=limit)
            if not results:
                st.info("No results found. Try adjusting your query.")
            for art in results:
                render_article_card(art, st.session_state.user["id"])
        except Exception as e:
            st.error(str(e))

def page_bookmarks():
    st.subheader("Your Bookmarks")
    saved = db.get_saved_articles(st.session_state.user["id"])
    if not saved:
        st.info("No bookmarks yet. Save articles to see them here.")
        return

    for art in saved:
        with st.container(border=True):
            st.markdown(f"### [{art['title']}]({art['url']})")
            st.caption(f"{art.get('source','')} • {art.get('published_at','')}")
            if art.get("image_url"):
                st.image(art["image_url"], use_container_width=True)
            st.write(art.get("description",""))
            cols = st.columns([1,1])
            if cols[0].button("Remove", key=f"rm_{art['id']}"):
                db.remove_saved_article(st.session_state.user["id"], art["url"])
                st.rerun()
            cols[1].download_button("Export as CSV", data=_bookmarks_to_csv(saved), file_name="bookmarks.csv")

def _bookmarks_to_csv(rows: List[Dict[str, Any]]) -> str:
    import csv, io
    buff = io.StringIO()
    writer = csv.DictWriter(buff, fieldnames=["title","url","description","source","published_at","image_url"])
    writer.writeheader()
    for r in rows:
        writer.writerow({k: r.get(k, "") for k in writer.fieldnames})
    return buff.getvalue()

def page_profile():
    st.subheader("Profile")
    u = db.get_user_by_id(st.session_state.user["id"])
    full_name = st.text_input("Full Name", value=u["full_name"] or "")
    bio = st.text_area("Bio", value=u["bio"] or "", height=120)
    if st.button("Save Profile"):
        db.update_profile(u["id"], full_name, bio)
        st.success("Profile updated.")

    st.markdown("### Recent Searches")
    hist = db.get_search_history(u["id"], limit=20)
    if not hist:
        st.caption("No searches yet.")
    else:
        for h in hist:
            st.markdown(f"- **{h['query']}**  \n  _{h['created_at']}_")

def page_prefs():
    st.subheader("Preferences")
    prefs = db.get_preferences(st.session_state.user["id"])
    cur_cats = [c for c in (prefs["categories"].split(",") if prefs["categories"] else []) if c]
    cur_srcs = [s for s in (prefs["sources"].split(",") if prefs["sources"] else []) if s]
    cur_keys = [k for k in (prefs["keywords"].split(",") if prefs["keywords"] else []) if k]

    cats = st.multiselect("Preferred Categories (max 5)", CATEGORIES, default=cur_cats[:5])
    sources = st.text_input("Preferred Sources (comma-separated)", value=",".join(cur_srcs))
    keywords = st.text_input("Preferred Keywords (comma-separated)", value=",".join(cur_keys))

    if st.button("Save Preferences", type="primary"):
        db.update_preferences(
            st.session_state.user["id"],
            categories=cats,
            sources=[s.strip() for s in sources.split(",") if s.strip()],
            keywords=[k.strip() for k in keywords.split(",") if k.strip()],
        )
        st.success("Preferences saved.")

def page_about():
    st.subheader("About")
    st.write(
        "News Pulse is a demo app built with Streamlit + SQLite + GNews API. "
        "Features include login, personalized preferences, search, sentiment analysis, and bookmarks."
    )
    st.caption("Built for learning purposes.")

# ---------- Main ----------
def main():
    show_header()
    ensure_logged_in()

    choice = sidebar_menu()

    if choice == "Login":
        auth_view()
        return
    if choice == "Logout":
        do_logout()
        return

    if not st.session_state.user:
        st.info("Please log in to continue.")
        auth_view()
        return

    if choice == "Home":
        page_home()
    elif choice == "Search":
        page_search()
    elif choice == "Bookmarks":
        page_bookmarks()
    elif choice == "Profile":
        page_profile()
    elif choice == "Preferences":
        page_prefs()
    elif choice == "About":
        page_about()

if __name__ == "__main__":
    main()
