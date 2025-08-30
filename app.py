# app.py
import os, hmac, hashlib, asyncio
from fastapi import FastAPI, Request, HTTPException
from dotenv import load_dotenv
load_dotenv()

from config import load_config
from db import init_db
from scheduler import scheduler, init_jobs

from telebot import TeleBot, types
from bot.ui import main_menu, back_kb, likes_kb   # ✅ добавили likes_kb
from modules.anti_likes import run_anti_likes_once  # ✅ для ручного запуска

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
                              text="Анти-лайки: мониторинг включён.\n"
                                   "Можешь запустить проверку вручную кнопкой ниже.",
                              reply_markup=likes_kb())  # ✅ показываем меню с 2 кнопками
    elif data == "run_anti_likes":
        if str(c.from_user.id) != str(cfg.TELEGRAM_ADMIN_CHAT_ID):
            bot.answer_callback_query(c.id, "Недостаточно прав", show_alert=True)
        else:
            bot.answer_callback_query(c.id)
            bot.edit_message_text(chat_id=c.message.chat.id,
                                  message_id=c.message.message_id,
                                  text="🔄 Запускаю проверку лайков…",
                                  reply_markup=back_kb("back_main"))
            try:
                result = asyncio.run(run_anti_likes_once())
                if result.get("ok"):
                    checked = result.get("checked", 0)
                    banned = result.get("banned", 0)
                    quarantine = result.get("quarantine", 0)
                    posts = result.get("posts", 0)
                    text = (f"👍 Готово.\n"
                            f"Постов проверено: {posts}\n"
                            f"Лайкеров проверено: {checked}\n"
                            f"Удалено: {banned}\n"
                            f"Карантин: {quarantine}\n\n"
                            f"Режим: {'боевой' if os.getenv('ANTI_LIKES_BAN_ENABLED','false').lower()=='true' else 'dry-run'}")
                else:
                    text = f"⚠️ Ошибка: {result.get('error','unknown')}"
            except Exception as e:
                text = f"⚠️ Исключение при запуске: {e}"

            bot.edit_message_text(chat_id=c.message.chat.id,
                                  message_id=c.message.message_id,
                                  text=text,
                                  reply_markup=likes_kb())  # ✅ остаёмся в разделе «Анти-лайки»
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

# --- Webhook ---
@app.post("/tg/webhook")
async def tg_webhook(request: Request):
    body = await request.body()
    update = types.Update.de_json(body.decode("utf-8"))
    bot.process_new_updates([update])
    return {"ok": True}

# health (если уже есть — не страшно)
@app.get("/health")
def health():
    return {"ok": True}

# Планировщик
@app.on_event("startup")
def on_startup():
    init_jobs()
    scheduler.start()
