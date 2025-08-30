from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

def main_menu():
    kb = InlineKeyboardMarkup()
    kb.row(InlineKeyboardButton("📊 Статус", callback_data="status"))
    kb.row(InlineKeyboardButton("🛡 Подписчики", callback_data="members"),
           InlineKeyboardButton("👍 Анти-лайки", callback_data="likes"))
    kb.row(InlineKeyboardButton("💬 Анти-комменты", callback_data="comments"))
    kb.row(InlineKeyboardButton("📦 Карантин", callback_data="quarantine"))
    kb.row(InlineKeyboardButton("💼 Реклама", callback_data="ads"))
    kb.row(InlineKeyboardButton("⚙️ Настройки", callback_data="settings"))
    return kb

def back_kb(tag="back_main"):
    kb = InlineKeyboardMarkup()
    kb.row(InlineKeyboardButton("🔙 Назад", callback_data=tag))
    return kb

# 👍 Меню для раздела «Анти-лайки»
def likes_kb():
    kb = InlineKeyboardMarkup()
    kb.row(
        InlineKeyboardButton("🔙 Назад", callback_data="back_main"),
        InlineKeyboardButton("🔄 Анти-лайки сейчас", callback_data="run_anti_likes")
    )
    return kb
