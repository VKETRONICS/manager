# ETRONICS Community Bot — Render package

Единый бот «на века» для ВК + Telegram:

- 🛡 Анти‑накрутка подписчиков / лайков / комментов (модули-заглушки, подключите VK API)
- 👍 Анти‑лайки (скан последних постов, бан фейков) — скелет
- 💬 Анти‑комменты (удаление спама) — скелет
- 🔁 Кросспостинг ВК → TG — скелет
- 💼 Умный приём рекламных лидов — готова структура и БД
- 📊 Суточные сводки — шедулер подключён (пока заглушки)
- 🧭 Инлайн‑панель с простыми меню

> Этот пакет — **готовая архитектура и рабочая панель в TG**. Подключите VK API вызовы в модулях и заполните .env — остальное уже собрано.

## 1) Быстрый старт на Render

1. Создайте новый **Web Service** на Render из этого репозитория (либо загрузите zip и залейте в GitHub).
2. В **Environment** добавьте переменные (см. `.env.example`):
   - `VK_GROUP_ID`, `VK_SERVICE_TOKEN`
   - `TELEGRAM_BOT_TOKEN`, `TELEGRAM_ADMIN_CHAT_ID`
   - `DATABASE_URL` (Render PostgreSQL)
   - `PUBLIC_BASE_URL` (публичный URL сервиса после деплоя)
   - опц: `OPENAI_API_KEY`, `WEBHOOK_SECRET`, `TZ`
3. Render автоматически установит зависимости (`requirements.txt`) и запустит `Procfile`.
4. Поставьте Telegram‑webhook:  
   `https://api.telegram.org/bot<TELEGRAM_BOT_TOKEN>/setWebhook?url=<PUBLIC_BASE_URL>/tg/webhook`
5. В Telegram отправьте боту `/start` → увидите **главное меню**.

## 2) Что нужно от вас (вводные)
- Числовой `VK_GROUP_ID` и **токен сообщества** с правами `groups, wall, users`.
- `TELEGRAM_BOT_TOKEN` и `TELEGRAM_ADMIN_CHAT_ID`.
- Доступ к **Render PostgreSQL** → строка `DATABASE_URL`.
- (Опционально) `OPENAI_API_KEY` для автоподбора хэштегов/текстов.
- Публичный домен Render `PUBLIC_BASE_URL` для вебхука.
- Список **ключевых слов/доменов** для анти‑комментов/анти‑рекламы (можно позже).

## 3) Где доработать (минимальная интеграция VK API)
В проекте уже есть каркас и UI. Достаточно реализовать VK‑вызовы в `vk_api_client.py` и подключить их в задачах:
- `groups.getMembers`, `groups.removeUser`, `groups.ban`
- `wall.get`, `likes.getList`, `wall.getComments`, `wall.deleteComment`
- Логику автопилота разместите в отдельных модулях `modules/` (скелеты предусмотрены).

## 4) OpenAI (опционально)
- Укажите `OPENAI_API_KEY` → модуль `openai_utils.suggest_hashtags(title, genre)` вернёт 6–8 тегов.
- Так же можно использовать для мягких шаблонов ответов рекламодателям.

## 5) Структура
```
app.py                 # FastAPI + Telegram webhook + меню
config.py              # загрузка конфигурации из ENV
db.py                  # SQLAlchemy + таблицы (init_db)
scheduler.py           # APScheduler и задачи (пока заглушки)
vk_api_client.py       # VK API вызовы (реализуйте по шагам)
openai_utils.py        # хэштеги/тексты (опционально)
bot/ui.py              # инлайн‑кнопки и панели
modules/ads_assistant.py # диалог с рекламодателями + сохранение лида
requirements.txt
Procfile
.env.example
```

## 6) Советы по продакшену
- Включите `WEBHOOK_SECRET` и прокидывайте подпись в заголовке при необходимости.
- Поставьте `ALERTS_ENABLED=true` для событийных уведомлений.
- Следующий шаг — вынести state‑логику в модули `modules/` и дописать VK вызовы (по нашей спецификации).
- Когда заработает — добавляйте **анти‑лайки/комменты** и **кросспостинг** по согласованному плану.
