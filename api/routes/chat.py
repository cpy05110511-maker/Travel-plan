"""Chat endpoints used by the Chainlit frontend and external clients."""

import logging
from uuid import uuid4

from fastapi import APIRouter, HTTPException, Request

from api.schemas import ChatRequest, ChatResponse
from api.services.travel_service import run_travel_agent

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest, http_request: Request) -> ChatResponse:
    """Execute one conversational turn of the travel-planning workflow."""
    thread_id = request.thread_id or str(uuid4())

    graph = getattr(http_request.app.state, "travel_graph", None)
    if graph is None:
        raise HTTPException(
            status_code=503,
            detail="Travel Agent is not initialized",
        )

    try:
        result = await run_travel_agent(
            graph=graph,
            message=request.message,
            thread_id=thread_id,
        )
        return ChatResponse(**result)
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Travel Agent execution failed for thread %s", thread_id)
        # Keep internal exception details in server logs; do not leak secrets
        # or stack traces through the public API response.
        raise HTTPException(
            status_code=500,
            detail="Travel Agent execution failed. Check backend logs.",
        ) from exc
