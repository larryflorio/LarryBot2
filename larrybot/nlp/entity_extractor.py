import spacy
from dateparser import parse as parse_date
from larrybot.config.loader import Config


class EntityExtractor:
    """
    Extracts entities (e.g., dates, times, task names) from natural language input using spaCy and dateparser.
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

    def extract_entities(self, text: str) ->dict:
        """
        Analyze the input text and return a dictionary of extracted entities.
        Extracts: date, time, task_name (if possible).
        'date' is always set to the first found date (dateparser or spaCy NER).
        'all_dates' contains all found dates (optional).
        """
        if not self.enabled or not self._nlp:
            return {}
        doc = self._nlp(text)
        entities = {}
        all_dates = []
        date = parse_date(text, settings={'PREFER_DATES_FROM': 'future'})
        if date:
            all_dates.append(date.isoformat())
        for ent in doc.ents:
            if ent.label_ in ['DATE', 'TIME']:
                parsed = parse_date(ent.text, settings={'PREFER_DATES_FROM':
                    'future'})
                if parsed:
                    all_dates.append(parsed.isoformat())
            if ent.label_ in ['PERSON', 'ORG', 'GPE']:
                entities.setdefault('named_entities', []).append({'text':
                    ent.text, 'label': ent.label_})
        if all_dates:
            entities['date'] = all_dates[0]
            entities['all_dates'] = all_dates
        for i, token in enumerate(doc):
            if token.lemma_ in ['task', 'remind'] and i + 1 < len(doc):
                next_chunk = doc[i + 1:].text.strip()
                if next_chunk:
                    entities['task_name'] = next_chunk
                    break
        return entities
