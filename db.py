# -*- coding: utf-8 -*-
"""数据库引擎与会话管理"""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session

import config
from models import Base

engine = create_engine(
    config.DATABASE_URL,
    connect_args={"check_same_thread": False},  # Streamlit 多线程访问
)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def init_db():
    Base.metadata.create_all(engine)


def get_session():
    return SessionLocal()
