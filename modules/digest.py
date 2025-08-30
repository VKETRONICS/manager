# modules/digest.py
import os
import asyncio
import datetime as dt
from zoneinfo import ZoneInfo

import httpx
from sqlalchemy import text

# === Настройки таймзоны и токенов ===
# TZ влияет на то, за какие сутки считаем метрики (ставим МСК)
TZ = os.getenv("TZ", "Europe/Moscow")

TG_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TG_ADMIN = os.getenv("TELEGRAM_ADMIN_CHAT_ID", "")
VK_TOKEN = os.getenv("VK_SERVICE_TOKEN", "")
VK_GROUP_ID = os.getenv("VK_GROUP_ID", "")

# Подключение к БД: используем ваш общий engine
from db import engine


def _yesterday_window(tz: str):
    zone = ZoneInfo(tz)
    now = dt.datetime.now(zone)
    start = (now - dt.timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
    end = start + dt.timedelta(days=1)
    # Приводим к UTC для timestamptz
    return start.astimezone(ZoneInfo("UTC")), end.astimezone(ZoneInfo("UTC")), now


def _table_exists(conn, table_name: str) -> bool:
    q = text("""
        SELECT EXISTS (
          SELECT 1 FROM information_schema.tables
          WHERE table_schema='public' AND table_name=:t
        )
    """)
    return bool(conn.execute(q, {"t": table_name}).scalar())


def _column_exists(conn, table_name: str, column_name: str) -> bool:
    q = text("""
        SELECT EXISTS (
          SELECT 1 FROM information_schema.columns
          WHERE table_schema='public'
            AND table_name=:t
            AND column_name=:c
        )
    """)
    return bool(conn.execute(q, {"t": table_name, "c": column_name}).scalar())


def _pick_ts_column(conn, table: str) -> str | None:
    # Частые варианты имени столбца времени
    for cand in ("created_at", "created", "inserted_at", "ts"):
        if _column_exists(conn, table, cand):
            return cand
    return None


def _count_new_between(conn, table: str, start_utc: dt.datetime, end_utc: dt.datetime) -> int | None:
    if not _table_exists(conn, table):
        return None
    ts_col = _pick_ts_column(conn, table)
    if not ts_col:
        return None
    q = text(f"""
        SELECT COUNT(*) FROM {table}
        WHERE {ts_col} >= :start AND {ts_col} < :end
    """)
    return int(conn.execute(q, {"start": start_utc, "end": end_utc}).scalar() or 0)


async def _ping_vk() -> tuple[bool, str | None]:
    if not VK_TOKEN or not VK_GROUP_ID:
        return False, "VK токен/ID не заданы"
    url = "https://api.vk.com/method/groups.getById"
    params = {"group_id": VK_GROUP_ID, "access_token": VK_TOKEN, "v": "5.131"}
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.get(url, params=params)
            data = r.json()
        if "error" in data:
            return False, f"VK error {data['error'].get('error_code')}: {data['error'].get('error_msg')}"
        return True, None
    except Exception as e:
        return False, str(e)


async def _send_tg(text_html: str) -> None:
    if not TG_TOKEN or not TG_ADMIN:
        return
    url = f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage"
    payload = {"chat_id": TG_ADMIN, "text": text_html, "parse_mode": "HTML", "disable_web_page_preview": True}
    async with httpx.AsyncClient(timeout=10) as client:
        await client.post(url, json=payload)


def _ensure_stats_daily(conn):
    conn.execute(text("""
        CREATE TABLE IF NOT EXISTS stats_daily (
            day date PRIMARY KEY,
            quarantine_new integer DEFAULT 0,
            leads_new integer DEFAULT 0,
            vk_ok boolean,
            db_ok boolean,
            created_at timestamptz DEFAULT now()
        )
    """))


def _upsert_stats_daily(conn, day: dt.date, quarantine_new: int | None,
                        leads_new: int | None, vk_ok: bool, db_ok: bool):
    conn.execute(text("""
        INSERT INTO stats_daily (day, quarantine_new, leads_new, vk_ok, db_ok)
        VALUES (:day, :q, :l, :vk, :db)
        ON CONFLICT (day) DO UPDATE
        SET quarantine_new = EXCLUDED.quarantine_new,
            leads_new     = EXCLUDED.leads_new,
            vk_ok         = EXCLUDED.vk_ok,
            db_ok         = EXCLUDED.db_ok
    """), {
        "day": day,
        "q": quarantine_new if quarantine_new is not None else 0,
        "l": leads_new if leads_new is not None else 0,
        "vk": vk_ok,
        "db": db_ok
    })


async def send_daily_digest():
    """Собираем метрики за вчера и шлём отчёт админу."""
    start_utc, end_utc, now_local = _yesterday_window(TZ)
    day_local = (now_local - dt.timedelta(days=1)).date()

    # 1) VK доступность
    vk_ok, vk_err = await _ping_vk()

    # 2) БД + метрики
    db_ok = False
    quarantine_new = leads_new = None
    try:
        with engine.begin() as conn:
            conn.execute(text("SELECT 1"))
            db_ok = True

            quarantine_new = _count_new_between(conn, "quarantine", start_utc, end_utc)
            leads_new = _count_new_between(conn, "ads_leads", start_utc, end_utc)

            _ensure_stats_daily(conn)
            _upsert_stats_daily(conn, day_local, quarantine_new, leads_new, vk_ok, db_ok)
    except Exception:
        db_ok = False

    q_str = "—" if quarantine_new is None else str(quarantine_new)
    l_str = "—" if leads_new is None else str(leads_new)

    lines = [
        f"<b>📊 Еженедельная сводка — {day_local.strftime('%d.%m.%Y')}</b>",
        "",
        f"• VK API: {'✅' if vk_ok else '❌'}" + ("" if vk_ok else f" (<i>{vk_err}</i>)"),
        f"• База данных: {'✅' if db_ok else '❌'}",
        f"• Новых в карантине за сутки: <b>{q_str}</b>",
        f"• Новых лидов за сутки: <b>{l_str}</b>",
        "",
        "ℹ️ Анти-лайки/анти-подписчики пока не включены — поэтому «Карантин» может быть 0.",
        "   Следующий шаг: включить <b>Анти-лайки v1</b> (скан 1–3 постов).",
    ]
    await _send_tg("\n".join(lines))


def schedule_daily_digest(scheduler):
    """
    Планировщик: ПОНЕДЕЛЬНИК в 10:00 по МСК.
    Имя функции оставляем прежним, чтобы в scheduler.py ничего больше не менять.
    """
    try:
        scheduler.remove_job("weekly_digest_mon_10_msk")
    except Exception:
        pass

    scheduler.add_job(
        send_daily_digest,
        trigger="cron",
        day_of_week="mon",
        hour=10,
        minute=0,
        timezone=ZoneInfo("Europe/Moscow"),
        id="weekly_digest_mon_10_msk",
        replace_existing=True,
        coalesce=True,
        misfire_grace_time=600,
        max_instances=1,
    )
