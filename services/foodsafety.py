# -*- coding: utf-8 -*-
"""阳光明厨与食药溯源 — 数据服务
48h 食品留样数字化台账 · 餐具每日消杀 · 许可证到期预警
"""
import random
from datetime import datetime, timedelta
from sqlalchemy.orm import Session

from models import Organization
from services.mask import org_label, staff_mask


# ============ 48h 留样台账（模拟数据） ============
def sample_logs(session: Session):
    rnd = random.Random(21)
    orgs = session.query(Organization).order_by(Organization.id).all()
    dishes = ["土豆烧牛肉", "清蒸鲈鱼", "西红柿炒蛋", "冬瓜排骨汤", "麻婆豆腐",
              "芹菜炒肉丝", "胡萝卜炖鸡", "清炒时蔬", "紫菜蛋花汤", "糖醋里脊"]
    rows = []
    for o in orgs[:4]:
        for d in range(6):
            dt = datetime.now() - timedelta(days=d)
            expiry = dt + timedelta(hours=48)
            for meal in ["早餐", "午餐", "晚餐"]:
                rows.append({
                    "机构": org_label(o.name, o.code),
                    "日期": dt.strftime("%m-%d"),
                    "餐次": meal,
                    "菜品": rnd.choice(dishes),
                    "留样克重": f"{rnd.choice([125, 150, 150, 200])}g",
                    "留样人": staff_mask(rnd.choice(["孙师傅", "李师傅", "王师傅", "赵师傅"])),
                    "48h到期": expiry.strftime("%m-%d %H:%M"),
                    "状态": "✅ 在库" if expiry > datetime.now() else "🗑️ 已销毁",
                })
    rows.sort(key=lambda r: (r["机构"], r["日期"], r["餐次"]))
    return rows


# ============ 餐具每日消杀 ============
def disinfection_logs(session: Session):
    rnd = random.Random(33)
    orgs = session.query(Organization).order_by(Organization.id).all()
    rows = []
    for o in orgs[:4]:
        for d in range(3):
            dt = (datetime.now() - timedelta(days=d)).strftime("%m-%d")
            for period in ["早班后", "午班后", "晚班后"]:
                done = rnd.random() > 0.08
                rows.append({
                    "机构": org_label(o.name, o.code), "日期": dt, "时段": period,
                    "消毒方式": rnd.choice(["热力高温", "红外消毒柜", "化学消毒"]) if done else "—",
                    "操作人": staff_mask(rnd.choice(["保洁-刘姐", "保洁-陈姐", "保洁-吴姐"])) if done else "—",
                    "状态": "✅ 已消毒" if done else "🔴 未记录",
                })
    return rows


# ============ 许可证到期预警 ============
def license_alerts(session: Session):
    """《食品经营许可证》到期前 30 天 → 红色警报工单"""
    rnd = random.Random(55)
    orgs = session.query(Organization).order_by(Organization.id).all()
    rows = []
    for o in orgs:
        days_left = rnd.choice([6, 12, 25, 38, 45, 90, 200, 320])
        if days_left <= 30:
            level, status = "🔴 红色警报", "需立即续办"
        elif days_left <= 60:
            level, status = "🟠 预警", "需安排续办"
        else:
            level, status = "🟢 正常", "有效期充足"
        rows.append({
            "机构": org_label(o.name, o.code), "许可证": f"JY{rnd.randint(1000, 9999)}0{rnd.randint(100, 999)}",
            "到期剩余": f"{days_left} 天", "预警": level, "处理建议": status,
        })
    return rows


def license_summary(session: Session):
    alerts = license_alerts(session)
    red = sum(1 for a in alerts if "红色" in a["预警"])
    total = len(alerts)
    return red, total
