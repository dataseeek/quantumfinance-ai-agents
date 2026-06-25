"""Chat WebSocket: streaming conversation with crews/agents.

Two key behaviors:
- ChatSession is created lazily on the first user message (avoids empty
  sessions every time the page mounts/refreshes).
- Single-agent replies are streamed token-by-token via litellm's async
  streaming API. Crew replies are post-processed into a readable text
  (recommendation + reasoning) instead of a raw JSON dump.
"""
import json

import litellm
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.agents.crew import run_crew_for_ticker, get_default_crew_id
from app.agents.builder import build_agent_by_name
from app.config import settings
from app.db.base import SessionLocal
from app.db.models import ChatSession, ChatMessage
from app.tools.news import COMPANY_KEYWORDS


router = APIRouter(prefix="/api/chat", tags=["chat"])


def _detect_ticker(text: str) -> str | None:
    """Find the first ticker mentioned in the user's text.

    Priority:
    1. Literal ticker code (VALE3 / PETR4 / BBAS3 / ITUB4).
    2. Longest company keyword match (avoids 'banco do brasil' losing to 'bb').
    """
    if not text:
        return None
    t = text.lower()
    for ticker in COMPANY_KEYWORDS.keys():
        if ticker.lower() in t:
            return ticker
    candidates: list[tuple[int, str]] = []
    for ticker, kws in COMPANY_KEYWORDS.items():
        for kw in kws:
            if kw in t:
                candidates.append((len(kw), ticker))
    if candidates:
        candidates.sort(reverse=True)
        return candidates[0][1]
    return None


def _create_session(model: str) -> int:
    db = SessionLocal()
    try:
        s = ChatSession(title="New chat", model_used=model)
        db.add(s); db.commit(); db.refresh(s)
        return s.id
    finally:
        db.close()


def _persist_message(session_id: int, role: str, content: str, agent_name: str | None = None):
    db = SessionLocal()
    try:
        db.add(ChatMessage(session_id=session_id, role=role,
                            content=content, agent_name=agent_name))
        db.commit()
    finally:
        db.close()


async def _stream_single_agent(ws: WebSocket, agent_name: str, user_text: str) -> str | None:
    """Stream a single-agent reply token-by-token. Returns the full text or None on error."""
    agent = build_agent_by_name(agent_name)
    if agent is None:
        await ws.send_json({"type": "error", "error": f"agent {agent_name} not found"})
        return None

    system = (
        f"Você é {agent.role}. {agent.backstory}. "
        f"Responda em português, de forma concisa e citando dados quando possível."
    )
    messages = [
        {"role": "system", "content": system},
        {"role": "user", "content": user_text},
    ]

    parts: list[str] = []
    try:
        resp = await litellm.acompletion(
            model=settings.llm_model,
            messages=messages,
            api_key=settings.openrouter_api_key,
            api_base="https://openrouter.ai/api/v1",
            stream=True,
            temperature=0.3,
        )
        async for chunk in resp:
            delta = None
            try:
                delta = chunk.choices[0].delta.content
            except Exception:
                delta = None
            if delta:
                parts.append(delta)
                await ws.send_json({"type": "chunk", "delta": delta, "agent": agent_name})
    except Exception as e:
        await ws.send_json({"type": "error", "error": f"LLM error: {e}"})
        return None
    return "".join(parts)


def _format_crew_reply(ticker: str, result: dict) -> str:
    """Render the crew result as readable text rather than a JSON dump."""
    if "error" in result:
        return f"⚠️  Crew error: {result['error']}"
    rec = (result.get("recommendation") or "?").upper()
    reasoning = result.get("reasoning") or ""
    head = f"**{ticker.upper()} → {rec}**"
    return f"{head}\n\n{reasoning}" if reasoning else head


@router.websocket("")
async def chat_ws(ws: WebSocket):
    await ws.accept()
    session_id: int | None = None

    try:
        while True:
            raw = await ws.receive_text()
            try:
                msg = json.loads(raw)
            except Exception:
                await ws.send_json({"type": "error", "error": "invalid json"})
                continue

            user_text = (msg.get("content") or "").strip()
            if not user_text:
                await ws.send_json({"type": "error", "error": "empty message"})
                continue

            target = msg.get("target", "crew")
            ticker = msg.get("ticker")

            # Lazy session creation: only on the FIRST real user message.
            if session_id is None:
                session_id = _create_session(settings.llm_model)
                await ws.send_json({"type": "session", "session_id": session_id})

            _persist_message(session_id, "user", user_text)
            await ws.send_json({"type": "thinking", "target": target})

            if target == "crew":
                # Auto-detect ticker from text. The detected ticker overrides
                # the dropdown only when it actually differs (so the user can
                # still pick a ticker manually and discuss it freely).
                detected = _detect_ticker(user_text)
                effective_ticker = detected or ticker
                if detected and ticker and detected.upper() != (ticker or "").upper():
                    await ws.send_json({
                        "type": "auto_ticker",
                        "from": ticker, "to": detected,
                    })
                if not effective_ticker:
                    await ws.send_json({
                        "type": "error",
                        "error": "Selecione um ticker no dropdown ou mencione a ação (VALE3, Petrobras, Itaú…) na sua mensagem.",
                    })
                    continue
                crew_id = msg.get("crew_id") or get_default_crew_id()
                try:
                    result = await run_crew_for_ticker(effective_ticker.upper(), crew_id=crew_id)
                except Exception as e:
                    await ws.send_json({"type": "error", "error": f"Crew error: {e}"})
                    continue
                reply = _format_crew_reply(effective_ticker, result)
                _persist_message(session_id, "assistant", reply, agent_name="crew")
                await ws.send_json({
                    "type": "message", "role": "assistant",
                    "agent": "crew", "content": reply,
                })
            else:
                agent_name = target if target != "crew" else "investment_strategist"
                full = await _stream_single_agent(ws, agent_name, user_text)
                if full is not None:
                    _persist_message(session_id, "assistant", full, agent_name=agent_name)
                    await ws.send_json({"type": "done", "agent": agent_name})
    except WebSocketDisconnect:
        pass
