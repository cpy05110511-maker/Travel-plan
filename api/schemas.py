"""Pydantic schemas for the HTTP API boundary."""

from typing import Literal

from pydantic import BaseModel, Field, field_validator


class ChatRequest(BaseModel):
    """A message submitted by Chainlit or another HTTP client."""

    message: str = Field(
        ...,
        min_length=1,
        max_length=10_000,
        description="The user's current message.",
    )
    thread_id: str | None = Field(
        default=None,
        min_length=1,
        max_length=200,
        description="LangGraph thread ID. Omit it to start a new thread.",
    )

    @field_validator("message")
    @classmethod
    def message_must_not_be_blank(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("message cannot be blank")
        return value

    @field_validator("thread_id")
    @classmethod
    def thread_id_must_not_be_blank(cls, value: str | None) -> str | None:
        if value is not None:
            value = value.strip()
            if not value:
                raise ValueError("thread_id cannot be blank")
        return value


class ChatResponse(BaseModel):
    """Normalized response returned to the Chainlit frontend."""

    thread_id: str
    status: Literal["waiting_for_user", "completed"]
    reply: str = ""
    interrupts: list[str] = Field(default_factory=list)
    current_state: str | None = None


class HealthResponse(BaseModel):
    status: str
    service: str
