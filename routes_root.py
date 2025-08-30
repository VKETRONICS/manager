# routes_root.py
from fastapi import APIRouter, Response
from datetime import datetime
from modules.digest import send_daily_digest
from scheduler import scheduler

router = APIRouter()

# --- ROOT ---
@router.get("/", tags=["root"])
async def index():
    return {"status": "ok", "app": "manager", "message": "Service is live"}

@router.head("/", tags=["root"])
async def index_head():
    # Пустой ответ 200 для HEAD-проверок
    return Response(status_code=200)

# --- HEALTH ---
@router.get("/healthz", tags=["root"])
async def healthz():
    return {"ok": True}

@router.head("/healthz", tags=["root"])
async def healthz_head():
    return Response(status_code=200)

# --- DEBUG: ручной запуск отчёта ---
@router.get("/debug/digest", tags=["debug"])
async def debug_digest():
    # Считает "вчера" по TZ и шлёт отчёт админу в TG
    await send_daily_digest()
    return {"status": "digest_sent"}

# --- DEBUG: список задач APScheduler (удобно для проверки) ---
@router.get("/debug/jobs", tags=["debug"])
def debug_jobs():
    jobs = []
    for j in scheduler.get_jobs():
        jobs.append({
            "id": j.id,
            "trigger": str(j.trigger),
            "next_run_time": j.next_run_time.isoformat() if j.next_run_time else None,
        })
    return {
        "now": datetime.utcnow().isoformat() + "Z",
        "jobs": jobs
    }
# --- DEBUG: ручной запуск анти-лайков (постоянно, но под ключом) ---
import os
from fastapi import Query, HTTPException
from modules.anti_likes import run_anti_likes_once

DEBUG_KEY = os.getenv("DEBUG_ENDPOINT_KEY", "")

@router.get("/debug/anti_likes", tags=["debug"])
async def debug_anti_likes(k: str = Query(default="", description="secret key from DEBUG_ENDPOINT_KEY")):
    # Проверяем секрет
    if not DEBUG_KEY or k != DEBUG_KEY:
        raise HTTPException(status_code=404, detail="Not found")
    result = await run_anti_likes_once()
    return {"ok": True, "result": result}
