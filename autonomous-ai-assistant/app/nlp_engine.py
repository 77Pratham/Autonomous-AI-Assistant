import spacy
from transformers import pipeline

class NLPEngine:
    """
    Handles Natural Language Processing for the AI Assistant.
    - Intent Classification using Zero-Shot Learning.
    - Entity Extraction using spaCy's Named Entity Recognition (NER).
    """
    def __init__(self):
        """
        Initializes the NLP models. This can be slow, so it's done once.
        """
        print("Loading NLP Engine models...")
        # Load a zero-shot classification pipeline for intent recognition
        self.intent_classifier = pipeline("zero-shot-classification", model="facebook/bart-large-mnli")

        # Load spaCy for named entity recognition
        self.nlp = spacy.load("en_core_web_sm")
        print("NLP Engine models loaded successfully.")

    def get_intent(self, text: str):
        """
        Determines the user's intent from a predefined list of tasks.
        """
        candidate_labels = [
            "File Management",
            "Email Handling",
            "Scheduling",
            "Data Analysis",
            "Document Generation",
            "IMS Integration",
            "General Chit-Chat"
        ]
        
        result = self.intent_classifier(text, candidate_labels)
        
        intent = {
            "label": result['labels'][0],
            "score": round(result['scores'][0], 2)
        }
        return intent

    def get_entities(self, text: str):
        """
        Extracts key entities (like dates, names, files) from the text.
        """
        doc = self.nlp(text)
        entities = []
        for ent in doc.ents:
            entities.append({
                "text": ent.text,
                "label": ent.label_
            })
        return entities

    def process_command(self, command: str):
        """
        Processes a user command to extract intent and entities.
        """
        if not command or not isinstance(command, str):
            return {
                "error": "Invalid command provided. Must be a non-empty string."
            }
            
        intent = self.get_intent(command)
        entities = self.get_entities(command)

        return {
            "command": command,
            "intent": intent,
            "entities": entities
        }