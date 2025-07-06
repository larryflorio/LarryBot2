import spacy
from larrybot.config.loader import Config


class IntentRecognizer:
    """
    Recognizes user intent from natural language input using spaCy and rule-based matching.
    """

    def __init__(self, config: Config=None):
        self.config = config
        self.enabled = getattr(config, 'NLP_ENABLED', True) if config else True
        self.model_name = getattr(config, 'NLP_MODEL', 'en_core_web_sm'
            ) if config else 'en_core_web_sm'
        self._nlp = None
        if self.enabled:
            try:
                self._nlp = spacy.load(self.model_name)
            except Exception:
                self._nlp = None
                self.enabled = False

    def recognize_intent(self, text: str) ->str:
        """
        Analyze the input text and return the detected intent as a string.
        Supported intents: create_task, set_reminder, get_analytics, edit_task, unknown.
        """
        if not self.enabled or not self._nlp:
            return 'unknown'
        doc = self._nlp(text.lower())
        if any(w in text.lower() for w in ['add task', 'create task',
            'new task', 'todo']):
            return 'create_task'
        if any(w in text.lower() for w in ['remind', 'reminder', 'remind me']):
            return 'set_reminder'
        if any(w in text.lower() for w in ['analytics', 'stats', 'report']):
            return 'get_analytics'
        if any(w in text.lower() for w in ['edit task', 'change task',
            'update task']):
            return 'edit_task'
        for token in doc:
            if token.lemma_ == 'add' and 'task' in text:
                return 'create_task'
            if token.lemma_ == 'remind':
                return 'set_reminder'
        return 'unknown'
