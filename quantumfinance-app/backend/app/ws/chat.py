"""Chat WebSocket: streaming conversation with crews/agents."""
import json

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.agents.crew import run_crew_for_ticker, get_default_crew_id
from app.agents.builder import build_agent_by_name
from app.agents.llm import make_llm
from app.db.base import SessionLocal
from app.db.models import ChatSession, ChatMessage


router = APIRouter(prefix="/api/chat", tags=["chat"])


@router.websocket("")
async def chat_ws(ws: WebSocket):
    await ws.accept()
    db = SessionLocal()
    session = ChatSession(title="New chat", model_used="openrouter/openai/gpt-4o-mini")
    db.add(session); db.commit(); db.refresh(session)
    await ws.send_json({"type": "session", "session_id": session.id})

    try:
        while True:
            raw = await ws.receive_text()
            try:
                msg = json.loads(raw)
            except Exception:
                await ws.send_json({"type": "error", "error": "invalid json"})
                continue
            user_text = msg.get("content", "")
            target = msg.get("target", "crew")  # crew or agent_name
            ticker = msg.get("ticker")

            # Persist user message
            db.add(ChatMessage(session_id=session.id, role="user", content=user_text))
            db.commit()

            await ws.send_json({"type": "thinking", "target": target})

            if target == "crew" and ticker:
                # Full crew run
                crew_id = msg.get("crew_id") or get_default_crew_id()
                result = await run_crew_for_ticker(ticker.upper(), crew_id=crew_id)
                reply = json.dumps(result, ensure_ascii=False, indent=2)
                db.add(ChatMessage(session_id=session.id, role="assistant",
                                    content=reply, agent_name="crew"))
                db.commit()
                await ws.send_json({"type": "message", "role": "assistant",
                                     "agent": "crew", "content": reply})
            else:
                # Single agent question
                agent_name = target if target != "crew" else "investment_strategist"
                agent = build_agent_by_name(agent_name)
                if not agent:
                    await ws.send_json({"type": "error", "error": f"agent {agent_name} not found"})
                    continue
                # Use the LLM directly with a system+user prompt
                llm = make_llm()
                prompt = [
                    {"role": "system", "content": (
                        f"Você é {agent.role}. {agent.backstory}. Responda em português, "
                        f"de forma concisa e citando dados sempre que possível."
                    )},
                    {"role": "user", "content": user_text},
                ]
                try:
                    reply = llm.call(prompt)
                except Exception as e:
                    reply = f"[erro do LLM: {e}]"
                db.add(ChatMessage(session_id=session.id, role="assistant",
                                    content=reply, agent_name=agent_name))
                db.commit()
                await ws.send_json({"type": "message", "role": "assistant",
                                     "agent": agent_name, "content": reply})
    except WebSocketDisconnect:
        pass
    finally:
        db.close()
