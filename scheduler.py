from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

from config import load_config
from modules.digest import schedule_daily_digest


cfg = load_config()
scheduler = BackgroundScheduler(timezone=cfg.TZ)


def init_jobs():
    # анти-подписчики (заглушка)
    scheduler.add_job(
        lambda: None,
        IntervalTrigger(minutes=30),
        id="members_scan",
        replace_existing=True
    )

    # анти-лайки (заглушка)
    scheduler.add_job(
        lambda: None,
        IntervalTrigger(minutes=30),
        id="likes_scan",
        replace_existing=True
    )

    # анти-комменты (заглушка)
    scheduler.add_job(
        lambda: None,
        IntervalTrigger(minutes=30),
        id="comments_scan",
        replace_existing=True
    )

    # еженедельная сводка: понедельник в 10:00 по МСК
    schedule_daily_digest(scheduler)
