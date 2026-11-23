"""FastAPI application entry point for the Travel Planner backend."""

from contextlib import asynccontextmanager
import logging

from fastapi import FastAPI
from langgraph.checkpoint.memory import MemorySaver
from langgraph.store.memory import InMemoryStore

from workflow import get_travel_agent
from api.routes.chat import router as chat_router
from api.routes.health import router as health_router

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Create one LangGraph instance for this API process."""
    checkpointer = MemorySaver()
    store = InMemoryStore()

    logger.info("Initializing Travel Planner LangGraph workflow")
    app.state.travel_graph = get_travel_agent(checkpointer, store)
    app.state.checkpointer = checkpointer
    app.state.store = store

    try:
        yield
    finally:
        # MemorySaver and InMemoryStore are in-process stores. There is no
        # external connection to close, but dropping references is explicit.
        app.state.travel_graph = None
        app.state.checkpointer = None
        app.state.store = None
        logger.info("Travel Planner API shutdown complete")


app = FastAPI(
    title="Travel Planner API",
    description="HTTP API for the RoamWise multi-agent travel planner.",
    version="1.0.0",
    lifespan=lifespan,
)

app.include_router(
    chat_router,
    prefix="/api/v1",
    tags=["Chat"],
)
app.include_router(
    health_router,
    tags=["Health"],
)


@app.get("/", tags=["Health"])
async def root():
    return {"message": "Travel Planner API is running"}
