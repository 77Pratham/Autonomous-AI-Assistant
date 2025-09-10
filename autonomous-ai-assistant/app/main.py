import os
import logging
from flask import Flask, request, jsonify
from flask_cors import CORS
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Import our modules with proper error handling
try:
    from app.nlp_engine import NLPEngine
    from app.rag_system import RAGSystem
    from app.automation_scripts import file_management
except ImportError as e:
    logger.error(f"Import error: {e}")
    # Fall back to absolute imports
    try:
        from nlp_engine import NLPEngine
        from rag_system import RAGSystem
        from automation_scripts import file_management
    except ImportError as e2:
        logger.fatal(f"Failed to import modules: {e2}")
        raise

app = Flask(__name__)
CORS(app)  # Enable CORS for web interface

# Global variables for our AI systems
nlp_engine = None
rag_system = None

def initialize_systems():
    """Initialize the AI systems with proper error handling"""
    global nlp_engine, rag_system
    
    try:
        logger.info("Initializing NLP Engine...")
        nlp_engine = NLPEngine()
        logger.info("NLP Engine initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize NLP Engine: {e}")
        nlp_engine = None

    try:
        logger.info("Initializing RAG System...")
        rag_system = RAGSystem()
        logger.info("RAG System initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize RAG System: {e}")
        rag_system = None

# Initialize systems when the module is loaded
initialize_systems()

@app.route('/')
def index():
    """Health check endpoint"""
    status = {
        "status": "running",
        "nlp_engine": "available" if nlp_engine else "unavailable",
        "rag_system": "available" if rag_system else "unavailable"
    }
    return jsonify(status)

@app.route('/health')
def health():
    """Detailed health check"""
    return jsonify({
        "status": "healthy",
        "services": {
            "nlp_engine": nlp_engine is not None,
            "rag_system": rag_system is not None
        }
    })

# --- NLP and RAG Endpoints ---

@app.route('/process', methods=['POST'])
def process():
    """Process a command through the NLP engine"""
    if nlp_engine is None:
        return jsonify({"error": "NLP Engine is not available"}), 503
    
    try:
        data = request.get_json()
        if not data or 'command' not in data:
            return jsonify({"error": "Invalid request. 'command' key is required"}), 400
        
        command = data['command']
        if not isinstance(command, str) or not command.strip():
            return jsonify({"error": "Command must be a non-empty string"}), 400
        
        processed_data = nlp_engine.process_command(command)
        return jsonify(processed_data)
        
    except Exception as e:
        logger.error(f"Error processing command: {e}")
        return jsonify({"error": "An internal error occurred"}), 500

@app.route('/add_context', methods=['POST'])
def add_context():
    """Add a document to the RAG system"""
    if rag_system is None:
        return jsonify({"error": "RAG System is not available"}), 503
    
    try:
        data = request.get_json()
        if not data or 'text' not in data:
            return jsonify({"error": "Invalid request. 'text' key is required"}), 400
        
        text = data['text']
        if not isinstance(text, str) or not text.strip():
            return jsonify({"error": "Text must be a non-empty string"}), 400
        
        rag_system.add_document(text)
        return jsonify({"message": "Context added successfully"}), 201
        
    except Exception as e:
        logger.error(f"Error adding context: {e}")
        return jsonify({"error": "An internal error occurred"}), 500

@app.route('/get_context', methods=['POST'])
def get_context():
    """Retrieve relevant context from the RAG system"""
    if rag_system is None:
        return jsonify({"error": "RAG System is not available"}), 503
    
    try:
        data = request.get_json()
        if not data or 'query' not in data:
            return jsonify({"error": "Invalid request. 'query' key is required"}), 400
        
        query = data['query']
        k = data.get('k', 3)  # Number of results to return
        
        if not isinstance(query, str) or not query.strip():
            return jsonify({"error": "Query must be a non-empty string"}), 400
        
        results = rag_system.retrieve(query, k)
        return jsonify(results)
        
    except Exception as e:
        logger.error(f"Error retrieving context: {e}")
        return jsonify({"error": "An internal error occurred"}), 500

# --- Execution Endpoints ---

@app.route('/execute/file_management', methods=['POST'])
def execute_file_management():
    """Execute file management operations"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "Invalid request. JSON data required"}), 400
        
        action = data.get('action')
        parameters = data.get('parameters', {})
        
        if not action:
            return jsonify({"error": "'action' parameter is required"}), 400
        
        if action == 'create_folder':
            folder_name = parameters.get('folder_name')
            base_path = parameters.get('path', '/usr/src/app/data/output')
            
            if not folder_name:
                return jsonify({
                    "status": "error", 
                    "message": "'folder_name' parameter is required"
                }), 400
            
            result = file_management.create_folder(folder_name, base_path)
            return jsonify(result)
        
        elif action == 'list_files':
            path = parameters.get('path', '/usr/src/app/data/output')
            result = file_management.list_files(path)
            return jsonify(result)
        
        else:
            return jsonify({
                "status": "error", 
                "message": f"Unknown action: {action}"
            }), 400
            
    except Exception as e:
        logger.error(f"Error in file management execution: {e}")
        return jsonify({"error": "An internal error occurred"}), 500

@app.route('/execute/smart_command', methods=['POST'])
def execute_smart_command():
    """Execute a command intelligently using NLP + execution"""
    if nlp_engine is None:
        return jsonify({"error": "NLP Engine is not available"}), 503
    
    try:
        data = request.get_json()
        if not data or 'command' not in data:
            return jsonify({"error": "Invalid request. 'command' key is required"}), 400
        
        command = data['command']
        
        # First, process the command through NLP
        processed = nlp_engine.process_command(command)
        
        # Then execute based on intent
        intent_label = processed.get('intent', {}).get('label', '')
        entities = processed.get('entities', [])
        
        result = {
            "processed_command": processed,
            "execution_result": None
        }
        
        if intent_label == 'File Management':
            # Extract folder name from entities or command
            folder_name = None
            for entity in entities:
                if entity.get('label') in ['WORK_OF_ART', 'PRODUCT', 'ORG']:
                    folder_name = entity.get('text')
                    break
            
            if not folder_name:
                # Simple extraction from command
                import re
                match = re.search(r'(?:folder|directory).*?(?:named|called)\s+["\']?([^"\']+)["\']?', command, re.IGNORECASE)
                if match:
                    folder_name = match.group(1).strip()
            
            if folder_name:
                exec_result = file_management.create_folder(folder_name)
                result["execution_result"] = exec_result
            else:
                result["execution_result"] = {
                    "status": "error",
                    "message": "Could not extract folder name from command"
                }
        
        else:
            result["execution_result"] = {
                "status": "info",
                "message": f"Intent '{intent_label}' recognized but execution not implemented yet"
            }
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Error in smart command execution: {e}")
        return jsonify({"error": "An internal error occurred"}), 500

@app.errorhandler(404)
def not_found(error):
    return jsonify({"error": "Endpoint not found"}), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({"error": "Internal server error"}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)