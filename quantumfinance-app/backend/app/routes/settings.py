"""Settings KV store."""
from fastapi import APIRouter
from pydantic import BaseModel

from app.db.base import SessionLocal
from app.db.models import Setting


router = APIRouter(prefix="/api/settings", tags=["settings"])


class SettingUpdate(BaseModel):
    value: dict


@router.get("")
def list_settings():
    db = SessionLocal()
    try:
        return {s.key: s.value for s in db.query(Setting).all()}
    finally:
        db.close()


@router.put("/{key}")
def update_setting(key: str, body: SettingUpdate):
    db = SessionLocal()
    try:
        s = db.get(Setting, key)
        if not s:
            s = Setting(key=key, value=body.value)
            db.add(s)
        else:
            s.value = body.value
        db.commit()
        return {"key": key, "value": body.value}
    finally:
        db.close()
