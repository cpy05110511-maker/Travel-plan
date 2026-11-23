"""Application service that executes and resumes the LangGraph workflow.

This module intentionally contains no FastAPI or Chainlit UI code. Both the
HTTP API and any future backend entry point can reuse this service.
"""

import logging
from typing import Any

from langchain_core.runnables import RunnableConfig
from langgraph.types import Command

logger = logging.getLogger(__name__)


async def run_travel_agent(
    graph: Any,
    message: str,
    thread_id: str,
) -> dict[str, Any]:
    """Start a new graph turn or resume the thread if it is interrupted.

    The resume logic follows the behavior in the original Chainlit app:
    if multiple tasks are interrupted, the latest interrupt task ID is
    associated with the user's response.
    """
    config_dict = {"configurable": {"thread_id": thread_id}}
    config = RunnableConfig(**config_dict)

    # Read the existing state for this thread. The same thread_id must be
    # reused for every turn in a conversation.
    snapshot = await graph.aget_state(config)

    if snapshot.next:
        tasks = snapshot.tasks
        interrupted_tasks = [task for task in tasks if task.interrupts]

        if len(interrupted_tasks) > 1:
            latest_task = interrupted_tasks[-1]
            resume_value: Any = {latest_task.id: message}
        else:
            # Preserve the original app.py behavior for a single interrupt
            # or a pending task whose interrupt metadata is unavailable.
            resume_value = message

        logger.info("Resuming LangGraph thread %s", thread_id)
        result = await graph.ainvoke(
            Command(resume=resume_value),
            config=config,
        )
    else:
        # Keep previous messages so the Validator can understand follow-up
        # questions after a completed graph run.
        existing_messages = (
            snapshot.values.get("messages", [])
            if snapshot.values
            else []
        )

        logger.info("Starting LangGraph turn for thread %s", thread_id)
        result = await graph.ainvoke(
            {
                "user_query": message,
                "messages": existing_messages,
                "reply_to_user": "",
                "current_state": "",
                "user_feedback": "",
            },
            config=config,
        )

    interrupt_messages = [
        str(item.value)
        for item in result.get("__interrupt__", [])
        if hasattr(item, "value")
    ]

    # LangGraph returns state values plus __interrupt__ when execution pauses.
    if interrupt_messages:
        status = "waiting_for_user"
        reply = "\n\n".join(interrupt_messages)
    else:
        status = "completed"
        reply = result.get("reply_to_user", "") or ""

    current_state = result.get("current_state")

    return {
        "thread_id": thread_id,
        "status": status,
        "reply": reply,
        "interrupts": interrupt_messages,
        "current_state": current_state,
    }
