# Chainlit + FastAPI Integration

This version keeps Chainlit as the chat frontend and runs FastAPI as a separate backend process. Chainlit sends each user turn to FastAPI via HTTP; FastAPI owns the LangGraph instance and invokes the original workflow and agents.

## Architecture

```text
Browser
  |
  v
Chainlit (app.py, port 8000)
  |  HTTP POST /api/v1/chat
  |  JSON: {"message": "...", "thread_id": "..."}
  v
FastAPI (api/main.py, port 8001)
  |
  v
API Router (api/routes/chat.py)
  |
  v
Service (api/services/travel_service.py)
  |
  v
Existing LangGraph (workflow.py)
  |
  +--> existing agents/
  +--> existing tools/
  +--> existing models/
```

The original `workflow.py`, `agents/`, `models/`, `tools/`, and `utils.py` are retained. `app.py` no longer imports or invokes LangGraph; it only forwards messages to FastAPI and displays the response.

## New files

- `api/main.py`: creates the FastAPI app and initializes the LangGraph workflow during application startup.
- `api/schemas.py`: validates incoming chat requests and outgoing responses.
- `api/routes/chat.py`: exposes `POST /api/v1/chat`.
- `api/routes/health.py`: exposes `GET /health`.
- `api/services/travel_service.py`: starts or resumes the LangGraph thread and converts results into an API response.
- `tests/test_api.py`: tests the request schema and the service's start/resume behavior.

## Install dependencies

```bash
uv sync
```

The direct API dependencies are `fastapi`, `uvicorn`, and `httpx`; they are listed in `pyproject.toml` and `uv.lock`.

## Configure and run

Copy `.env.sample` to `.env` and fill in the existing model/search/email credentials. The Chainlit process also needs `TRAVEL_API_URL`:

```text
TRAVEL_API_URL=http://127.0.0.1:8001/api/v1/chat
```

Start the backend in terminal 1:

```bash
uv run uvicorn api.main:app --host 127.0.0.1 --port 8001 --reload
```

Start the frontend in terminal 2 (Linux/macOS):

```bash
export TRAVEL_API_URL=http://127.0.0.1:8001/api/v1/chat
uv run chainlit run app.py --host 127.0.0.1 --port 8000
```

Windows PowerShell:

```powershell
$env:TRAVEL_API_URL="http://127.0.0.1:8001/api/v1/chat"
uv run chainlit run app.py --host 127.0.0.1 --port 8000
```

Open:

- Chainlit UI: http://127.0.0.1:8000
- FastAPI Swagger UI: http://127.0.0.1:8001/docs
- Health check: http://127.0.0.1:8001/health

## API contract

Request:

```json
{
  "message": "Plan a five-day trip to Japan",
  "thread_id": "chainlit-session-id"
}
```

Response when the graph pauses for user input:

```json
{
  "thread_id": "chainlit-session-id",
  "status": "waiting_for_user",
  "reply": "Which city are you departing from?",
  "interrupts": ["Which city are you departing from?"],
  "current_state": "entity_identifier"
}
```

The frontend must send the same `thread_id` on subsequent turns. The backend uses it as LangGraph's `configurable.thread_id` to locate the thread checkpoint.

## Persistence and deployment limitations

1. This implementation retains the original `MemorySaver` and `InMemoryStore` approach. The checkpoint is stored in the FastAPI process memory. If FastAPI restarts, pending LangGraph conversations cannot be resumed even if Chainlit's SQLite chat history still exists.
2. Run one Uvicorn worker while using the in-memory checkpointer. Multiple workers have separate memory and do not share checkpoint state.
3. For multi-worker or production deployment, use a shared persistent LangGraph checkpointer (for example PostgreSQL), authenticate callers, and authorize each `thread_id` against the current user.
4. This version uses regular request/response JSON, not SSE streaming. The Chainlit UI receives the answer after the FastAPI request completes or interrupts.
5. An HTTP client timeout does not prove that backend execution stopped. Before retrying side-effecting operations such as email sending, add idempotency keys and task-status checks.
6. The original `agents/itinerary.py` contains a developer-specific absolute `FilesystemBackend` path. Configure that path for your machine before running the itinerary stage; it has intentionally not been changed as part of the FastAPI integration.
