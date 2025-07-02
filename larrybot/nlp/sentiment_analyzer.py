import spacy
from larrybot.config.loader import Config

class SentimentAnalyzer:
    """
    Analyzes sentiment of user input using spaCy or a simple rule-based approach.
    """
    def __init__(self, config: Config = None):
        self.config = config
        self.enabled = getattr(config, 'NLP_ENABLED', True) if config else True
        self.model_name = getattr(config, 'NLP_MODEL', 'en_core_web_sm') if config else 'en_core_web_sm'
        self._nlp = None
        if self.enabled:
            try:
                self._nlp = spacy.load(self.model_name)
            except Exception:
                self._nlp = None
                self.enabled = False
        # Simple word lists for fallback
        self.positive_words = {"good", "great", "happy", "love", "excellent", "awesome", "fantastic", "progress"}
        self.negative_words = {"bad", "sad", "hate", "terrible", "awful", "frustrated", "angry", "problem"}

    def analyze_sentiment(self, text: str) -> str:
        """
        Analyze the input text and return the sentiment (e.g., 'positive', 'neutral', 'negative').
        """
        if not self.enabled:
            return "neutral"
        # spaCy does not have built-in sentiment in en_core_web_sm, so use rule-based fallback
        text_lower = text.lower()
        pos = any(word in text_lower for word in self.positive_words)
        neg = any(word in text_lower for word in self.negative_words)
        if pos and not neg:
            return "positive"
        if neg and not pos:
            return "negative"
        if pos and neg:
            return "neutral"
        return "neutral" 