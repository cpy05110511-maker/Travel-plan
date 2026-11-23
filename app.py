"""Chainlit frontend for RoamWise.

LangGraph execution lives in the FastAPI backend. This file only manages
Chainlit sessions, sends HTTP requests, and renders backend responses.
"""

import os
from typing import Any

import chainlit as cl
import httpx


DEFAULT_API_URL = "http://127.0.0.1:8001/api/v1/chat"


@cl.set_starters  # type: ignore
async def set_starts() -> list[cl.Starter]:
    return [
        cl.Starter(
            label="Plan a family trip to Manali",
            message="Plan a 5 day trip to Manali from Mumbai in the month of May",
        ),
        cl.Starter(
            label="Plan a weekend Gateway to Lonavala",
            message="Plan a weekend trip to Lonavala from Mumbai in the last week of Dec",
        ),
        cl.Starter(
            label="Where to go in the month May",
            message="Best places to visit in the month of may in india from Mumbai",
        ),
    ]


@cl.on_chat_start
async def on_chat_start():
    """Initialize the Chainlit-side session identifier."""
    thread_id = cl.context.session.id
    cl.user_session.set("thread_id", thread_id)


@cl.on_chat_resume
async def on_chat_resume(thread: dict[str, Any]):
    """Restore the same thread ID when a Chainlit history is resumed."""
    thread_id = thread.get("id")
    if thread_id:
        cl.user_session.set("thread_id", thread_id)

    await cl.Message(
        content="💬 Chat resumed. You can continue from where you left off!"
    ).send()


@cl.on_message
async def on_message(msg: cl.Message):
    """Forward the user's message to FastAPI and render its response."""
    api_url = os.getenv("TRAVEL_API_URL", DEFAULT_API_URL)
    thread_id = (
        cl.user_session.get("thread_id")
        or cl.context.session.id
    )
    cl.user_session.set("thread_id", thread_id)

    timeout = httpx.Timeout(300.0, connect=10.0)

    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(
                api_url,
                json={
                    "message": msg.content,
                    "thread_id": thread_id,
                },
            )
            response.raise_for_status()
            result = response.json()

        # The backend may return a generated thread_id for clients that do
        # not provide one. Chainlit normally supplies its own session ID.
        thread_id = result.get("thread_id", thread_id)
        cl.user_session.set("thread_id", thread_id)

        reply = result.get("reply", "")
        if not reply:
            reply = "任务已处理，但当前没有可展示的文本回复。"

        await cl.Message(content=reply).send()

    except httpx.TimeoutException:
        await cl.Message(
            content="请求 FastAPI 服务超时。请检查后端执行状态后再重试，避免重复执行外部操作。"
        ).send()
    except httpx.HTTPStatusError as exc:
        status_code = exc.response.status_code
        await cl.Message(
            content=f"旅行规划后端返回错误（HTTP {status_code}），请检查 FastAPI 日志。"
        ).send()
    except httpx.RequestError:
        await cl.Message(
            content="无法连接 FastAPI 后端，请确认后端服务已经启动。"
        ).send()
    except Exception:
        await cl.Message(
            content="前端处理请求时发生异常，请查看 Chainlit 服务日志。"
        ).send()


if __name__ == "__main__":
    from chainlit.cli import run_chainlit
    run_chainlit(__file__)
