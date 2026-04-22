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
