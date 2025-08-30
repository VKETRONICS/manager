# scheduler.py
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

from config import load_config
from modules.digest import schedule_daily_digest
from modules.anti_likes import schedule_anti_likes  # ✅ добавили анти-лайки

cfg = load_config()
scheduler = BackgroundScheduler(timezone=cfg.TZ)

def init_jobs():
    # анти-подписчики (заглушка — пока без логики)
    scheduler.add_job(
        lambda: None,
        IntervalTrigger(minutes=30),
        id="members_scan",
        replace_existing=True
    )

    # анти-лайки — реальная задача (каждые 30 минут по умолчанию)
    schedule_anti_likes(scheduler)  # ✅ регистрируем job anti_likes_scan

    # анти-комменты (заглушка — пока без логики)
    scheduler.add_job(
        lambda: None,
        IntervalTrigger(minutes=30),
        id="comments_scan",
        replace_existing=True
    )

    # еженедельная сводка: понедельник в 10:00 по МСК
    schedule_daily_digest(scheduler)
