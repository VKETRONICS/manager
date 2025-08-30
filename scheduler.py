from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from config import load_config

cfg = load_config()
scheduler = BackgroundScheduler(timezone=cfg.TZ)

# Placeholders: connect real jobs from modules when ready
def init_jobs():
    # anti-members
    scheduler.add_job(lambda: None, IntervalTrigger(minutes=30), id="members_scan", replace_existing=True)
    # anti-likes
    scheduler.add_job(lambda: None, IntervalTrigger(minutes=30), id="likes_scan", replace_existing=True)
    # anti-comments
    scheduler.add_job(lambda: None, IntervalTrigger(minutes=30), id="comments_scan", replace_existing=True)
    # daily digest 23:59
    scheduler.add_job(lambda: None, CronTrigger(hour=23, minute=59), id="daily_digest", replace_existing=True)
