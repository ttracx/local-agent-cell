"""ThoxChat-shaped shell. Muse is the primary agent. The cell is the runtime."""

from __future__ import annotations

import uuid
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from cell.chat import turn
from cell.harness import new_workspace

STATIC = Path(__file__).resolve().parent / "static"

app = FastAPI(title="ThoxChat Muse")
threads: dict[str, dict] = {}


class NewMessage(BaseModel):
    content: str = Field(min_length=1, max_length=4000)
    card: bool = False


def _public(thread: dict) -> dict:
    return {
        "id": thread["id"],
        "title": thread["title"],
        "agent": "muse",
        "messages": thread["messages"],
        "files": thread["files"],
    }


@app.get("/api/health")
def health():
    return {"ok": True, "agent": "muse"}


@app.get("/api/threads")
def list_threads():
    return {"threads": [_public(t) for t in threads.values()]}


@app.post("/api/threads")
def create_thread():
    thread_id = uuid.uuid4().hex[:12]
    thread = {
        "id": thread_id,
        "title": "New chat",
        "workspace": new_workspace(),
        "files": "",
        "messages": [],
    }
    threads[thread_id] = thread
    return _public(thread)


@app.get("/api/threads/{thread_id}")
def get_thread(thread_id: str):
    thread = threads.get(thread_id)
    if not thread:
        raise HTTPException(404, "thread not found")
    return _public(thread)


@app.post("/api/threads/{thread_id}/messages")
def post_message(thread_id: str, body: NewMessage):
    thread = threads.get(thread_id)
    if not thread:
        raise HTTPException(404, "thread not found")
    text = body.content.strip()
    thread["messages"].append({"role": "user", "content": text})
    if thread["title"] == "New chat":
        thread["title"] = text[:42]
    result = turn(text, thread["workspace"], body.card)
    thread["workspace"] = result["workspace"]
    thread["files"] = result["files"]
    message = {
        "role": "assistant",
        "agent": "muse",
        "content": result["content"],
        "decision": result["decision"],
        "trace": result["trace"],
        "steps": result["steps"],
        "fingerprint": result["fingerprint"],
    }
    thread["messages"].append(message)
    return {"thread": _public(thread), "message": message}


@app.get("/")
def index():
    return FileResponse(STATIC / "index.html")


app.mount("/static", StaticFiles(directory=STATIC), name="static")
