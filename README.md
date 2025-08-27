# Autonomous-AI-Assistant
Autonomous AI Assistant for Routine Task Automation leverages advanced NLP, RAG, and reinforcement learning to automate desktop tasks like file management, email handling, scheduling, and data analysis. Designed for secure, adaptive, and personalized workflows in educational and corporate settings.

***

## 🚀 Core Objectives

- **NLP-Powered Command Interpretation:** Accurately interpret complex, multi-step voice and text commands for efficient task execution.
- **Context-Aware Execution with RAG:** Retrieve and utilize user-specific data securely for personalized responses.
- **Adaptive Learning with Reinforcement Learning:** Continuously optimize performance using feedback-driven RL adaptation.
- **Secure and Orchestrated Workflows:** Integrate desktop/cloud services via n8n, OAuth2, and end-to-end encryption.

***

## ✨ Key Functionalities

- **📂 File Management:** Automate file and folder operations—organizing, moving, copying, and deleting.
- **📧 Email Handling:** Smart reading, summarizing, drafting, sending, and filtering of emails.
- **🗓️ Scheduling:** Integrate Google Calendar for events, meetings, and reminders.
- **📊 Data Analysis:** Generate insights and automated reports from user data.
- **✍️ Document Generation:** Prepare circulars, notices, and analytical reports with actionable recommendations.
- **🎓 IMS Integration:** Automate academic data entry in the Integrated Management System (IMS) portal.

***

## 🏛️ Technical Architecture

System Flow:  
`Input (Voice/Text) → Security Layer → NLP Engine → RAG System → n8n Orchestration → Task Execution → Notification → Feedback Loop → RL Adaptation`

**Core Components**:
- User Input Layer (Whisper/Google Speech-to-Text)
- Security Layer (OAuth2, AES-256 encryption, auditing)
- NLP Engine (Intent recognition & slot-filling)
- RAG System (FAISS vector DB, contextual data retrieval)
- Orchestration Layer (Multi-agent workflows with n8n)
- Execution Layer (APIs, Selenium, PyAutoGUI)
- Learning Layer (Reinforcement Learning)
- Interface Layer (Web dashboard)

***

## 🛠️ Technology Stack

| Category         | Technology                                  |
|------------------|---------------------------------------------|
| OS               | Ubuntu 22.04 LTS                            |
| Language         | Python 3.10+                                |
| AI Frameworks    | PyTorch 1.13 / TensorFlow 2.12              |
| Orchestration    | n8n (Pro Version)                           |
| NLP              | transformers, spaCy, Hugging Face Models    |
| Automation       | Selenium 4.0, pyautogui                     |
| Vector DB        | FAISS                                       |
| Database         | PostgreSQL 14 / SQLite                      |
| APIs             | OpenAI API, Google Speech-to-Text, Whisper  |
| Security         | OAuth2, cryptography                        |
| Containerization | Docker 20.10                                |

***

## 📦 Project Structure

```text
/autonomous-ai-assistant
├── .github/                # GitHub Actions for CI/CD
├── app/
│   ├── main.py
│   ├── nlp_engine.py
│   ├── rag_system.py
│   ├── rl_agent.py
│   ├── security.py
│   ├── automation_scripts/
│   │   ├── file_management.py
│   │   └── email_handler.py
│   └── api_integrations/
│       ├── google_calendar.py
│       └── gmail_api.py
├── config/
│   └── config.yaml
├── data/
│   ├── faiss_index/
│   └── logs/
├── n8n_workflows/
│   └── main_workflow.json
├── static/
├── templates/
│   └── index.html
├── tests/
│   ├── test_nlp_engine.py
│   └── test_rag_system.py
├── .dockerignore
├── .env.example
├── .gitignore
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
└── README.md
```

***

## ⚙️ Installation and Setup

**Prerequisites**:
- Docker and Docker Compose
- Python 3.10+
- Git

**Steps**:
1. Clone the repository:
    ```bash
    git clone https://github.com/your-username/autonomous-ai-assistant.git
    cd autonomous-ai-assistant
    ```
2. Set up environment variables:
    ```bash
    cp .env.example .env
    # Edit .env and add API keys and credentials
    ```
3. Build and run using Docker:
    ```bash
    docker-compose up --build
    ```
   The application will be available at `http://localhost:5000`, and n8n at `http://localhost:5678`.

***

## 📖 Usage

- Open the web interface in your browser.
- Use the text box or microphone for commands.
    - Example (Text): `"Summarize my unread emails from the last 24 hours."`
    - Example (Voice): `"Create a new folder on my desktop named 'Project Documents'."`
- Provide feedback with thumbs up/down icons to improve assistant learning.

***

## 🧪 Testing

Run the test suite:
```bash
docker-compose exec app pytest
```

***

## 🤝 Contributing

Contributions, issues, and feature requests are welcome. Please open an issue to discuss or propose changes.

***

## 📄 License

This project is licensed under the MIT License. See the LICENSE file for details.

***

## 🎓 Project Team

- **Jayashree AR (4CB22AI023)**
- **Pratham R (4CB22AI040)**
- **Shreya M (4CB22AI053)**
- **Siddharth K (4CB22AI057)**
- **Project Guide: Prof. Basappa B Kodada, Department of AIML, Canara Engineering College**

---

[1](https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/attachments/57714664/836cd881-1a7d-4f92-a57e-16143a956434/Our_Project_Synopsis.pdf)
[2](https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/attachments/57714664/a4169510-561e-4a14-a616-0c0536d3a07e/Our_Project.pdf)
