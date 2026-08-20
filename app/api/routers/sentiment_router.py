"""
Sentiment Analysis API Router - Live Stimmungserkennung.

Endpoints für Echtzeit-Sentiment-Analyse von User-Input.
Version: 1.0
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Optional

from liara_engine.nlp.sentiment_analyzer import (
    get_sentiment_analyzer,
    SentimentCategory
)


router = APIRouter(prefix="/sentiment", tags=["Sentiment Analysis"])


class SentimentAnalyzeRequest(BaseModel):
    """Request für Sentiment-Analyse."""
    text: str = Field(..., min_length=1, max_length=5000)
    include_mood_recommendation: bool = Field(default=True)


class SentimentBatchRequest(BaseModel):
    """Request für Batch-Analyse mehrerer Texte."""
    texts: list[str] = Field(..., max_items=10)


@router.post("/analyze")
def analyze_sentiment(request: SentimentAnalyzeRequest):
    """
    🎭 Analysiere Sentiment eines Textes in Echtzeit.
    
    Erkennt emotionale Zustände wie:
    - Sehr positiv (Freude, Begeisterung)
    - Positiv (Zufriedenheit)
    - Negativ (Frustration)
    - Sehr negativ (Trauer, Wut)
    - Ängstlich (Stress, Sorge)
    - Aufgeregt (Vorfreude)
    - Verwirrt (Unsicherheit)
    
    Args:
        request: Text und optionale Flags
        
    Returns:
        Sentiment-Analyse mit Kategorie, Score, Confidence, Indikatoren
    """
    analyzer = get_sentiment_analyzer()
    
    # Analysiere Sentiment
    result = analyzer.analyze_sentiment(request.text)
    
    # Füge optionale Mood-Empfehlung hinzu
    if request.include_mood_recommendation:
        result['recommended_mood'] = analyzer.get_recommended_mood(result)
        result['response_modifier'] = analyzer.get_response_modifier(result)
    
    return result


@router.post("/batch")
def analyze_batch(request: SentimentBatchRequest):
    """
    📊 Analysiere mehrere Texte gleichzeitig.
    
    Args:
        request: Liste von max. 10 Texten
        
    Returns:
        Liste von Sentiment-Analysen
    """
    analyzer = get_sentiment_analyzer()
    
    results = []
    for text in request.texts:
        result = analyzer.analyze_sentiment(text)
        results.append(result)
    
    # Berechne Durchschnitts-Sentiment
    avg_score = sum(r['score'] for r in results) / len(results) if results else 0.0
    avg_intensity = sum(r['emotion_intensity'] for r in results) / len(results) if results else 0.0
    
    return {
        'analyses': results,
        'summary': {
            'count': len(results),
            'average_score': round(avg_score, 2),
            'average_intensity': round(avg_intensity, 2),
            'overall_sentiment': 'positive' if avg_score > 0.3 else 'negative' if avg_score < -0.3 else 'neutral'
        }
    }


@router.get("/history")
def get_history(limit: int = 10):
    """
    📜 Hole Sentiment-History.
    
    Args:
        limit: Max Anzahl Einträge (default: 10, max: 20)
        
    Returns:
        Liste von vergangenen Sentiment-Analysen
    """
    analyzer = get_sentiment_analyzer()
    limit = min(limit, 20)
    
    return {
        'history': analyzer.get_sentiment_history(limit=limit),
        'total_analyzed': len(analyzer.sentiment_history)
    }


@router.get("/categories")
def list_categories():
    """
    📋 Liste alle Sentiment-Kategorien.
    
    Returns:
        Verfügbare Sentiment-Kategorien mit Beschreibungen
    """
    return {
        'categories': [cat.value for cat in SentimentCategory],
        'descriptions': {
            'very_positive': '😊 Sehr positiv - Freude, Begeisterung, Glück',
            'positive': '🙂 Positiv - Zufriedenheit, gute Laune',
            'neutral': '😐 Neutral - Sachlich, neutral',
            'negative': '😔 Negativ - Unzufriedenheit, Frustration',
            'very_negative': '😢 Sehr negativ - Trauer, Wut, Verzweiflung',
            'anxious': '😰 Ängstlich - Stress, Sorge, Unsicherheit',
            'excited': '🤩 Aufgeregt - Vorfreude, Energie, Enthusiasmus',
            'confused': '🤔 Verwirrt - Unsicherheit, Fragen, Verwirrung'
        },
        'score_range': {
            'min': -1.0,
            'max': 1.0,
            'description': 'Negative Werte = negative Stimmung, Positive Werte = positive Stimmung'
        }
    }


@router.post("/mood-recommendation")
def get_mood_recommendation(request: SentimentAnalyzeRequest):
    """
    🎯 Empfehle Mood basierend auf Sentiment.
    
    Args:
        request: Text für Analyse
        
    Returns:
        Empfohlener Mood + Response-Modifier für System-Prompt
    """
    analyzer = get_sentiment_analyzer()
    
    # Analysiere Sentiment
    sentiment = analyzer.analyze_sentiment(request.text)
    
    # Empfehle Mood
    recommended_mood = analyzer.get_recommended_mood(sentiment)
    response_modifier = analyzer.get_response_modifier(sentiment)
    
    return {
        'sentiment': sentiment,
        'recommended_mood': recommended_mood,
        'response_modifier': response_modifier,
        'usage_hint': 'Füge response_modifier zum System-Prompt hinzu für emotionale Anpassung'
    }
