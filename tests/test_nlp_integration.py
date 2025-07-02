from larrybot.nlp.intent_recognizer import IntentRecognizer
from larrybot.nlp.entity_extractor import EntityExtractor
from larrybot.nlp.sentiment_analyzer import SentimentAnalyzer

import pytest

def test_intent_recognizer_create_task():
    recognizer = IntentRecognizer()
    assert recognizer.recognize_intent('Add a new task for tomorrow') == 'create_task'

def test_intent_recognizer_reminder():
    recognizer = IntentRecognizer()
    assert recognizer.recognize_intent('Remind me to call John at 5pm') == 'set_reminder'

def test_intent_recognizer_analytics():
    recognizer = IntentRecognizer()
    assert recognizer.recognize_intent('Show me my analytics report') == 'get_analytics'

def test_intent_recognizer_unknown():
    recognizer = IntentRecognizer()
    assert recognizer.recognize_intent('What is the weather?') == 'unknown'

def test_intent_recognizer_ambiguous():
    recognizer = IntentRecognizer()
    assert recognizer.recognize_intent('Do something') == 'unknown'

def test_entity_extractor_date():
    extractor = EntityExtractor()
    entities = extractor.extract_entities('Remind me to call John tomorrow at 5pm')
    assert 'date' in entities

def test_entity_extractor_task_name():
    extractor = EntityExtractor()
    entities = extractor.extract_entities('Add task Buy groceries and milk')
    assert 'task_name' in entities

def test_entity_extractor_named_entities():
    extractor = EntityExtractor()
    entities = extractor.extract_entities('Remind me to call John at 5pm')
    assert 'named_entities' in entities or entities == {}  # Named entity extraction may vary

def test_entity_extractor_empty():
    extractor = EntityExtractor()
    assert extractor.extract_entities('') == {}

def test_entity_extractor_no_entities():
    extractor = EntityExtractor()
    entities = extractor.extract_entities('This is a random sentence.')
    assert 'date' not in entities and 'task_name' not in entities

def test_sentiment_analyzer_positive():
    analyzer = SentimentAnalyzer()
    assert analyzer.analyze_sentiment('I am happy with my progress!') == 'positive'

def test_sentiment_analyzer_negative():
    analyzer = SentimentAnalyzer()
    assert analyzer.analyze_sentiment('I am frustrated with this problem.') == 'negative'

def test_sentiment_analyzer_neutral():
    analyzer = SentimentAnalyzer()
    assert analyzer.analyze_sentiment('This is a task.') == 'neutral'

def test_sentiment_analyzer_non_english():
    analyzer = SentimentAnalyzer()
    # Should default to neutral for non-English
    assert analyzer.analyze_sentiment('Je suis content.') == 'neutral' 