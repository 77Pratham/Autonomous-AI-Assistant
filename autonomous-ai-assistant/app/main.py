import os
import logging
from flask import Flask, request, jsonify, render_template_string, send_from_directory
from flask_cors import CORS
from dotenv import load_dotenv
from datetime import datetime
import json

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=getattr(logging, os.getenv('LOG_LEVEL', 'INFO')),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Import our modules with proper error handling
try:
    from app.nlp_engine import NLPEngine
    from app.rag_system import RAGSystem
    from app.automation_scripts import file_management
    from app.automation_scripts.email_handler import EmailHandler, send_email, read_unread_emails, summarize_recent_emails
    from app.automation_scripts.data_analysis import DataAnalyzer, analyze_data_file, quick_data_summary
    from app.api_integrations.google_calendar import CalendarIntegration, create_meeting_from_command, get_daily_schedule
except ImportError as e:
    logger.error(f"Import error: {e}")
    # Fall back to absolute imports
    try:
        from nlp_engine import NLPEngine
        from rag_system import RAGSystem
        from automation_scripts import file_management
        from automation_scripts.email_handler import EmailHandler, send_email, read_unread_emails, summarize_recent_emails
        from automation_scripts.data_analysis import DataAnalyzer, analyze_data_file, quick_data_summary
        from api_integrations.google_calendar import CalendarIntegration, create_meeting_from_command, get_daily_schedule
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

# HTML template for the web interface
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Autonomous AI Assistant</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 0; padding: 20px; background: #f5f5f5; }
        .container { max-width: 1200px; margin: 0 auto; }
        .header { text-align: center; margin-bottom: 30px; }
        .card { background: white; padding: 30px; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); margin-bottom: 20px; }
        .btn { padding: 12px 24px; margin: 5px; border: none; border-radius: 5px; cursor: pointer; font-size: 16px; }
        .btn-primary { background: #007bff; color: white; }
        .btn-success { background: #28a745; color: white; }
        .btn-info { background: #17a2b8; color: white; }
        .endpoint { margin: 20px 0; padding: 15px; background: #f8f9fa; border-radius: 5px; }
        .method { font-weight: bold; color: #007bff; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🤖 Autonomous AI Assistant</h1>
            <p>Your intelligent assistant for automation tasks</p>
        </div>
        
        <div class="card">
            <h2>System Status</h2>
            <p><strong>NLP Engine:</strong> {{ 'Available' if nlp_available else 'Unavailable' }}</p>
            <p><strong>RAG System:</strong> {{ 'Available' if rag_available else 'Unavailable' }}</p>
            <p><strong>Email Handler:</strong> Available</p>
            <p><strong>Calendar Integration:</strong> Available (Mock Mode)</p>
            <p><strong>Data Analyzer:</strong> Available</p>
        </div>
        
        <div class="card">
            <h2>🚀 Quick Actions</h2>
            <button class="btn btn-primary" onclick="testCommand()">Test NLP Processing</button>
            <button class="btn btn-success" onclick="createFolder()">Create Test Folder</button>
            <button class="btn btn-info" onclick="scheduleDemo()">Schedule Demo Meeting</button>
        </div>
        
        <div class="card">
            <h2>📚 Available Endpoints</h2>
            
            <div class="endpoint">
                <span class="method">POST</span> <strong>/process</strong> - Process commands through NLP
                <pre>curl -X POST /process -H "Content-Type: application/json" -d '{"command": "Create a folder named test"}'</pre>
            </div>
            
            <div class="endpoint">
                <span class="method">POST</span> <strong>/execute/smart_command</strong> - Smart end-to-end command execution
                <pre>curl -X POST /execute/smart_command -H "Content-Type: application/json" -d '{"command": "Schedule meeting tomorrow at 3pm"}'</pre>
            </div>
            
            <div class="endpoint">
                <span class="method">POST</span> <strong>/execute/file_management</strong> - File operations
                <pre>curl -X POST /execute/file_management -H "Content-Type: application/json" -d '{"action": "list_files"}'</pre>
            </div>
            
            <div class="endpoint">
                <span class="method">POST</span> <strong>/execute/email</strong> - Email operations
                <pre>curl -X POST /execute/email -H "Content-Type: application/json" -d '{"action": "read_unread"}'</pre>
            </div>
            
            <div class="endpoint">
                <span class="method">POST</span> <strong>/execute/calendar</strong> - Calendar operations
                <pre>curl -X POST /execute/calendar -H "Content-Type: application/json" -d '{"action": "get_schedule"}'</pre>
            </div>
            
            <div class="endpoint">
                <span class="method">POST</span> <strong>/execute/data_analysis</strong> - Data analysis operations
                <pre>curl -X POST /execute/data_analysis -H "Content-Type: application/json" -d '{"action": "analyze", "file_path": "/path/to/data.csv"}'</pre>
            </div>
        </div>
    </div>
    
    <script>
        function testCommand() {
            fetch('/process', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({command: 'Create a folder named TestFolder'})
            }).then(r => r.json()).then(data => alert(JSON.stringify(data, null, 2)));
        }
        
        function createFolder() {
            fetch('/execute/file_management', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({action: 'create_folder', parameters: {folder_name: 'DemoFolder'}})
            }).then(r => r.json()).then(data => alert(JSON.stringify(data, null, 2)));
        }
        
        function scheduleDemo() {
            fetch('/execute/calendar', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({action: 'schedule_quick', parameters: {title: 'Demo Meeting', hours_from_now: 2}})
            }).then(r => r.json()).then(data => alert(JSON.stringify(data, null, 2)));
        }
    </script>
</body>
</html>
"""

@app.route('/')
def index():
    """Serve the main web interface"""
    return render_template_string(HTML_TEMPLATE, 
                                nlp_available=nlp_engine is not None,
                                rag_available=rag_system is not None)

@app.route('/health')
def health():
    """Detailed health check"""
    return jsonify({
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "services": {
            "nlp_engine": nlp_engine is not None,
            "rag_system": rag_system is not None,
            "email_handler": True,
            "calendar_integration": True,
            "data_analyzer": True,
            "file_management": True
        }
    })

@app.route('/api/status')
def api_status():
    """API status endpoint"""
    return jsonify({
        "api_version": "2.0",
        "status": "operational",
        "endpoints": [
            "/process", "/execute/smart_command", "/execute/file_management",
            "/execute/email", "/execute/calendar", "/execute/data_analysis",
            "/add_context", "/get_context"
        ]
    })

# --- Core NLP and RAG Endpoints ---

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
        
        result = rag_system.add_document(text)
        if result:
            return jsonify({"message": "Context added successfully"}), 201
        else:
            return jsonify({"error": "Failed to add context"}), 500
        
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
        k = data.get('k', 3)
        
        if not isinstance(query, str) or not query.strip():
            return jsonify({"error": "Query must be a non-empty string"}), 400
        
        results = rag_system.retrieve(query, k)
        return jsonify(results)
        
    except Exception as e:
        logger.error(f"Error retrieving context: {e}")
        return jsonify({"error": "An internal error occurred"}), 500

# --- Enhanced Execution Endpoints ---

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
            "execution_result": None,
            "timestamp": datetime.now().isoformat()
        }
        
        # Route to appropriate execution module
        if intent_label == 'File Management':
            result["execution_result"] = execute_file_management_intent(command, entities)
            
        elif intent_label == 'Email Handling':
            result["execution_result"] = execute_email_intent(command, entities)
            
        elif intent_label == 'Scheduling':
            result["execution_result"] = execute_calendar_intent(command, entities)
            
        elif intent_label == 'Data Analysis':
            result["execution_result"] = execute_data_analysis_intent(command, entities)
            
        else:
            result["execution_result"] = {
                "status": "info",
                "message": f"Intent '{intent_label}' recognized but execution not implemented yet"
            }
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Error in smart command execution: {e}")
        return jsonify({"error": "An internal error occurred"}), 500

def execute_file_management_intent(command, entities):
    """Execute file management operations based on NLP analysis"""
    try:
        # Extract folder/file name from entities or command
        folder_name = None
        for entity in entities:
            if entity.get('label') in ['WORK_OF_ART', 'PRODUCT', 'ORG', 'FOLDER']:
                folder_name = entity.get('text')
                break
        
        # Fallback extraction
        if not folder_name:
            import re
            patterns = [
                r'(?:folder|directory).*?(?:named|called)\s+["\']?([^"\']+)["\']?',
                r'create\s+["\']?([^"\']+)["\']?',
            ]
            for pattern in patterns:
                match = re.search(pattern, command, re.IGNORECASE)
                if match:
                    folder_name = match.group(1).strip()
                    break
        
        # Determine action
        if any(word in command.lower() for word in ['create', 'make', 'new']):
            if folder_name:
                return file_management.create_folder(folder_name)
            else:
                return {"status": "error", "message": "Could not extract folder name from command"}
        elif any(word in command.lower() for word in ['list', 'show', 'display']):
            return file_management.list_files()
        else:
            return {"status": "error", "message": "Could not determine file management action"}
            
    except Exception as e:
        return {"status": "error", "message": f"File management execution failed: {e}"}

def execute_email_intent(command, entities):
    """Execute email operations based on NLP analysis"""
    try:
        if any(word in command.lower() for word in ['read', 'check', 'show', 'unread']):
            return {"status": "info", "message": "Email reading functionality available but requires configuration"}
        elif any(word in command.lower() for word in ['send', 'compose', 'write']):
            return {"status": "info", "message": "Email sending functionality available but requires configuration"}
        elif any(word in command.lower() for word in ['summarize', 'summary']):
            return {"status": "info", "message": "Email summarization functionality available but requires configuration"}
        else:
            return {"status": "info", "message": "Email functionality recognized but requires specific action"}
            
    except Exception as e:
        return {"status": "error", "message": f"Email execution failed: {e}"}

def execute_calendar_intent(command, entities):
    """Execute calendar operations based on NLP analysis"""
    try:
        if any(word in command.lower() for word in ['schedule', 'create', 'meeting', 'appointment']):
            result = create_meeting_from_command(command)
            return result
        elif any(word in command.lower() for word in ['show', 'display', 'today', 'schedule']):
            result = get_daily_schedule()
            return result
        else:
            return {"status": "info", "message": "Calendar functionality recognized but requires specific action"}
            
    except Exception as e:
        return {"status": "error", "message": f"Calendar execution failed: {e}"}

def execute_data_analysis_intent(command, entities):
    """Execute data analysis operations based on NLP analysis"""
    try:
        return {
            "status": "info", 
            "message": "Data analysis functionality available. Please use /execute/data_analysis endpoint with specific file path"
        }
            
    except Exception as e:
        return {"status": "error", "message": f"Data analysis execution failed: {e}"}

# --- Specific Execution Endpoints ---

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
            
        elif action == 'list_files':
            path = parameters.get('path', '/usr/src/app/data/output')
            result = file_management.list_files(path)
            
        elif action == 'delete':
            path = parameters.get('path')
            force = parameters.get('force', False)
            if not path:
                return jsonify({"status": "error", "message": "'path' parameter is required"}), 400
            result = file_management.delete_file_or_folder(path, force)
            
        elif action == 'move':
            source_path = parameters.get('source_path')
            dest_path = parameters.get('destination_path')
            if not source_path or not dest_path:
                return jsonify({"status": "error", "message": "Both 'source_path' and 'destination_path' required"}), 400
            result = file_management.move_file_or_folder(source_path, dest_path)
            
        elif action == 'copy':
            source_path = parameters.get('source_path')
            dest_path = parameters.get('destination_path')
            if not source_path or not dest_path:
                return jsonify({"status": "error", "message": "Both 'source_path' and 'destination_path' required"}), 400
            result = file_management.copy_file_or_folder(source_path, dest_path)
            
        elif action == 'create_file':
            file_name = parameters.get('file_name')
            content = parameters.get('content', '')
            path = parameters.get('path', '/usr/src/app/data/output')
            if not file_name:
                return jsonify({"status": "error", "message": "'file_name' parameter is required"}), 400
            result = file_management.create_file(file_name, content, path)
            
        elif action == 'read_file':
            file_path = parameters.get('file_path')
            if not file_path:
                return jsonify({"status": "error", "message": "'file_path' parameter is required"}), 400
            result = file_management.read_file(file_path)
            
        else:
            return jsonify({
                "status": "error", 
                "message": f"Unknown action: {action}. Available actions: create_folder, list_files, delete, move, copy, create_file, read_file"
            }), 400
            
        return jsonify(result)
            
    except Exception as e:
        logger.error(f"Error in file management execution: {e}")
        return jsonify({"error": "An internal error occurred"}), 500

@app.route('/execute/email', methods=['POST'])
def execute_email():
    """Execute email operations"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "Invalid request. JSON data required"}), 400
        
        action = data.get('action')
        parameters = data.get('parameters', {})
        
        if not action:
            return jsonify({"error": "'action' parameter is required"}), 400
        
        if action == 'send':
            to_emails = parameters.get('to_emails', [])
            subject = parameters.get('subject', '')
            body = parameters.get('body', '')
            
            if not to_emails or not subject or not body:
                return jsonify({
                    "status": "error",
                    "message": "to_emails, subject, and body parameters are required"
                }), 400
                
            result = send_email(to_emails, subject, body, **parameters)
            
        elif action == 'read_unread':
            limit = parameters.get('limit', 10)
            since_days = parameters.get('since_days', 1)
            result = read_unread_emails(limit, since_days)
            
        elif action == 'summarize':
            days = parameters.get('days', 1)
            limit = parameters.get('limit', 10)
            result = summarize_recent_emails(days, limit)
            
        else:
            return jsonify({
                "status": "error",
                "message": f"Unknown action: {action}. Available actions: send, read_unread, summarize"
            }), 400
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Error in email execution: {e}")
        return jsonify({"error": "An internal error occurred"}), 500

@app.route('/execute/calendar', methods=['POST'])
def execute_calendar():
    """Execute calendar operations"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "Invalid request. JSON data required"}), 400
        
        action = data.get('action')
        parameters = data.get('parameters', {})
        
        if not action:
            return jsonify({"error": "'action' parameter is required"}), 400
        
        calendar = CalendarIntegration()
        
        if action == 'create_from_command':
            command = parameters.get('command', '')
            if not command:
                return jsonify({"status": "error", "message": "'command' parameter is required"}), 400
            result = create_meeting_from_command(command)
            
        elif action == 'get_schedule':
            result = get_daily_schedule()
            
        elif action == 'get_week':
            result = calendar.get_week_schedule()
            
        elif action == 'schedule_quick':
            title = parameters.get('title', 'Quick Meeting')
            attendee_emails = parameters.get('attendee_emails', [])
            hours_from_now = parameters.get('hours_from_now', 1)
            
            from automation_scripts.google_calendar import schedule_quick_meeting
            result = schedule_quick_meeting(title, attendee_emails, hours_from_now)
            
        elif action == 'find_free_slots':
            from datetime import datetime, timedelta
            date = parameters.get('date')
            if date:
                date = datetime.fromisoformat(date)
            else:
                date = datetime.now() + timedelta(days=1)  # Default to tomorrow
                
            duration_hours = parameters.get('duration_hours', 1.0)
            working_hours = tuple(parameters.get('working_hours', [9, 17]))
            
            result = calendar.find_free_time_slots(date, duration_hours, working_hours)
            
        else:
            return jsonify({
                "status": "error",
                "message": f"Unknown action: {action}. Available actions: create_from_command, get_schedule, get_week, schedule_quick, find_free_slots"
            }), 400
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Error in calendar execution: {e}")
        return jsonify({"error": "An internal error occurred"}), 500

@app.route('/execute/data_analysis', methods=['POST'])
def execute_data_analysis():
    """Execute data analysis operations"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "Invalid request. JSON data required"}), 400
        
        action = data.get('action')
        parameters = data.get('parameters', {})
        
        if not action:
            return jsonify({"error": "'action' parameter is required"}), 400
        
        if action == 'analyze':
            file_path = parameters.get('file_path')
            if not file_path:
                return jsonify({"status": "error", "message": "'file_path' parameter is required"}), 400
            
            generate_viz = parameters.get('generate_visualizations', True)
            report_format = parameters.get('report_format', 'json')
            
            result = analyze_data_file(file_path, generate_viz, report_format)
            
        elif action == 'quick_summary':
            file_path = parameters.get('file_path')
            if not file_path:
                return jsonify({"status": "error", "message": "'file_path' parameter is required"}), 400
                
            result = quick_data_summary(file_path)
            
        elif action == 'compare':
            file_paths = parameters.get('file_paths', [])
            if len(file_paths) < 2:
                return jsonify({"status": "error", "message": "At least 2 file paths required for comparison"}), 400
                
            analyzer = DataAnalyzer()
            result = analyzer.compare_datasets(file_paths)
            
        else:
            return jsonify({
                "status": "error",
                "message": f"Unknown action: {action}. Available actions: analyze, quick_summary, compare"
            }), 400
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Error in data analysis execution: {e}")
        return jsonify({"error": "An internal error occurred"}), 500

# --- File Upload and Management ---

@app.route('/upload', methods=['POST'])
def upload_file():
    """Upload files for analysis"""
    try:
        if 'file' not in request.files:
            return jsonify({"error": "No file provided"}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({"error": "No file selected"}), 400
        
        # Save file to upload directory
        upload_dir = '/usr/src/app/data/uploads'
        os.makedirs(upload_dir, exist_ok=True)
        
        file_path = os.path.join(upload_dir, file.filename)
        file.save(file_path)
        
        # Basic file info
        file_info = {
            "filename": file.filename,
            "path": file_path,
            "size": os.path.getsize(file_path),
            "uploaded_at": datetime.now().isoformat()
        }
        
        # If it's a CSV, provide quick analysis
        if file.filename.lower().endswith('.csv'):
            try:
                summary = quick_data_summary(file_path)
                file_info["quick_analysis"] = summary
            except Exception as e:
                logger.warning(f"Failed to analyze uploaded CSV: {e}")
        
        return jsonify({
            "status": "success",
            "message": "File uploaded successfully",
            "file_info": file_info
        })
        
    except Exception as e:
        logger.error(f"Error uploading file: {e}")
        return jsonify({"error": "File upload failed"}), 500

@app.route('/download/<path:filename>')
def download_file(filename):
    """Download generated files"""
    try:
        return send_from_directory('/usr/src/app/data/output', filename, as_attachment=True)
    except Exception as e:
        logger.error(f"Error downloading file: {e}")
        return jsonify({"error": "File not found"}), 404

# --- System Management ---

@app.route('/system/stats')
def system_stats():
    """Get system statistics"""
    try:
        import psutil
        import platform
        
        stats = {
            "system_info": {
                "platform": platform.system(),
                "python_version": platform.python_version(),
                "timestamp": datetime.now().isoformat()
            },
            "resources": {
                "cpu_percent": psutil.cpu_percent(interval=1),
                "memory_percent": psutil.virtual_memory().percent,
                "disk_percent": psutil.disk_usage('/').percent
            },
            "services": {
                "nlp_engine": nlp_engine is not None,
                "rag_system": rag_system is not None,
                "rag_documents": rag_system.get_stats()["total_documents"] if rag_system else 0
            }
        }
        
        return jsonify(stats)
        
    except ImportError:
        # psutil not available, return basic info
        return jsonify({
            "system_info": {
                "timestamp": datetime.now().isoformat()
            },
            "services": {
                "nlp_engine": nlp_engine is not None,
                "rag_system": rag_system is not None
            }
        })
    except Exception as e:
        logger.error(f"Error getting system stats: {e}")
        return jsonify({"error": "Failed to get system stats"}), 500

@app.route('/system/rag/clear', methods=['POST'])
def clear_rag_system():
    """Clear all documents from RAG system"""
    if rag_system is None:
        return jsonify({"error": "RAG System is not available"}), 503
    
    try:
        result = rag_system.clear_all()
        if result:
            return jsonify({"message": "RAG system cleared successfully"})
        else:
            return jsonify({"error": "Failed to clear RAG system"}), 500
    except Exception as e:
        logger.error(f"Error clearing RAG system: {e}")
        return jsonify({"error": "An internal error occurred"}), 500

@app.route('/system/rag/stats')
def rag_stats():
    """Get RAG system statistics"""
    if rag_system is None:
        return jsonify({"error": "RAG System is not available"}), 503
    
    try:
        stats = rag_system.get_stats()
        return jsonify(stats)
    except Exception as e:
        logger.error(f"Error getting RAG stats: {e}")
        return jsonify({"error": "An internal error occurred"}), 500

# --- Error Handlers ---

@app.errorhandler(404)
def not_found(error):
    return jsonify({"error": "Endpoint not found"}), 404

@app.errorhandler(405)
def method_not_allowed(error):
    return jsonify({"error": "Method not allowed"}), 405

@app.errorhandler(500)
def internal_error(error):
    logger.error(f"Internal server error: {error}")
    return jsonify({"error": "Internal server error"}), 500

@app.errorhandler(413)
def request_entity_too_large(error):
    return jsonify({"error": "File too large"}), 413

# --- Startup Information ---

@app.before_first_request
def startup_info():
    """Log startup information"""
    logger.info("=== Autonomous AI Assistant Started ===")
    logger.info(f"NLP Engine: {'✓' if nlp_engine else '✗'}")
    logger.info(f"RAG System: {'✓' if rag_system else '✗'}")
    logger.info("Available endpoints:")
    for rule in app.url_map.iter_rules():
        if rule.endpoint != 'static':
            logger.info(f"  {rule.methods} {rule.rule}")
    logger.info("========================================")

if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    debug = os.getenv('DEBUG', 'false').lower() == 'true'
    
    logger.info(f"Starting server on port {port} (debug={debug})")
    app.run(host='0.0.0.0', port=port, debug=debug)