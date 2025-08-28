from flask import Flask, request, jsonify
from .nlp_engine import NLPEngine
from .rag_system import RAGSystem
from .automation_scripts import file_management # <-- IMPORT THE NEW SCRIPT

app = Flask(__name__)

# Initialize the core systems once when the application starts
try:
    nlp_engine = NLPEngine()
    rag_system = RAGSystem()
except Exception as e:
    nlp_engine = None
    rag_system = None
    print(f"FATAL: Could not load AI systems. Error: {e}")

@app.route('/')
def index():
    return "AI Assistant API is running."

# --- NLP and RAG Endpoints ---

@app.route('/process', methods=['POST'])
def process():
    # ... (code for this endpoint is unchanged)
    if nlp_engine is None: return jsonify({"error": "NLP Engine is not available."}), 503
    data = request.get_json()
    if not data or 'command' not in data: return jsonify({"error": "Invalid request. 'command' key is required."}), 400
    command = data['command']
    try:
        processed_data = nlp_engine.process_command(command)
        return jsonify(processed_data)
    except Exception as e:
        print(f"Error processing command: {e}")
        return jsonify({"error": "An internal error occurred."}), 500


@app.route('/add_context', methods=['POST'])
def add_context():
    # ... (code for this endpoint is unchanged)
    if rag_system is None: return jsonify({"error": "RAG System is not available."}), 503
    data = request.get_json()
    if not data or 'text' not in data: return jsonify({"error": "Invalid request. 'text' key is required."}), 400
    text = data['text']
    rag_system.add_document(text)
    return jsonify({"message": "Context added successfully."}), 201


@app.route('/get_context', methods=['POST'])
def get_context():
    # ... (code for this endpoint is unchanged)
    if rag_system is None: return jsonify({"error": "RAG System is not available."}), 503
    data = request.get_json()
    if not data or 'query' not in data: return jsonify({"error": "Invalid request. 'query' key is required."}), 400
    query = data['query']
    results = rag_system.retrieve(query)
    return jsonify(results)


# --- NEW EXECUTION ENDPOINT ---

@app.route('/execute/file_management', methods=['POST'])
def execute_file_management():
    data = request.get_json()
    action = data.get('action')
    parameters = data.get('parameters', {})

    if action == 'create_folder':
        folder_name = parameters.get('folder_name')
        if not folder_name:
            return jsonify({"status": "error", "message": "'folder_name' parameter is required."}), 400
        
        result = file_management.create_folder(folder_name)
        return jsonify(result)
    
    return jsonify({"status": "error", "message": "Unknown action."}), 400


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)