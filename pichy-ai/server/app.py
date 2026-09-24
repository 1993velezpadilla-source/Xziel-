from __future__ import annotations

import base64
import json
import os
import re
import threading
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import requests
from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from agent.pichy_agent import PichyAgent, load_config
from server.memory import SessionMemory
from server.attachments import AttachmentStore


APP_VERSION = "0.3.1-lab"
CONFIG_ENV = "PICHY_CONFIG"
SERVER_TOKEN_ENV = "PICHY_SERVER_TOKEN"
DATA_DIR_ENV = "PICHY_DATA_DIR"


class ChatRequest(BaseModel):
    session_id: str | None = None
    message: str = Field(min_length=1, max_length=100_000)
    route: str | None = None
    attachment_ids: list[str] = Field(default_factory=list, max_length=8)


class AttachmentRequest(BaseModel):
    session_id: str | None = None
    filename: str = Field(min_length=1, max_length=240)
    mime_type: str = Field(default="application/octet-stream", max_length=120)
    b64_data: str = Field(min_length=1)


class AttachmentResponse(BaseModel):
    session_id: str
    attachment_id: str
    filename: str
    mime_type: str
    size: int


class ChatResponse(BaseModel):
    session_id: str
    route: str
    answer: str


class ImageRequest(BaseModel):
    session_id: str | None = None
    prompt: str = Field(min_length=1, max_length=20_000)
    new_concept: bool = False
    size: str = "1024x1024"


class ImageResponse(BaseModel):
    session_id: str
    effective_prompt: str
    b64_json: str | None = None
    url: str | None = None


@dataclass
class SessionState:
    agent: PichyAgent
    lock: threading.Lock = field(default_factory=threading.Lock)
    last_image_prompt: str = ""


app = FastAPI(title="Pichy AI", version=APP_VERSION)
_sessions: dict[str, SessionState] = {}
_sessions_lock = threading.Lock()
_config_cache: dict[str, Any] | None = None


def _data_dir() -> Path:
    return Path(os.getenv(DATA_DIR_ENV, "data")).resolve()


_memory = SessionMemory(_data_dir() / "pichy_sessions.sqlite3")
_attachments = AttachmentStore(_data_dir() / "uploads")


def _config_path() -> Path:
    raw = os.getenv(CONFIG_ENV, "config/pichy.local.json")
    p = Path(raw)
    if not p.is_absolute():
        p = (Path.cwd() / p).resolve()
    return p


def get_config() -> dict[str, Any]:
    global _config_cache
    if _config_cache is None:
        path = _config_path()
        if not path.exists():
            raise HTTPException(
                status_code=503,
                detail=f"Pichy is not configured. Copy config/pichy.example.json to {path} and configure providers.",
            )
        _config_cache = load_config(str(path))
    return _config_cache


def require_token(x_pichy_token: str | None = Header(default=None)) -> None:
    expected = os.getenv(SERVER_TOKEN_ENV, "")
    if expected and x_pichy_token != expected:
        raise HTTPException(status_code=401, detail="Invalid Pichy server token")


def new_session_id() -> str:
    return uuid.uuid4().hex


def get_session(session_id: str | None) -> tuple[str, SessionState]:
    sid = (session_id or "").strip() or new_session_id()
    if not re.fullmatch(r"[A-Za-z0-9_-]{1,128}", sid):
        raise HTTPException(status_code=400, detail="invalid session_id")
    with _sessions_lock:
        state = _sessions.get(sid)
        if state is None:
            agent = PichyAgent(get_config())
            saved = _memory.load(sid)
            last_image_prompt = ""
            if saved:
                restored = [m for m in saved.get("history", []) if isinstance(m, dict) and m.get("role") != "system"]
                agent.history.extend(restored)
                last_image_prompt = saved.get("last_image_prompt", "")
            state = SessionState(agent, last_image_prompt=last_image_prompt)
            _sessions[sid] = state
    return sid, state


def persist_session(session_id: str, state: SessionState) -> None:
    history = [m for m in state.agent.history if m.get("role") != "system"]
    _memory.save(session_id, history, state.last_image_prompt)


def compose_image_prompt(previous: str, request: str, new_concept: bool) -> str:
    request = request.strip()
    if new_concept or not previous.strip():
        return request
    return (
        previous.strip()
        + "\n\nRevision request: "
        + request
        + "\nPreserve the identity, composition, and all prior accepted details unless this revision explicitly changes them."
    )


def image_provider_request(config: dict[str, Any], prompt: str, size: str) -> tuple[str | None, str | None]:
    cfg = config.get("image") or {}
    if not cfg:
        raise HTTPException(status_code=503, detail="Image provider is not configured")
    key_env = cfg.get("api_key_env", "")
    key = os.getenv(key_env, "")
    if not key:
        raise HTTPException(status_code=503, detail=f"Missing image API key env: {key_env}")
    payload = {
        "model": cfg["model"],
        "prompt": prompt,
        "n": 1,
        "size": size,
        "response_format": "b64_json",
    }
    try:
        r = requests.post(
            cfg["base_url"].rstrip("/") + "/images/generations",
            json=payload,
            timeout=240,
            headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
        )
    except requests.RequestException as exc:
        raise HTTPException(status_code=502, detail=f"Image provider network error: {exc}") from exc
    if r.status_code >= 400:
        raise HTTPException(status_code=502, detail=f"Image provider HTTP {r.status_code}: {r.text[:1000]}")
    try:
        first = r.json()["data"][0]
    except Exception as exc:
        raise HTTPException(status_code=502, detail="Image provider returned an unexpected response") from exc
    b64 = first.get("b64_json")
    url = first.get("url")
    if not b64 and not url:
        raise HTTPException(status_code=502, detail="Image provider returned no image")
    return b64, url


@app.get("/health")
def health() -> dict[str, Any]:
    return {
        "ok": True,
        "name": "Pichy AI",
        "version": APP_VERSION,
        "configured": _config_path().exists(),
        "sessions": len(_sessions),
        "persistent_memory": True,
    }


@app.get("/v1/capabilities", dependencies=[Depends(require_token)])
def capabilities() -> dict[str, Any]:
    cfg = get_config()
    public_models = {}
    for name, item in cfg.get("models", {}).items():
        public_models[name] = {
            "model": item.get("model"),
            "base_url": item.get("base_url"),
        }
    return {
        "version": APP_VERSION,
        "routes": sorted(cfg.get("routes", {}).keys()),
        "models": public_models,
        "image_configured": bool(cfg.get("image")),
        "persistent_memory": True,
        "tools": [x["function"]["name"] for x in PichyAgent(cfg).tools.definitions()],
    }


@app.post("/v1/attachments", response_model=AttachmentResponse, dependencies=[Depends(require_token)])
def upload_attachment(req: AttachmentRequest) -> AttachmentResponse:
    sid, _state = get_session(req.session_id)
    try:
        item = _attachments.save_b64(sid, req.filename, req.mime_type, req.b64_data)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return AttachmentResponse(
        session_id=sid,
        attachment_id=item.attachment_id,
        filename=item.filename,
        mime_type=item.mime_type,
        size=item.size,
    )


@app.get("/v1/provider-status", dependencies=[Depends(require_token)])
def provider_status() -> dict[str, Any]:
    cfg = get_config()
    models: dict[str, Any] = {}
    for name, item in cfg.get("models", {}).items():
        key_env = item.get("api_key_env", "")
        models[name] = {
            "model": item.get("model"),
            "base_url": item.get("base_url"),
            "api_key_env": key_env,
            "key_present": bool(key_env and os.getenv(key_env, "")),
        }
    image_cfg = cfg.get("image") or {}
    image_key_env = image_cfg.get("api_key_env", "")
    return {
        "models": models,
        "image": {
            "model": image_cfg.get("model"),
            "base_url": image_cfg.get("base_url"),
            "api_key_env": image_key_env,
            "key_present": bool(image_key_env and os.getenv(image_key_env, "")),
        },
    }


@app.get("/v1/sessions", dependencies=[Depends(require_token)])
def list_sessions(limit: int = 20) -> dict[str, Any]:
    return {"sessions": _memory.list_recent(limit)}


@app.delete("/v1/sessions/{session_id}", dependencies=[Depends(require_token)])
def delete_session(session_id: str) -> dict[str, Any]:
    with _sessions_lock:
        _sessions.pop(session_id, None)
    return {"deleted": _memory.delete(session_id)}


@app.post("/v1/chat", response_model=ChatResponse, dependencies=[Depends(require_token)])
def chat(req: ChatRequest) -> ChatResponse:
    sid, state = get_session(req.session_id)
    route = req.route or state.agent.classify_route(req.message)
    if route not in {"general", "reasoning", "coding", "research", "vision", "map_modeling"}:
        raise HTTPException(status_code=400, detail="Unsupported route")
    try:
        stored = [_attachments.load(sid, aid) for aid in req.attachment_ids]
        task_content = _attachments.to_message_content(req.message, stored)
        with state.lock:
            answer = state.agent.run(task_content, forced_route=route)
            persist_session(sid, state)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Pichy agent error: {type(exc).__name__}: {exc}") from exc
    return ChatResponse(session_id=sid, route=route, answer=answer)


@app.post("/v1/chat/stream", dependencies=[Depends(require_token)])
def chat_stream(req: ChatRequest) -> StreamingResponse:
    sid, state = get_session(req.session_id)
    route = req.route or state.agent.classify_route(req.message)
    if route not in {"general", "reasoning", "coding", "research", "vision", "map_modeling"}:
        raise HTTPException(status_code=400, detail="Unsupported route")

    def event_stream():
        yield "event: status\ndata: " + json.dumps({"session_id": sid, "state": "working", "route": route}) + "\n\n"
        try:
            stored = [_attachments.load(sid, aid) for aid in req.attachment_ids]
            task_content = _attachments.to_message_content(req.message, stored)
            with state.lock:
                answer = state.agent.run(task_content, forced_route=route)
                persist_session(sid, state)
            payload = {"session_id": sid, "route": route, "answer": answer}
            yield "event: final\ndata: " + json.dumps(payload, ensure_ascii=False) + "\n\n"
        except Exception as exc:
            payload = {"session_id": sid, "error": f"{type(exc).__name__}: {exc}"}
            yield "event: error\ndata: " + json.dumps(payload, ensure_ascii=False) + "\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")


@app.post("/v1/image", response_model=ImageResponse, dependencies=[Depends(require_token)])
def image(req: ImageRequest) -> ImageResponse:
    sid, state = get_session(req.session_id)
    with state.lock:
        effective = compose_image_prompt(state.last_image_prompt, req.prompt, req.new_concept)
        b64, url = image_provider_request(get_config(), effective, req.size)
        state.last_image_prompt = effective
        persist_session(sid, state)
    return ImageResponse(
        session_id=sid,
        effective_prompt=effective,
        b64_json=b64,
        url=url,
    )
