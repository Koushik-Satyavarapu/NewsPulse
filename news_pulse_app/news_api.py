import os
import requests
from typing import List, Optional, Dict, Any
from urllib.parse import urlencode
from dotenv import load_dotenv

load_dotenv()
API_KEY = os.getenv("GNEWS_API_KEY")
DEFAULT_LANGUAGE = os.getenv("DEFAULT_LANGUAGE", "en")
DEFAULT_COUNTRY = os.getenv("DEFAULT_COUNTRY", "in")

BASE_URL = "https://gnews.io/api/v4"

def _request(endpoint: str, params: Dict[str, Any]) -> Dict[str, Any]:
    if not API_KEY:
        raise RuntimeError("Missing GNEWS_API_KEY. Create a .env file from .env.example and add your key.")
    params["apikey"] = API_KEY
    url = f"{BASE_URL}/{endpoint}?{urlencode(params)}"
    try:
        resp = requests.get(url, timeout=15)
        resp.raise_for_status()
        return resp.json()
    except requests.HTTPError as e:
        raise RuntimeError(f"GNews API error: {e} -> {resp.text}")  # type: ignore
    except Exception as e:
        raise RuntimeError(f"Request failed: {e}")

def search_news(query: str, lang: Optional[str] = None, country: Optional[str] = None, max_results: int = 20) -> List[Dict[str, Any]]:
    params = {
        "q": query,
        "lang": lang or DEFAULT_LANGUAGE,
        "country": country or DEFAULT_COUNTRY,
        "max": max(1, min(int(max_results), 100)),
    }
    data = _request("search", params)
    return _normalize_articles(data.get("articles", []))

def top_headlines(topic: Optional[str] = None, lang: Optional[str] = None, country: Optional[str] = None, max_results: int = 20) -> List[Dict[str, Any]]:
    # topic can be: world, nation, business, technology, entertainment, sports, science, health
    params = {
        "lang": lang or DEFAULT_LANGUAGE,
        "country": country or DEFAULT_COUNTRY,
        "max": max(1, min(int(max_results), 100)),
    }
    if topic:
        params["topic"] = topic
    data = _request("top-headlines", params)
    return _normalize_articles(data.get("articles", []))

def _normalize_articles(articles: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    normalized = []
    for a in articles:
        normalized.append({
            "title": a.get("title", ""),
            "description": a.get("description", ""),
            "content": a.get("content", ""),
            "url": a.get("url", ""),
            "image_url": a.get("image", ""),
            "published_at": a.get("publishedAt", ""),
            "source": (a.get("source") or {}).get("name", ""),
        })
    return normalized
