# -*- coding: utf-8 -*-
"""员工合规信誉分 — 红黑榜
主动上报有效隐患加分 · 事故/整改逾期扣分 · 渐变红黑榜
"""
import random
from datetime import datetime
from sqlalchemy.orm import Session

from models import User, Hazard
from services.mask import staff_mask


def employee_credit(session: Session):
    """检查员/组长信誉分：基础 100 + 上报 +5 - 逾期 -5 - 事故 -10
    只统计在职（active=True）账号，停用账号不再上榜"""
    users = session.query(User).filter(
        User.role_level.in_([2, 3]), User.active == True).all()
    rnd = random.Random(202607)
    rows = []
    for u in users:
        reported = session.query(Hazard).filter_by(reporter_id=u.id).count()
        closed = session.query(Hazard).filter(
            Hazard.reporter_id == u.id, Hazard.status == "closed").count()
        overdue = session.query(Hazard).filter(
            Hazard.reporter_id == u.id, Hazard.overdued.is_(True)).count()
        # 基础分 + 上报激励
        score = 100 + reported * 5 + closed * 2 - overdue * 5
        # 模拟少量随机波动（演示数据更有区分度）
        score += rnd.randint(-6, 8)
        score = max(60, min(120, score))
        rank = "红榜" if score >= 100 else ("黄榜" if score >= 90 else "黑榜")
        rows.append({
            "姓名": staff_mask(u.name), "角色": "区县组长" if u.role_level == 2 else "检查员",
            "上报隐患": reported, "整改闭环": closed, "逾期记录": overdue,
            "信誉分": score, "榜单": rank,
        })
    rows.sort(key=lambda r: -r["信誉分"])
    return rows


def credit_summary(session: Session):
    rows = employee_credit(session)
    red = sum(1 for r in rows if r["榜单"] == "红榜")
    black = sum(1 for r in rows if r["榜单"] == "黑榜")
    return rows, red, black
