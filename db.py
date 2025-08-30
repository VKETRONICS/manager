from sqlalchemy import create_engine, MetaData, Table, Column, Integer, String, Text, DateTime, Boolean, JSON, BigInteger
from sqlalchemy.orm import Session
from sqlalchemy.sql import func
from config import load_config

cfg = load_config()
engine = create_engine(cfg.DATABASE_URL, pool_pre_ping=True, future=True)
meta = MetaData()

# Simple tables (extend later)
stats_daily = Table("stats_daily", meta,
    Column("id", Integer, primary_key=True),
    Column("date", String(10), index=True),
    Column("metric", String(50)),
    Column("value", Integer, default=0),
)

quarantine = Table("quarantine", meta,
    Column("id", Integer, primary_key=True),
    Column("platform", String(16)),  # members/likes/comments/ads
    Column("user_id", BigInteger, index=True),
    Column("reason", String(255)),
    Column("score", Integer),
    Column("first_seen", DateTime(timezone=True), server_default=func.now()),
    Column("extra", JSON),
)

ads_leads = Table("ads_leads", meta,
    Column("id", Integer, primary_key=True),
    Column("source", String(32)),  # vk/tg/email
    Column("name", String(255)),
    Column("profile_link", String(512)),
    Column("format", String(128)),
    Column("budget", String(128)),
    Column("audience", Text),
    Column("timing", String(128)),
    Column("contacts", String(256)),
    Column("examples", Text),
    Column("priority", String(32)), # low/medium/high
    Column("flags", String(256)),
    Column("status", String(32), default="new"), # new/in_work/archived
    Column("created_at", DateTime(timezone=True), server_default=func.now()),
)

def init_db():
    meta.create_all(engine)
