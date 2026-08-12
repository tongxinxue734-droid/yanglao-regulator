# -*- coding: utf-8 -*-
"""韧性康养 · 演练归档库 — 数据服务
消防/防噎食/防跌倒演练记录 · 超半年未演练自动扣分（E3）
"""
import random
from datetime import datetime, timedelta
from sqlalchemy.orm import Session

from models import Organization
from services.mask import org_label


# 必须演练项目（对应指标）
DRILL_TYPES = [
    ("消防疏散演练", "E3", "每半年至少 1 次"),
    ("防噎食应急演练", "E3", "每半年至少 1 次"),
    ("防跌倒应急预案演练", "E3", "每半年至少 1 次"),
]


def drill_records(session: Session):
    """各机构各演练项目：最近演练时间 + 是否逾期（>180 天未做）"""
    rnd = random.Random(88)
    orgs = session.query(Organization).order_by(Organization.id).all()
    rows = []
    for o in orgs:
        for name, ind, freq in DRILL_TYPES:
            days_ago = rnd.choice([20, 45, 90, 130, 175, 190, 210, 260])
            last = datetime.now() - timedelta(days=days_ago)
            overdue = days_ago > 180
            rows.append({
                "机构": org_label(o.name, o.code), "演练项目": name, "对应指标": ind,
                "最近演练": last.strftime("%Y-%m-%d"),
                "距今": f"{days_ago} 天",
                "状态": "🔴 已逾期（超半年）" if overdue else "🟢 合规",
                "现场照片": "📸 已归档" if rnd.random() > 0.15 else "⚠️ 缺照片",
                "参与人数": rnd.randint(15, 60),
                "逾期": overdue,
            })
    rows.sort(key=lambda r: (r["机构"], r["演练项目"]))
    return rows


def drill_summary(session: Session):
    recs = drill_records(session)
    total = len(recs)
    overdue = sum(1 for r in recs if r["逾期"])
    return total, overdue
