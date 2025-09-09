import spacy
from transformers import pipeline
import logging
import re
from typing import Dict, List, Any

logger = logging.getLogger(__name__)

class NLPEngine:
    """
    Handles Natural Language Processing for the AI Assistant.
    - Intent Classification using Zero-Shot Learning.
    - Entity Extraction using spaCy's Named Entity Recognition (NER).
    - Enhanced with better error handling and more robust processing.
    """
    def __init__(self):
        """
        Initializes the NLP models. This can be slow, so it's done once.
        """
        logger.info("Loading NLP Engine models...")
        
        try:
            # Load a zero-shot classification pipeline for intent recognition
            logger.info("Loading BART model for intent classification...")
            self.intent_classifier = pipeline(
                "zero-shot-classification", 
                model="facebook/bart-large-mnli",
                device=-1  # Use CPU
            )
            logger.info("BART model loaded successfully")
        except Exception as e:
            logger.error(f"Failed to load BART model: {e}")
            raise
        
        try:
            # Load spaCy for named entity recognition
            logger.info("Loading spaCy model...")
            self.nlp = spacy.load("en_core_web_sm")
            logger.info("spaCy model loaded successfully")
        except Exception as e:
            logger.error(f"Failed to load spaCy model: {e}")
            raise
        
        # Define candidate labels for intent classification
        self.candidate_labels = [
            "File Management",
            "Email Handling", 
            "Scheduling",
            "Data Analysis",
            "Document Generation",
            "IMS Integration",
            "General Chit-Chat"
        ]
        
        logger.info("NLP Engine models loaded successfully")

    def get_intent(self, text: str) -> Dict[str, Any]:
        """
        Determines the user's intent from a predefined list of tasks.
        
        Args:
            text: The input text to classify
            
        Returns:
            Dictionary containing the predicted intent and confidence score
        """
        try:
            if not text or not isinstance(text, str):
                return {"label": "General Chit-Chat", "score": 0.0}
            
            result = self.intent_classifier(text, self.candidate_labels)
            
            intent = {
                "label": result['labels'][0],
                "score": round(result['scores'][0], 3),
                "all_scores": {
                    label: round(score, 3) 
                    for label, score in zip(result['labels'], result['scores'])
                }
            }
            return intent
            
        except Exception as e:
            logger.error(f"Error in intent classification: {e}")
            return {"label": "General Chit-Chat", "score": 0.0, "error": str(e)}

    def get_entities(self, text: str) -> List[Dict[str, Any]]:
        """
        Extracts key entities (like dates, names, files) from the text.
        
        Args:
            text: The input text to extract entities from
            
        Returns:
            List of dictionaries containing entity information
        """
        try:
            if not text or not isinstance(text, str):
                return []
            
            doc = self.nlp(text)
            entities = []
            
            for ent in doc.ents:
                entities.append({
                    "text": ent.text,
                    "label": ent.label_,
                    "start": ent.start_char,
                    "end": ent.end_char,
                    "description": spacy.explain(ent.label_) or "Unknown"
                })
            
            # Add custom entity extraction for common patterns
            custom_entities = self._extract_custom_entities(text)
            entities.extend(custom_entities)
            
            return entities
            
        except Exception as e:
            logger.error(f"Error in entity extraction: {e}")
            return []

    def _extract_custom_entities(self, text: str) -> List[Dict[str, Any]]:
        """
        Extract custom entities using regex patterns.
        
        Args:
            text: The input text
            
        Returns:
            List of custom entities found
        """
        custom_entities = []
        
        try:
            # File extensions
            file_pattern = r'\b\w+\.(txt|pdf|doc|docx|xls|xlsx|ppt|pptx|jpg|png|gif|mp4|mp3|zip|rar)\b'
            for match in re.finditer(file_pattern, text, re.IGNORECASE):
                custom_entities.append({
                    "text": match.group(),
                    "label": "FILE",
                    "start": match.start(),
                    "end": match.end(),
                    "description": "File name"
                })
            
            # Email addresses
            email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
            for match in re.finditer(email_pattern, text):
                custom_entities.append({
                    "text": match.group(),
                    "label": "EMAIL",
                    "start": match.start(),
                    "end": match.end(),
                    "description": "Email address"
                })
            
            # Folder/directory names in quotes
            folder_pattern = r'(?:folder|directory).*?["\']([^"\']+)["\']'
            for match in re.finditer(folder_pattern, text, re.IGNORECASE):
                custom_entities.append({
                    "text": match.group(1),
                    "label": "FOLDER",
                    "start": match.start(1),
                    "end": match.end(1),
                    "description": "Folder name"
                })
            
        except Exception as e:
            logger.error(f"Error in custom entity extraction: {e}")
        
        return custom_entities

    def extract_key_parameters(self, text: str, intent_label: str) -> Dict[str, Any]:
        """
        Extract key parameters based on the intent.
        
        Args:
            text: The input text
            intent_label: The classified intent
            
        Returns:
            Dictionary of extracted parameters
        """
        parameters = {}
        
        try:
            if intent_label == "File Management":
                # Extract folder/file names
                folder_match = re.search(r'(?:folder|directory).*?(?:named|called)\s+["\']?([^"\']+)["\']?', text, re.IGNORECASE)
                if folder_match:
                    parameters["folder_name"] = folder_match.group(1).strip()
                
                # Extract actions
                if any(word in text.lower() for word in ['create', 'make', 'new']):
                    parameters["action"] = "create"
                elif any(word in text.lower() for word in ['delete', 'remove']):
                    parameters["action"] = "delete"
                elif any(word in text.lower() for word in ['list', 'show', 'display']):
                    parameters["action"] = "list"
            
            elif intent_label == "Scheduling":
                # Extract time-related information
                time_patterns = [
                    r'(\d{1,2}:\d{2}(?:\s?[AP]M)?)',
                    r'(\d{1,2}\s?[AP]M)',
                    r'(tomorrow|today|yesterday)',
                    r'(monday|tuesday|wednesday|thursday|friday|saturday|sunday)',
                    r'(\d{1,2}/\d{1,2}/\d{4})'
                ]
                
                for pattern in time_patterns:
                    matches = re.findall(pattern, text, re.IGNORECASE)
                    if matches:
                        parameters.setdefault("time_expressions", []).extend(matches)
            
            elif intent_label == "Email Handling":
                # Extract email-related parameters
                if any(word in text.lower() for word in ['send', 'compose', 'write']):
                    parameters["action"] = "send"
                elif any(word in text.lower() for word in ['read', 'check', 'show']):
                    parameters["action"] = "read"
                elif any(word in text.lower() for word in ['summarize', 'summary']):
                    parameters["action"] = "summarize"
        
        except Exception as e:
            logger.error(f"Error extracting parameters: {e}")
        
        return parameters

    def process_command(self, command: str) -> Dict[str, Any]:
        """
        Processes a user command to extract intent, entities, and parameters.
        
        Args:
            command: The user's command as a string
            
        Returns:
            Dictionary containing all processed information
        """
        if not command or not isinstance(command, str):
            return {
                "error": "Invalid command provided. Must be a non-empty string."
            }
        
        # Clean the command
        command = command.strip()
        
        try:
            # Get intent classification
            intent = self.get_intent(command)
            
            # Extract entities
            entities = self.get_entities(command)
            
            # Extract key parameters based on intent
            parameters = self.extract_key_parameters(command, intent.get('label', ''))
            
            # Determine confidence level
            confidence_score = intent.get('score', 0.0)
            if confidence_score > 0.8:
                confidence_level = "high"
            elif confidence_score > 0.5:
                confidence_level = "medium"
            else:
                confidence_level = "low"
            
            return {
                "command": command,
                "intent": intent,
                "entities": entities,
                "parameters": parameters,
                "confidence_level": confidence_level,
                "status": "success"
            }
            
        except Exception as e:
            logger.error(f"Error processing command: {e}")
            return {
                "command": command,
                "error": str(e),
                "status": "error"
            }