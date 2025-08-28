# Autonomous AI Assistant

This project is an Autonomous AI Assistant that utilizes Natural Language Processing (NLP) to process user commands. It is built using Flask for the web server and leverages various AI frameworks for intent classification and entity extraction.

## Project Structure

```
autonomous-ai-assistant
├── app/
│   ├── __init__.py       # Marks the directory as a Python package
│   ├── main.py           # Creates the Flask web server and defines API endpoints
│   └── nlp_engine.py     # Contains the NLPEngine class for NLP tasks
├── .env.example           # Template for environment variables
├── .gitignore             # Specifies files to be ignored by Git
├── Dockerfile             # Instructions to build the Docker image
├── docker-compose.yml     # Defines Docker services for the application
└── requirements.txt       # Lists required Python libraries
```

## Setup Instructions

1. **Clone the Repository**
   ```bash
   git clone <repository-url>
   cd autonomous-ai-assistant
   ```

2. **Create the Environment File**
   Copy the example environment file:
   ```bash
   cp .env.example .env
   ```

3. **Build and Run the Application**
   Use Docker Compose to build the image and start the container:
   ```bash
   docker-compose up --build
   ```

4. **Test the API Endpoint**
   Once the container is running, you can test the API using `curl`:
   ```bash
   curl -X POST http://localhost:5000/process \
        -H "Content-Type: application/json" \
        -d '{"command": "Schedule a meeting with Shreya for next Friday at 10am"}'
   ```

   You should receive a JSON response with the processed command, intent, and extracted entities.

## Usage

The application provides an API endpoint at `/process` where you can send commands for processing. The NLPEngine will classify the intent and extract relevant entities from the command.

## Dependencies

The project requires the following Python libraries:
- torch
- transformers
- spacy
- flask

These are specified in the `requirements.txt` file and will be installed automatically when building the Docker image.

## License

This project is licensed under the MIT License.