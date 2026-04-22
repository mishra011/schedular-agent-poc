# Appointment Scheduler API

A FastAPI application that uses LangChain, LangGraph, and Ollama to manage an appointment scheduler. It allows users to schedule, reschedule, and cancel appointments using natural language, and exposes a RESTful API.

## Features

- **Natural Language Understanding**: Chat with the API to manage your appointments.
- **FastAPI Backend**: Fast, asynchronous REST framework.
- **Dockerized**: Easily run the application using Docker and Docker Compose.
- **Ollama Integration**: Connects to your local Ollama instance for LLM capabilities.

## Prerequisites

1. **Docker and Docker Compose** installed on your machine.
2. **Ollama** installed and running on your local machine.

## Setup Instructions

### 1. Ensure Ollama is running and has the model

The default model is `llama3.1:latest`. Make sure you have pulled it:
```bash
ollama pull llama3.1:latest
```

Ensure Ollama is running (it usually listens on port 11434).

### 2. Configure Environment

The application connects to Ollama using settings in the `.env` file.
The default `.env` is configured to connect from the Docker container to your host machine's Ollama instance using `host.docker.internal`.

```env
OLLAMA_BASE_URL=http://host.docker.internal:11434
OLLAMA_MODEL=llama3.1:latest
```

*Note: For Linux users, `host.docker.internal` is mapped via `extra_hosts` in `docker-compose.yml`. On Mac and Windows, Docker Desktop handles this automatically.*

### 3. Run the Application

Start the API using Docker Compose:

```bash
docker-compose up --build
```

The API will be available at `http://localhost:8000`.

## API Usage Examples

### 1. Chat Endpoint (`POST /chat`)

Used to interact with the scheduler. You must provide a `session_id` to maintain conversation history.

```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"session_id": "user123", "message": "Hi, I want to schedule an appointment for John on 2026-05-01 at 10:00 for a dental checkup."}'
```

### 2. View Database (`GET /db`)

View the mock database of all appointments.

```bash
curl http://localhost:8000/db
```

### 3. Health Check (`GET /health`)

Check if the API is running.

```bash
curl http://localhost:8000/health
```

## Future Tasks

Here is a list of planned enhancements to make the application production-ready:

### 1. Database & Persistence
*   **Persistent Database:** Replace the in-memory `MOCK_DB` with a real database (like PostgreSQL, MySQL, or MongoDB) using an ORM (like SQLAlchemy) or ODM (like Beanie/Motor) for reliable data storage.
*   **Conversation State Persistence:** Implement a persistent memory backend (like Redis, PostgreSQL, or MongoDB) for LangGraph checkpoints so users don't lose their session history on server restarts.

### 2. Security & Authentication
*   **Authentication & Authorization:** Secure the `/chat` endpoint using JWT tokens or OAuth2. Ensure users can only schedule, view, or cancel their *own* appointments.
*   **Restrict Sensitive Endpoints:** Restrict access to the `/db` endpoint to admins only or remove it entirely in production.
*   **Rate Limiting:** Implement rate limiting on the FastAPI endpoints to prevent abuse.

### 3. Reliability & Architecture
*   **Concurrency & Race Conditions:** Implement database transactions or locking mechanisms to ensure two users cannot book the same time slot simultaneously.
*   **Dynamic Calendar Integration:** Integrate with a real calendar API (like Google Calendar or Microsoft Outlook) to sync availability in real-time instead of using hardcoded working hours.
*   **Robust Error Handling:** Improve error handling to return specific HTTP status codes (400, 401, 404, etc.) instead of generic 500 errors, and implement structured logging.

### 4. Testing & Deployment
*   **Automated Testing:** Implement a comprehensive test suite using `pytest` to test the API endpoints, tool functions, and LangGraph agent logic.
*   **CI/CD Pipeline:** Set up Continuous Integration and Deployment (e.g., GitHub Actions) to automatically test code, build Docker images, and deploy.
*   **Environment Configuration Management:** Use a robust configuration manager (like Pydantic Settings) to manage environment variables and secrets securely.

