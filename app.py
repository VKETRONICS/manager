import hmac, hashlib
from fastapi import FastAPI, Request, HTTPException
from dotenv import load_dotenv
load_dotenv()

from config import load_config
from db import init_db
from scheduler import scheduler, init_jobs
from telebot import TeleBot, types
from bot.ui import main_menu, back_kb

cfg = load_config()
app = FastAPI(title="ETRONICS Community Bot")
init_db()

bot = TeleBot(cfg.TELEGRAM_BOT_TOKEN, parse_mode="HTML")

@app.on_event("startup")
def on_startup():
    init_jobs()
    scheduler.start()

@app.get("/health")
def health():
    return {"ok": True}

@app.post("/tg/webhook")
async def tg_webhook(request: Request):
    body = await request.body()
    if cfg.WEBHOOK_SECRET:
        sig = request.headers.get("X-Telegram-Signature") or ""
        want = hmac.new(cfg.WEBHOOK_SECRET.encode(), body, hashlib.sha256).hexdigest()
        if not hmac.compare_digest(sig, want):
            raise HTTPException(status_code=401, detail="bad signature")
    update = types.Update.de_json(body.decode("utf-8"))
    bot.process_new_updates([update])
    return {"ok": True}

# ----- Telegram UI handlers (skeleton) -----
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

# NOTE: On Render, set webhook via https://api.telegram.org/bot<TOKEN>/setWebhook?url=<PUBLIC_BASE_URL>/tg/webhook
