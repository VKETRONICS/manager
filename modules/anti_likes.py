# modules/anti_likes.py
import os
import math
import asyncio
import datetime as dt
from typing import List, Dict, Tuple
from zoneinfo import ZoneInfo

import httpx
from sqlalchemy import text

# === ENV / конфиг ===
VK_TOKEN = os.getenv("VK_SERVICE_TOKEN", "")
VK_GROUP_ID = os.getenv("VK_GROUP_ID", "")  # число без минуса
TZ = os.getenv("TZ", "Europe/Amsterdam")

# Управление поведением
ANTI_LIKES_ENABLED = os.getenv("ANTI_LIKES_ENABLED", "true").lower() == "true"
ANTI_LIKES_N_POSTS = int(os.getenv("ANTI_LIKES_N_POSTS", "5"))      # сканируем последние N постов
ANTI_LIKES_MAX_PER_POST = int(os.getenv("ANTI_LIKES_MAX_PER_POST", "1000"))  # максимум лайков на пост за проход

# Пороги решений (безопасные по умолчанию)
BAN_ENABLED = os.getenv("ANTI_LIKES_BAN_ENABLED", "false").lower() == "true"  # по умолчанию dry-run
BAN_THRESHOLD = int(os.getenv("ANTI_LIKES_BAN_THRESHOLD", "5"))               # score >= 5 → бан
QUARANTINE_MIN = int(os.getenv("ANTI_LIKES_QUARANTINE_MIN", "3"))             # 3–4 → карантин
QUARANTINE_HOURS = int(os.getenv("ANTI_LIKES_QUARANTINE_HOURS", "24"))        # обычный карантин
WAVE_QUARANTINE_HOURS = int(os.getenv("ANTI_LIKES_WAVE_QH", "6"))             # во «волну» (если включим детектор)

# Лимиты (перепишем под «умную адаптацию» позже, сейчас — безопасные дефолты)
X_LIKE_PER_RUN = int(os.getenv("ANTI_LIKES_X_PER_RUN", "40"))   # max банов за проход
Y_LIKE_PER_DAY = int(os.getenv("ANTI_LIKES_Y_PER_DAY", "200"))  # max банов за сутки

# Алерты в TG (опционально)
TG_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TG_ADMIN = os.getenv("TELEGRAM_ADMIN_CHAT_ID", "")
SEND_ALERTS = os.getenv("ANTI_ALERTS", "true").lower() == "true"

# SQLAlchemy engine из вашего проекта
from db import engine  # noqa: E402


API_VERSION = "5.131"


# ---------- Вспомогательные ----------
async def _vk_call(method: str, params: Dict) -> Dict:
    """Вызов VK API c httpx (async)."""
    url = f"https://api.vk.com/method/{method}"
    payload = dict(params)
    payload.update({"access_token": VK_TOKEN, "v": API_VERSION})
    async with httpx.AsyncClient(timeout=15) as client:
        r = await client.get(url, params=payload)
        data = r.json()
    if "error" in data:
        raise RuntimeError(f"VK error {data['error'].get('error_code')}: {data['error'].get('error_msg')}")
    return data["response"]


async def _send_tg(msg: str) -> None:
    if not (TG_TOKEN and TG_ADMIN and SEND_ALERTS):
        return
    url = f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage"
    payload = {"chat_id": TG_ADMIN, "text": msg, "disable_web_page_preview": True}
    async with httpx.AsyncClient(timeout=10) as client:
        await client.post(url, json=payload)


def _now_local() -> dt.datetime:
    return dt.datetime.now(ZoneInfo(TZ))


def _today_local() -> dt.date:
    return _now_local().date()


# ---------- DB: свои таблицы (ничего чужого не трогаем) ----------
def _ensure_tables(conn) -> None:
    # Карантин лайкеров — отдельная таблица, чтобы не конфликтовать с вашей "quarantine"
    conn.execute(text("""
        CREATE TABLE IF NOT EXISTS quarantine_likes (
            id           bigserial PRIMARY KEY,
            created_at   timestamptz DEFAULT now(),
            vk_user_id   bigint NOT NULL,
            vk_post_id   bigint NOT NULL,
            reason       text,
            score        integer,
            status       text DEFAULT 'pending'  -- pending | kept | banned
        )
    """))
    conn.execute(text("CREATE INDEX IF NOT EXISTS idx_quarlikes_user ON quarantine_likes(vk_user_id)"))
    conn.execute(text("CREATE INDEX IF NOT EXISTS idx_quarlikes_post ON quarantine_likes(vk_post_id)"))

    # Счётчики за день (чтобы лимит Y соблюдать)
    conn.execute(text("""
        CREATE TABLE IF NOT EXISTS likes_counters_daily (
            day date PRIMARY KEY,
            removed integer DEFAULT 0,
            quarantined integer DEFAULT 0,
            checked integer DEFAULT 0
        )
    """))


def _inc_daily(conn, day: dt.date, removed: int = 0, quarantined: int = 0, checked: int = 0) -> None:
    conn.execute(text("""
        INSERT INTO likes_counters_daily(day, removed, quarantined, checked)
        VALUES (:d, :r, :q, :c)
        ON CONFLICT (day) DO UPDATE
        SET removed     = likes_counters_daily.removed + EXCLUDED.removed,
            quarantined = likes_counters_daily.quarantined + EXCLUDED.quarantined,
            checked     = likes_counters_daily.checked + EXCLUDED.checked
    """), {"d": day, "r": removed, "q": quarantined, "c": checked})


def _get_removed_today(conn, day: dt.date) -> int:
    row = conn.execute(text("SELECT removed FROM likes_counters_daily WHERE day=:d"), {"d": day}).fetchone()
    return int(row[0]) if row else 0


def _add_quarantine_like(conn, vk_user_id: int, vk_post_id: int, reason: str, score: int) -> None:
    conn.execute(text("""
        INSERT INTO quarantine_likes(vk_user_id, vk_post_id, reason, score, status)
        VALUES (:u, :p, :reason, :score, 'pending')
    """), {"u": vk_user_id, "p": vk_post_id, "reason": reason, "score": score})


# ---------- VK helpers ----------
async def _get_recent_posts(n: int) -> List[int]:
    """Возвращает ID последних n постов группы."""
    owner_id = -abs(int(VK_GROUP_ID))
    resp = await _vk_call("wall.get", {"owner_id": owner_id, "count": max(1, min(n, 100))})
    items = resp.get("items", [])
    return [it["id"] for it in items if "id" in it]


async def _get_likes_user_ids(post_id: int, limit: int) -> List[int]:
    """Собираем ID лайкеров поста с пагинацией."""
    owner_id = -abs(int(VK_GROUP_ID))
    ids: List[int] = []
    offset = 0
    step = 1000  # максимум для likes.getList
    while offset < limit:
        count = min(step, limit - offset)
        resp = await _vk_call("likes.getList", {
            "type": "post", "owner_id": owner_id, "item_id": post_id,
            "count": count, "offset": offset
        })
        batch = resp.get("items", [])
        ids.extend(batch)
        if len(batch) < count:
            break  # больше нет
        offset += count
        await asyncio.sleep(0.3)
    return ids


async def _users_get(uids: List[int]) -> List[Dict]:
    """Инфо о пользователях батчами (поля для скоринга)."""
    out: List[Dict] = []
    if not uids:
        return out
    # VK users.get ограничение на ids — безопасно возьмём батчи по 500
    for i in range(0, len(uids), 500):
        chunk = uids[i:i+500]
        resp = await _vk_call("users.get", {
            "user_ids": ",".join(str(x) for x in chunk),
            "fields": "has_photo,is_closed,last_seen,photo_50,domain"
        })
        out.extend(resp)
        await asyncio.sleep(0.35)
    return out


# ---------- Скоринг ----------
def _score_user(u: Dict) -> Tuple[int, List[str]]:
    """Возвращает (score, причины). Чем выше — тем вероятнее фейк."""
    reasons: List[str] = []
    # 100% фейки
    if "deactivated" in u:
        return 100, ["deactivated"]

    s = 0
    # нет фото
    if not u.get("has_photo", False):
        s += 2
        reasons.append("no_photo")

    # приват + нет last_seen усиливает подозрение
    if u.get("is_closed", False):
        s += 1
        reasons.append("private")

    if "last_seen" not in u:
        s += 1
        reasons.append("no_last_seen")

    # иногда дефолтная аватарка — camera_50.png
    if str(u.get("photo_50", "")).endswith("camera_50.png"):
        s += 1
        reasons.append("default_avatar")

    return s, reasons


async def _ban_user(vk_user_id: int) -> bool:
    """Блокировка в группе (бан)."""
    if not BAN_ENABLED:
        return False
    try:
        await _vk_call("groups.ban", {"group_id": int(VK_GROUP_ID), "owner_id": vk_user_id})
        return True
    except Exception:
        # не критично — просто не удалось забанить (лимиты/права)
        return False


# ---------- Основной проход ----------
async def run_anti_likes_once() -> Dict:
    """
    Один проход анти-лайков:
    - берём последние посты
    - собираем лайкеров
    - скорим и принимаем решение (бан/карантин/оставить) с лимитами
    """
    if not (ANTI_LIKES_ENABLED and VK_TOKEN and VK_GROUP_ID):
        return {"ok": False, "reason": "disabled_or_no_vk_creds"}

    local_day = _today_local()

    total_checked = 0
    total_banned = 0
    total_quarantine = 0
    summaries = []

    try:
        with engine.begin() as conn:
            _ensure_tables(conn)
            banned_today = _get_removed_today(conn, local_day)

        posts = await _get_recent_posts(ANTI_LIKES_N_POSTS)

        for post_id in posts:
            if total_banned >= X_LIKE_PER_RUN:
                break

            uids = await _get_likes_user_ids(post_id, ANTI_LIKES_MAX_PER_POST)
            if not uids:
                continue

            infos = await _users_get(uids)
            checked_this_post = 0
            banned_this_post = 0
            quar_this_post = 0

            with engine.begin() as conn:
                for u in infos:
                    uid = int(u["id"])
                    score, reasons = _score_user(u)
                    decision = "keep"

                    if score >= BAN_THRESHOLD and total_banned < X_LIKE_PER_RUN and (banned_today + total_banned) < Y_LIKE_PER_DAY:
                        ok = await _ban_user(uid)
                        if ok:
                            decision = "ban"
                            total_banned += 1
                            banned_this_post += 1
                        else:
                            # если не удалось забанить — отправим в карантин
                            decision = "quarantine"

                    if decision == "quarantine" or (QUARANTINE_MIN <= score < BAN_THRESHOLD):
                        _add_quarantine_like(conn, uid, post_id, ",".join(reasons) or "suspect", score)
                        total_quarantine += 1
                        quar_this_post += 1

                    checked_this_post += 1
                    total_checked += 1

                _inc_daily(conn, local_day, removed=banned_this_post, quarantined=quar_this_post, checked=checked_this_post)

            summaries.append(f"Пост {post_id}: проверено {checked_this_post}, удалено {banned_this_post}, карантин {quar_this_post}")

            # Ограничитель на проход
            if total_banned >= X_LIKE_PER_RUN:
                break

        # Алерт, если есть что сказать
        if (total_banned + total_quarantine) > 0:
            msg = "👍 Анти-лайки: " + "; ".join(summaries)
            await _send_tg(msg)

        return {
            "ok": True,
            "checked": total_checked,
            "banned": total_banned,
            "quarantine": total_quarantine,
            "posts": len(posts)
        }

    except Exception as e:
        await _send_tg(f"⚠️ Анти-лайки: ошибка: {e}")
        return {"ok": False, "error": str(e)}


# ---------- Интеграция с APScheduler (BackgroundScheduler) ----------
def _run_sync():
    """Обёртка для запуска async в потоковом планировщике."""
    asyncio.run(run_anti_likes_once())


def schedule_anti_likes(scheduler, minutes: int = 30):
    """
    Зарегистрировать периодическую задачу.
    НИЧЕГО не вызывает автоматически — просто регистрирует job.
    """
    try:
        scheduler.remove_job("anti_likes_scan")
    except Exception:
        pass

    # каждые 30 минут (по умолчанию)
    scheduler.add_job(
        _run_sync,
        trigger="interval",
        minutes=max(5, int(minutes)),
        id="anti_likes_scan",
        replace_existing=True,
        coalesce=True,
        misfire_grace_time=300,
        max_instances=1,
    )
