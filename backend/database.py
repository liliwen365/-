# -*- coding: utf-8 -*-
"""SQLite数据库 - SQLAlchemy 2.0。"""
from sqlalchemy import create_engine, Column, String, Integer, Float, Text, DateTime, Boolean
from sqlalchemy.orm import DeclarativeBase, sessionmaker
from datetime import datetime, timezone

from backend.config import settings

engine = create_engine(f"sqlite:///{settings.DB_PATH}", echo=False)
SessionLocal = sessionmaker(bind=engine)


class Base(DeclarativeBase):
    pass


class PluginModel(Base):
    __tablename__ = "plugins"

    name = Column(String, primary_key=True)
    display_name = Column(String, nullable=False)
    version = Column(String, default="0.0.0")
    description = Column(Text, default="")
    category = Column(String, default="custom")
    icon = Column(String, default="")
    color = Column(String, default="#2196F3")
    author = Column(String, default="")
    enabled = Column(Boolean, default=True)
    installed_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class TaskHistoryModel(Base):
    __tablename__ = "task_history"

    id = Column(Integer, primary_key=True, autoincrement=True)
    plugin_name = Column(String, nullable=False, index=True)
    feature_id = Column(String, default="")
    status = Column(String, default="pending")
    params_json = Column(Text, default="")
    result_json = Column(Text, default="")
    progress_percent = Column(Float, default=0)
    progress_message = Column(String, default="")
    error_traceback = Column(Text, default="")
    duration_ms = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    finished_at = Column(DateTime, nullable=True)


class SettingModel(Base):
    __tablename__ = "settings"

    key = Column(String, primary_key=True)
    value = Column(Text, default="")


class ScheduleModel(Base):
    __tablename__ = "schedules"

    id = Column(Integer, primary_key=True, autoincrement=True)
    plugin_name = Column(String, nullable=False, index=True)
    feature_id = Column(String, default="")
    cron_expr = Column(String, nullable=False)
    params_json = Column(Text, default="")
    enabled = Column(Boolean, default=True)
    last_run_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


def create_tables():
    Base.metadata.create_all(engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
