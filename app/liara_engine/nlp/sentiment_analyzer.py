"""
Live Sentiment Analysis für Liara - Echtzeit-Stimmungserkennung.

Analysiert User-Input während der Eingabe und erkennt emotionale Zustände.
Version: 1.0
"""

from enum import Enum
from typing import Dict, List, Tuple, Optional
from datetime import datetime
import re


class SentimentCategory(str, Enum):
    """Sentiment-Kategorien für User-Input."""
    VERY_POSITIVE = "very_positive"      # 😊 Sehr positiv (Freude, Begeisterung)
    POSITIVE = "positive"                # 🙂 Positiv (Zufrieden, gut gelaunt)
    NEUTRAL = "neutral"                  # 😐 Neutral (sachlich, neutral)
    NEGATIVE = "negative"                # 😔 Negativ (unzufrieden, frustriert)
    VERY_NEGATIVE = "very_negative"      # 😢 Sehr negativ (Trauer, Wut)
    ANXIOUS = "anxious"                  # 😰 Ängstlich (Sorge, Stress)
    EXCITED = "excited"                  # 🤩 Aufgeregt (Vorfreude, Energie)
    CONFUSED = "confused"                # 🤔 Verwirrt (Unsicherheit, Fragen)


class EmotionMarkers:
    """Emotionale Marker und Schlüsselwörter für Sentiment-Detection."""
    
    # Sehr positive Emotionen
    VERY_POSITIVE = {
        'keywords': [
            'super', 'fantastisch', 'genial', 'perfekt', 'wunderbar',
            'ausgezeichnet', 'hervorragend', 'begeistert', 'glücklich',
            'liebe', 'amazing', 'awesome', 'love', 'brilliant', 'excellent'
        ],
        'patterns': [
            r'!!!+',  # Mehrfache Ausrufezeichen
            r'😍|🥰|😊|🤗|🎉|✨|💖',  # Emojis
            r'\b(sehr|mega|ultra|echt)\s+(gut|toll|super|cool)\b'
        ],
        'score': 1.0
    }
    
    # Positive Emotionen
    POSITIVE = {
        'keywords': [
            'gut', 'schön', 'toll', 'nice', 'cool', 'danke', 'thanks',
            'freue', 'gefällt', 'mag', 'gerne', 'hilfreich', 'klappt',
            'funktioniert', 'prima', 'okay', 'passt', 'like', 'good'
        ],
        'patterns': [
            r'!',  # Einzelnes Ausrufezeichen
            r'🙂|😀|👍|👌|✅',
            r'\b(ganz|ziemlich)\s+(gut|ok|nice)\b'
        ],
        'score': 0.6
    }
    
    # Sehr negative Emotionen
    VERY_NEGATIVE = {
        'keywords': [
            'hasse', 'schrecklich', 'furchtbar', 'katastrophe', 'wütend',
            'verzweifelt', 'traurig', 'deprimiert', 'awful', 'terrible',
            'hate', 'horrible', 'worst', 'disaster', 'miserable'
        ],
        'patterns': [
            r'😭|😡|😢|💔|😠',
            r'\b(total|völlig|komplett)\s+(schlecht|mies|katastrophal)\b',
            r'\b(nie|niemals)\s+(wieder|mehr)\b'
        ],
        'score': -1.0
    }
    
    # Negative Emotionen
    NEGATIVE = {
        'keywords': [
            'schlecht', 'nicht gut', 'problem', 'fehler', 'nervt', 'ärgerlich',
            'frustrierend', 'schwierig', 'kompliziert', 'bad', 'wrong',
            'issue', 'error', 'annoying', 'difficult', 'frustrating',
            'klappt nicht', 'funktioniert nicht', 'geht nicht'
        ],
        'patterns': [
            r'😞|😕|😐|👎',
            r'\bnicht\s+(gut|toll|schön|ok)\b',
            r'\bkein(e)?\s+(ahnung|plan|hilfe)\b'
        ],
        'score': -0.6
    }
    
    # Ängstlich/Gestresst
    ANXIOUS = {
        'keywords': [
            'stress', 'angst', 'sorge', 'nervös', 'unsicher', 'besorgt',
            'panik', 'druck', 'überwältigt', 'anxious', 'worried',
            'nervous', 'scared', 'afraid', 'overwhelmed', 'pressure'
        ],
        'patterns': [
            r'😰|😨|😱|😓',
            r'\b(zu viel|zu wenig)\s+(zeit|energie|kraft)\b',
            r'\bwas\s+wenn\b',
            r'\bhilfe\b.*\!'
        ],
        'score': -0.4
    }
    
    # Aufgeregt/Enthusiastisch
    EXCITED = {
        'keywords': [
            'aufgeregt', 'gespannt', 'vorfreude', 'kann kaum warten',
            'excited', 'eager', 'cant wait', 'looking forward'
        ],
        'patterns': [
            r'🤩|😃|🎊|🔥',
            r'\b(so|sehr)\s+gespannt\b',
            r'\bfreue\s+mich\s+(sehr|total|mega)\b'
        ],
        'score': 0.8
    }
    
    # Verwirrt/Unsicher
    CONFUSED = {
        'keywords': [
            'verwirrt', 'verstehe nicht', 'unklar', 'verstehe', 'weiß nicht',
            'confused', 'dont understand', 'not sure', 'unclear', 'huh',
            'was meinst du', 'wie geht das', 'was ist'
        ],
        'patterns': [
            r'🤔|😕|❓',
            r'\b(wie|was|wann|wo|warum)\s+.*\?',
            r'\?\?+',  # Mehrfache Fragezeichen
            r'\baber\s+(wie|was|warum)\b'
        ],
        'score': 0.0
    }


class SentimentAnalyzer:
    """
    Live Sentiment Analyzer.
    
    Analysiert User-Input in Echtzeit und erkennt emotionale Zustände.
    """
    
    def __init__(self):
        """Initialisiere Sentiment Analyzer."""
        self.emotion_markers = EmotionMarkers()
        self.sentiment_history: List[Tuple[str, SentimentCategory, float, datetime]] = []
    
    def analyze_sentiment(self, text: str) -> Dict:
        """
        Analysiere Sentiment eines Textes.
        
        Args:
            text: User-Input Text
            
        Returns:
            Dict mit Sentiment-Info:
            - category: SentimentCategory
            - score: Sentiment-Score (-1.0 bis 1.0)
            - confidence: Confidence-Level (0.0-1.0)
            - indicators: Gefundene Indikatoren
            - emotion_intensity: Intensität (0.0-1.0)
        """
        if not text or len(text.strip()) < 2:
            return self._neutral_response()
        
        text_lower = text.lower()
        
        # Sammle Scores von allen Kategorien
        category_scores = {
            SentimentCategory.VERY_POSITIVE: self._calculate_category_score(
                text_lower, text, self.emotion_markers.VERY_POSITIVE
            ),
            SentimentCategory.POSITIVE: self._calculate_category_score(
                text_lower, text, self.emotion_markers.POSITIVE
            ),
            SentimentCategory.VERY_NEGATIVE: self._calculate_category_score(
                text_lower, text, self.emotion_markers.VERY_NEGATIVE
            ),
            SentimentCategory.NEGATIVE: self._calculate_category_score(
                text_lower, text, self.emotion_markers.NEGATIVE
            ),
            SentimentCategory.ANXIOUS: self._calculate_category_score(
                text_lower, text, self.emotion_markers.ANXIOUS
            ),
            SentimentCategory.EXCITED: self._calculate_category_score(
                text_lower, text, self.emotion_markers.EXCITED
            ),
            SentimentCategory.CONFUSED: self._calculate_category_score(
                text_lower, text, self.emotion_markers.CONFUSED
            )
        }
        
        # Finde stärkste Kategorie
        best_category = max(category_scores.items(), key=lambda x: x[1]['total_score'])
        category, category_data = best_category
        
        # Wenn kein starkes Signal, dann Neutral
        if category_data['total_score'] < 0.3:
            return self._neutral_response()
        
        # Berechne finalen Sentiment-Score
        sentiment_score = self._calculate_final_score(category_scores)
        
        # Speichere in History
        self.sentiment_history.append((
            text[:50],  # Nur erste 50 Zeichen
            category,
            sentiment_score,
            datetime.now()
        ))
        
        # Behalte nur letzte 20 Einträge
        if len(self.sentiment_history) > 20:
            self.sentiment_history.pop(0)
        
        return {
            'category': category.value,
            'score': round(sentiment_score, 2),
            'confidence': round(category_data['confidence'], 2),
            'indicators': category_data['found_indicators'],
            'emotion_intensity': round(category_data['intensity'], 2),
            'timestamp': datetime.now().isoformat()
        }
    
    def _calculate_category_score(
        self,
        text_lower: str,
        text_original: str,
        marker_config: Dict
    ) -> Dict:
        """Berechne Score für eine Kategorie."""
        found_indicators = []
        keyword_matches = 0
        pattern_matches = 0
        
        # Keyword-Matching
        for keyword in marker_config['keywords']:
            if keyword.lower() in text_lower:
                keyword_matches += 1
                found_indicators.append(keyword)
        
        # Pattern-Matching
        for pattern in marker_config['patterns']:
            if re.search(pattern, text_original, re.IGNORECASE):
                pattern_matches += 1
                found_indicators.append(f"pattern:{pattern[:20]}")
        
        # Gesamtscore
        total_matches = keyword_matches + (pattern_matches * 1.5)  # Patterns wiegen mehr
        
        # Normalisierter Score (0.0-1.0)
        normalized_score = min(1.0, total_matches / 3)  # Max 3 Matches für 100%
        
        # Confidence basierend auf Anzahl Indikatoren
        confidence = min(1.0, len(found_indicators) / 2)  # 2+ Indikatoren = 100% Confidence
        
        # Intensität (wie stark ist die Emotion?)
        intensity = normalized_score * abs(marker_config['score'])
        
        return {
            'total_score': normalized_score * abs(marker_config['score']),
            'confidence': confidence,
            'found_indicators': found_indicators[:3],  # Max 3 zeigen
            'intensity': intensity
        }
    
    def _calculate_final_score(self, category_scores: Dict) -> float:
        """
        Berechne finalen Sentiment-Score (-1.0 bis 1.0).
        
        Kombiniert alle Kategorie-Scores zu einem Gesamt-Score.
        """
        weighted_sum = 0.0
        
        for category, data in category_scores.items():
            if category in [SentimentCategory.VERY_POSITIVE, SentimentCategory.EXCITED, SentimentCategory.POSITIVE]:
                weighted_sum += data['total_score']
            elif category in [SentimentCategory.VERY_NEGATIVE, SentimentCategory.NEGATIVE, SentimentCategory.ANXIOUS]:
                weighted_sum -= data['total_score']
            # CONFUSED und NEUTRAL bleiben bei 0
        
        # Normalisiere auf -1.0 bis 1.0
        return max(-1.0, min(1.0, weighted_sum))
    
    def _neutral_response(self) -> Dict:
        """Standard-Response für neutralen Sentiment."""
        return {
            'category': SentimentCategory.NEUTRAL.value,
            'score': 0.0,
            'confidence': 1.0,
            'indicators': [],
            'emotion_intensity': 0.0,
            'timestamp': datetime.now().isoformat()
        }
    
    def get_recommended_mood(self, sentiment_result: Dict) -> str:
        """
        Empfehle passenden Mood basierend auf Sentiment.
        
        Args:
            sentiment_result: Ergebnis von analyze_sentiment()
            
        Returns:
            Empfohlener MoodState (als String)
        """
        category = sentiment_result['category']
        
        mood_mapping = {
            SentimentCategory.VERY_POSITIVE.value: 'energetic',
            SentimentCategory.POSITIVE.value: 'playful',
            SentimentCategory.NEUTRAL.value: 'neutral',
            SentimentCategory.NEGATIVE.value: 'supportive',
            SentimentCategory.VERY_NEGATIVE.value: 'calm',
            SentimentCategory.ANXIOUS.value: 'supportive',
            SentimentCategory.EXCITED.value: 'energetic',
            SentimentCategory.CONFUSED.value: 'focused'
        }
        
        return mood_mapping.get(category, 'neutral')
    
    def get_response_modifier(self, sentiment_result: Dict) -> str:
        """
        Generiere Response-Modifier für System-Prompt.
        
        Args:
            sentiment_result: Ergebnis von analyze_sentiment()
            
        Returns:
            Modifier-String für System-Prompt
        """
        category = sentiment_result['category']
        intensity = sentiment_result['emotion_intensity']
        
        modifiers = {
            SentimentCategory.VERY_POSITIVE.value: 
                "Der User ist sehr positiv gestimmt! Teile ihre Begeisterung mit energetischer, freudiger Sprache. 🎉",
            
            SentimentCategory.POSITIVE.value: 
                "Der User ist gut gelaunt. Bleibe freundlich und positiv, aber nicht übertrieben enthusiastisch.",
            
            SentimentCategory.NEGATIVE.value: 
                "Der User wirkt frustriert oder unzufrieden. Sei besonders geduldig, verständnisvoll und lösungsorientiert.",
            
            SentimentCategory.VERY_NEGATIVE.value: 
                "Der User ist sehr negativ gestimmt oder aufgebracht. Reagiere mit maximaler Empathie, Ruhe und Unterstützung. Biete konkrete Hilfe an.",
            
            SentimentCategory.ANXIOUS.value: 
                "Der User wirkt gestresst oder ängstlich. Sei beruhigend, strukturiert und vermittle Sicherheit. Zeige Verständnis.",
            
            SentimentCategory.EXCITED.value: 
                "Der User ist aufgeregt und voller Energie! Teile die Begeisterung und sei motivierend.",
            
            SentimentCategory.CONFUSED.value: 
                "Der User ist verwirrt oder unsicher. Sei besonders klar, strukturiert und erklärend. Vermeide Fachjargon.",
            
            SentimentCategory.NEUTRAL.value: 
                "Der User kommuniziert neutral/sachlich. Bleibe professionell und informativ."
        }
        
        modifier = modifiers.get(category, modifiers[SentimentCategory.NEUTRAL.value])
        
        # Intensitäts-Boost
        if intensity > 0.7:
            modifier += f" Die Emotion ist stark ausgeprägt (Intensität: {intensity:.0%})."
        
        return modifier
    
    def get_sentiment_history(self, limit: int = 10) -> List[Dict]:
        """
        Hole Sentiment-History.
        
        Args:
            limit: Max Anzahl Einträge
            
        Returns:
            Liste von Sentiment-Einträgen
        """
        history = list(self.sentiment_history)[-limit:]
        return [
            {
                'text_preview': entry[0],
                'category': entry[1].value,
                'score': round(entry[2], 2),
                'timestamp': entry[3].isoformat()
            }
            for entry in history
        ]


# Singleton-Instanz
_sentiment_analyzer_instance = None


def get_sentiment_analyzer() -> SentimentAnalyzer:
    """Hole Sentiment Analyzer Singleton."""
    global _sentiment_analyzer_instance
    if _sentiment_analyzer_instance is None:
        _sentiment_analyzer_instance = SentimentAnalyzer()
    return _sentiment_analyzer_instance
