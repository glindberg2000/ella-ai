# Ella AI

## Description
Ella AI is a multimodal chatbot designed to integrate deep memory functionalities using MemGPT, with advanced tooling for reminders, scheduling, and media integration (SMS, iMessage, voice-to-chat). Built on the ChainLit chat UI framework and FastAPI, it incorporates a multi-agent backend for enhanced inference and knowledge augmentation.

## Current Features
- Authentication via Auth0.
- Basic database operations for storing user information.
- Preliminary integration with MemGPT for deep memory capabilities.

## Planned Features
- Full integration with Gmail, Google Calendar, and Twilio for SMS.
- Enhanced voice interaction capabilities.
- Scalable multi-agent system for backend processing.

## Quick Start
(Note: Project is in early development; the following instructions will evolve.)
- Clone the repository: `git clone https://github.com/glindberg2000/ella-ai.git`
- Navigate to the project directory: `cd ella_ai`
- Install dependencies: `pip install -r requirements.txt`
- Run the chat UI application: `chainlit run main.py --port 9000`
- Run the backend MemGPT: `memgpt server --port 8080`
- Run the services layer: `uvicorn services.main:app --host 0.0.0.0 --port 8000`

## Contributing
Currently, Ella AI is developed by [Your Name]. If you're interested in contributing, please reach out via greglindberg@gmail.com.

## License
This project is licensed under the Apache 2.0.
