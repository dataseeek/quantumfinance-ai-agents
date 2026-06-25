"""Chat session history endpoints (separate from the WebSocket)."""
from fastapi import APIRouter, HTTPException

from app.db.base import SessionLocal
from app.db.models import ChatSession, ChatMessage


router = APIRouter(prefix="/api/chat-sessions", tags=["chat"])


@router.get("")
def list_sessions(limit: int = 50):
    db = SessionLocal()
    try:
        sessions = (db.query(ChatSession)
                      .order_by(ChatSession.started_at.desc()).limit(limit).all())
        result = []
        for s in sessions:
            count = db.query(ChatMessage).filter_by(session_id=s.id).count()
            first_user = (db.query(ChatMessage)
                            .filter_by(session_id=s.id, role="user")
                            .order_by(ChatMessage.created_at.asc()).first())
            preview = first_user.content[:80] if first_user else "(empty)"
            result.append({
                "id": s.id,
                "started_at": s.started_at.isoformat(),
                "title": s.title,
                "preview": preview,
                "message_count": count,
            })
        return result
    finally:
        db.close()


@router.get("/{session_id}/messages")
def list_messages(session_id: int):
    db = SessionLocal()
    try:
        msgs = (db.query(ChatMessage).filter_by(session_id=session_id)
                  .order_by(ChatMessage.created_at.asc()).all())
        return [
            {"id": m.id, "role": m.role, "agent_name": m.agent_name,
             "content": m.content, "created_at": m.created_at.isoformat()}
            for m in msgs
        ]
    finally:
        db.close()


@router.delete("/{session_id}")
def delete_session(session_id: int):
    db = SessionLocal()
    try:
        session = db.get(ChatSession, session_id)
        if not session:
            raise HTTPException(404, f"Session {session_id} not found")
        deleted_msgs = (db.query(ChatMessage)
                          .filter_by(session_id=session_id)
                          .delete(synchronize_session=False))
        db.delete(session)
        db.commit()
        return {"ok": True, "deleted_session": session_id, "deleted_messages": deleted_msgs}
    finally:
        db.close()
