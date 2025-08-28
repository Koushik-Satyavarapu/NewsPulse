from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import requests
from datetime import datetime
from dateutil import parser
import logging
import re
from typing import Dict, List
from transformers import pipeline
import spacy
from nltk.tokenize import word_tokenize
from nltk.corpus import stopwords
from collections import Counter
import nltk

# Download NLTK data
nltk.download('punkt', quiet=True)
nltk.download('stopwords', quiet=True)

app = FastAPI()

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize NLP models
sentiment_analyzer = pipeline("sentiment-analysis", model="distilbert-base-uncased-finetuned-sst-2-english")
nlp = spacy.load("en_core_web_sm")
stop_words = set(stopwords.words('english'))

def clean_text(text: str) -> str:
    text = re.sub(r'[^\w\s]', '', text.lower())
    tokens = word_tokenize(text)
    tokens = [token for token in tokens if token not in stop_words]
    return ' '.join(tokens)

def fetch_gdelt_news(query: str) -> List[Dict]:
    def format_gdelt_date(date_str: str) -> str:
        try:
            return datetime.strptime(date_str, "%Y%m%d%H%M%S").isoformat()
        except Exception:
            return date_str

    gdelt_url = "http://api.gdeltproject.org/api/v2/doc/doc"
    params = {
        "query": query,
        "mode": "artlist",
        "maxrecords": 20,
        "timespan": "1m",
        "format": "json"
    }
    try:
        response = requests.get(gdelt_url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        articles = data.get("articles", [])
        standardized_articles = [
            {
                "title": article.get("title", ""),
                "description": article.get("seendate", ""),
                "url": article.get("url", ""),
                "urlToImage": article.get("socialimage", ""),
                "publishedAt": format_gdelt_date(article.get("seendate", ""))
            } for article in articles
        ]
        return standardized_articles
    except requests.RequestException as e:
        logger.error(f"GDELT request failed: {str(e)}")
        return []

@app.get("/fetch-news")
async def fetch_news(topic: str = "", keyword: str = "", region: str = ""):
    query = f"{keyword} {topic} {region}".strip()
    if not query:
        raise HTTPException(status_code=400, detail="At least one query parameter is required")

    api_key = "b10326e677404906b8278f44b674b094"
    url = "https://newsapi.org/v2/everything"
    params = {
        "q": query or "news",
        "language": "en",
        "pageSize": 20,
        "apiKey": api_key
    }

    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()

        if data.get("status") != "ok":
            logger.warning("NewsAPI failed, trying GDELT")
            articles = fetch_gdelt_news(query)
        else:
            articles = data.get("articles", [])

        processed_articles = []
        all_text = ""

        for article in articles:
            title = article.get("title", "")
            description = article.get("description", "")
            content = f"{title} {description}"
            all_text += content + " "

            cleaned_content = clean_text(content)
            doc = nlp(cleaned_content)
            entities = [{"text": ent.text, "label": ent.label_} for ent in doc.ents]

            sentiment_result = sentiment_analyzer(cleaned_content[:512])[0]
            sentiment = "positive" if sentiment_result["label"] == "POSITIVE" else "negative"
            sentiment_score = sentiment_result["score"]

            processed_articles.append({
                "title": title,
                "description": description,
                "url": article.get("url", ""),
                "urlToImage": article.get("urlToImage", ""),
                "publishedAt": article.get("publishedAt", ""),
                "sentiment": sentiment,
                "sentiment_score": sentiment_score,
                "entities": entities
            })

        # Sort articles by publishedAt in descending order (latest first)
        processed_articles.sort(
            key=lambda x: parser.parse(x.get("publishedAt")) if x.get("publishedAt") else datetime.min,
            reverse=True
        )

        cleaned_text = clean_text(all_text)
        tokens = word_tokenize(cleaned_text)
        word_freq = Counter(tokens)
        trends = dict(word_freq.most_common(5))

        sentiments = {"positive": 0, "negative": 0, "neutral": 0}
        for article in processed_articles:
            sentiment = article.get("sentiment", "neutral")
            sentiments[sentiment] = sentiments.get(sentiment, 0) + 1

        return {
            "articles": processed_articles,
            "sentiments": sentiments,
            "trends": trends
        }

    except requests.RequestException as e:
        logger.error(f"NewsAPI request failed: {str(e)}")
        articles = fetch_gdelt_news(query)
        processed_articles = []
        all_text = ""

        for article in articles:
            title = article.get("title", "")
            description = article.get("description", "")
            content = f"{title} {description}"
            all_text += content + " "

            cleaned_content = clean_text(content)
            doc = nlp(cleaned_content)
            entities = [{"text": ent.text, "label": ent.label_} for ent in doc.ents]

            sentiment_result = sentiment_analyzer(cleaned_content[:512])[0]
            sentiment = "positive" if sentiment_result["label"] == "POSITIVE" else "negative"
            sentiment_score = sentiment_result["score"]

            processed_articles.append({
                "title": title,
                "description": description,
                "url": article.get("url", ""),
                "urlToImage": article.get("urlToImage", ""),
                "publishedAt": article.get("publishedAt", ""),
                "sentiment": sentiment,
                "sentiment_score": sentiment_score,
                "entities": entities
            })

        # Sort articles by publishedAt in descending order (latest first)
        processed_articles.sort(
            key=lambda x: parser.parse(x.get("publishedAt")) if x.get("publishedAt") else datetime.min,
            reverse=True
        )

        cleaned_text = clean_text(all_text)
        tokens = word_tokenize(cleaned_text)
        word_freq = Counter(tokens)
        trends = dict(word_freq.most_common(5))

        sentiments = {"positive": 0, "negative": 0, "neutral": 0}
        for article in processed_articles:
            sentiment = article.get("sentiment", "neutral")
            sentiments[sentiment] = sentiments.get(sentiment, 0) + 1

        return {
            "articles": processed_articles,
            "sentiments": sentiments,
            "trends": trends
        }

@app.post("/analyze-text")
async def analyze_text(request: Dict):
    text = request.get("text", "")
    if not text:
        raise HTTPException(status_code=400, detail="Text is required")

    cleaned_text = clean_text(text)
    sentiment_result = sentiment_analyzer(cleaned_text[:512])[0]
    sentiment = "positive" if sentiment_result["label"] == "POSITIVE" else "negative"
    sentiment_score = sentiment_result["score"]

    doc = nlp(cleaned_text)
    entities = [{"text": ent.text, "label": ent.label_} for ent in doc.ents]

    return {
        "sentiment": sentiment,
        "sentiment_score": sentiment_score,
        "entities": entities
    }