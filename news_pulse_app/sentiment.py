from functools import lru_cache
from typing import Tuple
import nltk
from nltk.sentiment import SentimentIntensityAnalyzer

# Ensure lexicon (cached so it doesn't re-download every run)
@lru_cache(maxsize=1)
def _get_analyzer():
    try:
        nltk.data.find("sentiment/vader_lexicon.zip")
    except LookupError:
        nltk.download("vader_lexicon")
    return SentimentIntensityAnalyzer()

def analyze_sentiment(text: str) -> Tuple[str, float]:
    if not text or not text.strip():
        return "neutral", 0.0
    sia = _get_analyzer()
    score = sia.polarity_scores(text)["compound"]
    label = "positive" if score >= 0.05 else "negative" if score <= -0.05 else "neutral"
    return label, float(score)
