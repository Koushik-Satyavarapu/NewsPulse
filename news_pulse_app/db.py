import sqlite3
from pathlib import Path
from typing import List, Optional, Tuple, Dict, Any

DB_PATH = Path(__file__).parent / "app.db"

def get_connection():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    schema_file = Path(__file__).parent / "schema.sql"
    with get_connection() as conn, open(schema_file, "r", encoding="utf-8") as f:
        conn.executescript(f.read())
        conn.commit()

# ---------- USERS ----------

def create_user(username: str, email: str, password_hash: str) -> Tuple[bool, Optional[str]]:
    try:
        with get_connection() as conn:
            conn.execute(
                "INSERT INTO users (username, email, password_hash) VALUES (?, ?, ?)",
                (username.strip(), email.strip().lower(), password_hash),
            )
            conn.commit()
        return True, None
    except sqlite3.IntegrityError as e:
        return False, "Username or email already exists."
    except Exception as e:
        return False, str(e)

def get_user_by_username(username: str) -> Optional[sqlite3.Row]:
    with get_connection() as conn:
        cur = conn.execute("SELECT * FROM users WHERE username = ?", (username.strip(),))
        return cur.fetchone()

def get_user_by_id(user_id: int) -> Optional[sqlite3.Row]:
    with get_connection() as conn:
        cur = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,))
        return cur.fetchone()

def update_profile(user_id: int, full_name: str, bio: str) -> None:
    with get_connection() as conn:
        conn.execute(
            "UPDATE users SET full_name = ?, bio = ? WHERE id = ?",
            (full_name.strip(), bio.strip(), user_id),
        )
        conn.commit()

# ---------- PREFERENCES ----------

def get_preferences(user_id: int) -> sqlite3.Row:
    with get_connection() as conn:
        cur = conn.execute("SELECT * FROM preferences WHERE user_id = ?", (user_id,))
        row = cur.fetchone()
        if not row:
            conn.execute("INSERT INTO preferences (user_id) VALUES (?)", (user_id,))
            conn.commit()
            cur = conn.execute("SELECT * FROM preferences WHERE user_id = ?", (user_id,))
            row = cur.fetchone()
        return row

def update_preferences(user_id: int, categories: List[str], sources: List[str], keywords: List[str]) -> None:
    cats = ",".join(sorted(set([c.strip() for c in categories if c.strip()])))
    srcs = ",".join(sorted(set([s.strip() for s in sources if s.strip()])))
    keys = ",".join(sorted(set([k.strip() for k in keywords if k.strip()])))
    with get_connection() as conn:
        conn.execute(
            "UPDATE preferences SET categories = ?, sources = ?, keywords = ? WHERE user_id = ?",
            (cats, srcs, keys, user_id),
        )
        conn.commit()

# ---------- SAVED ARTICLES ----------

def save_article(user_id: int, article: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
    try:
        with get_connection() as conn:
            conn.execute(
                "INSERT INTO saved_articles (user_id, title, url, description, source, published_at, image_url) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (
                    user_id,
                    article.get("title","").strip(),
                    article.get("url","").strip(),
                    article.get("description",""),
                    article.get("source",""),
                    article.get("published_at",""),
                    article.get("image_url",""),
                ),
            )
            conn.commit()
        return True, None
    except sqlite3.IntegrityError:
        return False, "Already saved."
    except Exception as e:
        return False, str(e)

def get_saved_articles(user_id: int) -> list:
    with get_connection() as conn:
        cur = conn.execute(
            "SELECT id, title, url, description, source, published_at, image_url FROM saved_articles WHERE user_id = ? ORDER BY id DESC",
            (user_id,),
        )
        return [dict(row) for row in cur.fetchall()]

def remove_saved_article(user_id: int, url: str) -> None:
    with get_connection() as conn:
        conn.execute("DELETE FROM saved_articles WHERE user_id = ? AND url = ?", (user_id, url))
        conn.commit()

# ---------- SEARCH HISTORY ----------

def add_search_history(user_id: int, query: str) -> None:
    with get_connection() as conn:
        conn.execute("INSERT INTO search_history (user_id, query) VALUES (?, ?)", (user_id, query.strip()))
        conn.commit()

def get_search_history(user_id: int, limit: int = 20) -> list:
    with get_connection() as conn:
        cur = conn.execute(
            "SELECT query, created_at FROM search_history WHERE user_id = ? ORDER BY id DESC LIMIT ?",
            (user_id, limit),
        )
        return [dict(row) for row in cur.fetchall()]


# ---------- CONVERSATIONS & MESSAGES ----------
def create_conversation(user_id: int, article_url: str) -> int:
    with get_connection() as conn:
        cur = conn.execute("INSERT INTO conversations (user_id, article_url) VALUES (?, ?)", (user_id, article_url))
        conn.commit()
        return cur.lastrowid

def save_message(conversation_id: int, role: str, content: str):
    with get_connection() as conn:
        conn.execute("INSERT INTO messages (conversation_id, role, content) VALUES (?, ?, ?)", (conversation_id, role, content))
        conn.commit()

def get_messages_for_article(article_url: str) -> list:
    with get_connection() as conn:
        cur = conn.execute("""
            SELECT m.role, m.content, m.created_at
            FROM messages m
            JOIN conversations c ON c.id = m.conversation_id
            WHERE c.article_url=?
            ORDER BY m.id ASC
        """, (article_url,))
        return [dict(row) for row in cur.fetchall()]
