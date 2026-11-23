"""Focused tests for the FastAPI transport schema and LangGraph service."""

from types import SimpleNamespace

import pytest
from pydantic import ValidationError

from api.schemas import ChatRequest
from api.services.travel_service import run_travel_agent


def test_chat_request_strips_message():
    request = ChatRequest(message="  plan a trip  ", thread_id=" thread-1 ")
    assert request.message == "plan a trip"
    assert request.thread_id == "thread-1"


def test_chat_request_rejects_blank_message():
    with pytest.raises(ValidationError):
        ChatRequest(message="   ")


class FakeGraph:
    def __init__(self, snapshot, result):
        self.snapshot = snapshot
        self.result = result
        self.ainvoke_calls = []

    async def aget_state(self, config):
        return self.snapshot

    async def ainvoke(self, value, config):
        self.ainvoke_calls.append((value, config))
        return self.result


@pytest.mark.asyncio
async def test_service_starts_new_thread():
    snapshot = SimpleNamespace(next=(), tasks=(), values={"messages": []})
    graph = FakeGraph(
        snapshot,
        {"reply_to_user": "Please tell me your departure city.", "current_state": "entity_identifier"},
    )

    result = await run_travel_agent(graph, "Plan a Japan trip", "thread-1")

    assert result["status"] == "completed"
    assert result["reply"] == "Please tell me your departure city."
    call_value, call_config = graph.ainvoke_calls[0]
    assert call_value["user_query"] == "Plan a Japan trip"
    assert call_config["configurable"]["thread_id"] == "thread-1"


@pytest.mark.asyncio
async def test_service_resumes_interrupted_thread():
    interrupt_task = SimpleNamespace(id="task-1", interrupts=[object()])
    snapshot = SimpleNamespace(next=("entity_identifier",), tasks=[interrupt_task], values={})
    interrupt_value = SimpleNamespace(value="Which city are you departing from?")
    graph = FakeGraph(
        snapshot,
        {"__interrupt__": [interrupt_value], "current_state": "entity_identifier"},
    )

    result = await run_travel_agent(graph, "Shanghai", "thread-2")

    assert result["status"] == "waiting_for_user"
    assert result["reply"] == "Which city are you departing from?"
    call_value, _ = graph.ainvoke_calls[0]
    assert call_value.resume == "Shanghai"
