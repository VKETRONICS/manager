# routes_root.py
from fastapi import APIRouter
from modules.digest import send_daily_digest

router = APIRouter()

@router.get("/", tags=["root"])
async def index():
    return {"status": "ok", "app": "manager", "message": "Service is live"}

@router.get("/healthz", tags=["root"])
async def healthz():
    return {"ok": True}

@router.get("/debug/digest", tags=["debug"])
async def debug_digest():
    # ручной запуск еженедельной сводки (считает «вчера» по TZ)
    await send_daily_digest()
    return {"status": "digest_sent"}
