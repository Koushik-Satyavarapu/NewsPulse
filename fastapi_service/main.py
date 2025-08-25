from fastapi import FastAPI, Query, HTTPException
import requests
from transformers import pipeline
import spacy
import nltk
from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize
import logging
import os
import re

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Download NLTK data
try:
    nltk.data.find('tokenizers/punkt')
    nltk.data.find('tokenizers/punkt_tab')
    nltk.data.find('corpora/stopwords')
except LookupError:
    nltk.download('punkt')
    nltk.download('punkt_tab')
    nltk.download('stopwords')

# Load spaCy model
try:
    nlp = spacy.load('en_core_web_sm')
except OSError:
    logger.error("spaCy model 'en_core_web_sm' not found. Please install it using: python -m spacy download en_core_web_sm")
    raise Exception("spaCy model 'en_core_web_sm' is required.")

# Load Hugging Face sentiment analysis pipeline
try:
    sentiment_analyzer = pipeline('sentiment-analysis', model='distilbert-base-uncased-finetuned-sst-2-english')
except Exception as e:
    logger.error(f"Failed to load Hugging Face model: {str(e)}")
    raise Exception("Hugging Face model 'distilbert-base-uncased-finetuned-sst-2-english' is required.")

app = FastAPI()
NEWS_API_KEY = 'b10326e677404906b8278f44b674b094'  # Your NewsAPI key

# Text preprocessing pipeline
def preprocess_text(text):
    if not text:
        return ""
    # Clean text
    text = re.sub(r'[^\w\s]', '', text.lower())
    # Tokenize
    tokens = word_tokenize(text)
    # Remove stopwords
    stop_words = set(stopwords.words('english'))
    tokens = [token for token in tokens if token not in stop_words]
    # Lemmatize with spaCy
    doc = nlp(' '.join(tokens))
    cleaned_text = ' '.join([token.lemma_ for token in doc])
    return cleaned_text

# NER extraction
def extract_entities(text):
    doc = nlp(text)
    entities = [{'text': ent.text, 'label': ent.label_} for ent in doc.ents if ent.label_ in ['PERSON', 'ORG', 'GPE']]
    return entities

@app.on_event("startup")
async def startup_event():
    logger.info("Starting FastAPI server")
    if not NEWS_API_KEY:
        logger.error("NEWS_API_KEY is not set. Please provide a valid NewsAPI key.")
        raise Exception("NEWS_API_KEY is required.")

@app.get("/health")
async def health_check():
    logger.debug("Health check endpoint accessed")
    return {"status": "FastAPI service is running"}

@app.get("/fetch-news")
async def fetch_news(
    keyword: str = Query(None),
    city: str = Query(None),
    topic: str = Query(None),
    region: str = Query(None)
):
    logger.debug(f"Fetching news with parameters: keyword={keyword}, city={city}, topic={topic}, region={region}")
    params = {'apiKey': NEWS_API_KEY, 'language': 'en'}
    query = []
    if keyword:
        query.append(keyword)
    if city:
        query.append(city)
    if topic:
        query.append(topic)
    if region:
        query.append(region)
    if query:
        params['q'] = ' '.join(query)
    try:
        response = requests.get('https://newsapi.org/v2/everything', params=params, timeout=10)
        response.raise_for_status()
        articles = response.json().get('articles', [])
        if not articles:
            logger.warning("No articles found for the given parameters")
            return {"articles": [], "sentiments": {"positive": 0, "negative": 0, "neutral": 0}, "trends": {}}
        sentiments = {'positive': 0, 'negative': 0, 'neutral': 0}
        trends = {}
        processed_articles = []
        for article in articles:
            text = article['title'] + ' ' + article.get('description', '')
            # Preprocess text
            cleaned_text = preprocess_text(text)
            # Sentiment analysis
            sentiment_result = sentiment_analyzer(cleaned_text or text)
            sentiment = sentiment_result[0]['label'].lower()
            sentiment_score = sentiment_result[0]['score']
            if sentiment == 'positive':
                sentiments['positive'] += 1
            elif sentiment == 'negative':
                sentiments['negative'] += 1
            else:
                sentiments['neutral'] += 1
            # NER
            entities = extract_entities(text)
            # Trends
            for word in cleaned_text.split():
                if len(word) > 3:
                    trends[word] = trends.get(word, 0) + 1
            article['sentiment'] = sentiment
            article['sentiment_score'] = sentiment_score
            article['entities'] = entities
            processed_articles.append(article)
        top_trends = dict(sorted(trends.items(), key=lambda item: item[1], reverse=True)[:10])
        logger.info("News fetched successfully")
        return {
            "articles": processed_articles,
            "sentiments": sentiments,
            "trends": top_trends
        }
    except requests.RequestException as e:
        logger.error(f"NewsAPI request failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch news from NewsAPI: {str(e)}")
    except Exception as e:
        logger.error(f"Unexpected error in fetch_news: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")

@app.post("/analyze-text")
async def analyze_text(data: dict):
    logger.debug("Analyzing text")
    try:
        text = data.get('text')
        if not text:
            logger.warning("No text provided for analysis")
            raise HTTPException(status_code=400, detail="Text is required")
        # Preprocess text
        cleaned_text = preprocess_text(text)
        # Sentiment analysis
        sentiment_result = sentiment_analyzer(cleaned_text or text)
        sentiment = sentiment_result[0]['label'].upper()
        sentiment_score = sentiment_result[0]['score']
        # NER
        entities = extract_entities(text)
        logger.info("Text analysis successful")
        return {
            "sentiment": sentiment,
            "sentiment_score": sentiment_score,
            "entities": entities
        }
    except Exception as e:
        logger.error(f"Unexpected error in analyze_text: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")

if __name__ == "__main__":
    logger.info("Running FastAPI server")
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)