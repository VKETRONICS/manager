# app.py
import os, hmac, hashlib
from fastapi import FastAPI, Request, HTTPException
from dotenv import load_dotenv
load_dotenv()

from config import load_config
from db import init_db
from scheduler import scheduler, init_jobs

from telebot import TeleBot, types
from bot.ui import main_menu, back_kb

# корневые роуты (/, /healthz, /debug/*)
from routes_root import router as root_router

cfg = load_config()
app = FastAPI(title="ETRONICS Community Bot")

# БД и роуты
init_db()
app.include_router(root_router)

# --- Telegram bot ---
bot = TeleBot(cfg.TELEGRAM_BOT_TOKEN, parse_mode="HTML")

@bot.message_handler(commands=["start"])
def start(m: types.Message):
    bot.send_message(m.chat.id, "Панель управления", reply_markup=main_menu())

@bot.callback_query_handler(func=lambda c: True)
def callbacks(c: types.CallbackQuery):
    data = c.data
    if data == "status":
        bot.edit_message_text(chat_id=c.message.chat.id, message_id=c.message.message_id,
                              text="Автопилот: ✅\nУдалено сегодня: 0\nКарантин: 0",
                              reply_markup=back_kb("back_main"))
    elif data == "members":
        bot.edit_message_text(chat_id=c.message.chat.id, message_id=c.message.message_id,
                              text="Подписчики: проверено 0 / удалено 0 / карантин 0",
                              reply_markup=back_kb("back_main"))
    elif data == "likes":
        bot.edit_message_text(chat_id=c.message.chat.id, message_id=c.message.message_id,
                              text="Анти-лайки: за сутки проверено 0 / удалено 0 / карантин 0",
                              reply_markup=back_kb("back_main"))
    elif data == "comments":
        bot.edit_message_text(chat_id=c.message.chat.id, message_id=c.message.message_id,
                              text="Анти-комменты: за сутки проверено 0 / удалено 0 / карантин 0",
                              reply_markup=back_kb("back_main"))
    elif data == "quarantine":
        bot.edit_message_text(chat_id=c.message.chat.id, message_id=c.message.message_id,
                              text="Карантин (общий): 0 записей",
                              reply_markup=back_kb("back_main"))
    elif data == "ads":
        bot.edit_message_text(chat_id=c.message.chat.id, message_id=c.message.message_id,
                              text="💼 Реклама: новые лиды 0",
                              reply_markup=back_kb("back_main"))
    elif data == "settings":
        bot.edit_message_text(chat_id=c.message.chat.id, message_id=c.message.message_id,
                              text="⚙️ Настройки (минимум):\n— Алерты: Вкл\n— Карантин: 24ч",
                              reply_markup=back_kb("back_main"))
    elif data == "back_main":
        bot.edit_message_text(chat_id=c.message.chat.id, message_id=c.message.message_id,
                              text="Панель управления", reply_markup=main_menu())

# --- Webhook: максимально простой и надёжный ---
@app.post("/tg/webhook")
async def tg_webhook(request: Request):
    body = await request.body()
    update = types.Update.de_json(body.decode("utf-8"))
    bot.process_new_updates([update])
    return {"ok": True}

# Быстрый пинг в TG (помогает проверить токен/чат)
import httpx
@app.get("/debug/ping_tg")
async def debug_ping_tg():
    chat_id = os.getenv("TELEGRAM_ADMIN_CHAT_ID", "")
    token = os.getenv("TELEGRAM_BOT_TOKEN", "")
    if not (chat_id and token):
        return {"ok": False, "err": "TELEGRAM_* envs missing"}
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {"chat_id": chat_id, "text": "Бот жив. Вот меню ↓", "reply_markup": main_menu().to_dic()}
    async with httpx.AsyncClient(timeout=10) as client:
        r = await client.post(url, json=payload)
        data = r.json()
    return {"ok": True, "tg": data}

# health (если уже есть — не страшно, дубли не ломают)
@app.get("/health")
def health():
    return {"ok": True}

# Планировщик (digest и пр.)
@app.on_event("startup")
def on_startup():
    init_jobs()
    scheduler.start()
