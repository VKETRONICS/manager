# app.py
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

# подключаем роуты из routes_root.py
from routes_root import router as root_router

app = FastAPI(title="Manager", version="1.0.0")

# === Роуты: /, /healthz, /debug/digest ===
app.include_router(root_router)


# === Telegram webhook ===
# Если у тебя уже реализован свой обработчик — оставь его.
# Ниже минимальная заглушка, чтобы /tg/webhook не отдавал 404.
@app.post("/tg/webhook")
async def tg_webhook(request: Request):
    try:
        await request.json()  # читаем тело, чтобы не было ошибок
    except Exception:
        pass
    return JSONResponse({"ok": True})
