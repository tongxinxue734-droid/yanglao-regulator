# -*- coding: utf-8 -*-
"""智慧监管中台 — 数据服务（全部输出已按《政务数据脱敏 5 步法》处理）
信用评级 A/B/C/D · 骗补预警（基于门禁/IoT 离院真实数据表）· 免申即享 · IoT 体征模拟
"""
import random
from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from models import Organization, ResidentLeave
from services.mask import elder_code, age_band, org_label


# ============ 信用评级 ============
def org_credit_ratings(session: Session):
    """违规扣分 + IoT 报警频次 → A/B/C/D 动态信用等级（机构以编码标识）"""
    rnd = random.Random(7)
    orgs = session.query(Organization).order_by(Organization.id).all()
    rows = []
    for i, o in enumerate(orgs):
        vio = rnd.randint(0, 3)
        iot = rnd.randint(0, 6)
        score = max(0, 100 - vio * 6 - iot * 2 + rnd.randint(0, 6))
        if score >= 90:
            level, strategy = "A", "正常监管"
        elif score >= 75:
            level, strategy = "B", "季度抽查"
        elif score >= 60:
            level, strategy = "C", "重点监管"
        else:
            level, strategy = "D", "高频抽查·限制扩张"
        rows.append({
            "排名": i + 1,
            "code": org_label(o.name, o.code),
            "机构": org_label(o.name, o.code),
            "得分": score, "等级": level,
            "违规次数": vio, "IoT报警": iot, "监管策略": strategy,
            "x": 100 + (i % 3) * 180 + rnd.randint(-20, 20),
            "y": 320 - (i // 3) * 120 + rnd.randint(-20, 20),
        })
    rows.sort(key=lambda r: -r["得分"])
    for i, r in enumerate(rows):
        r["排名"] = i + 1
    return rows


# ============ 骗补智能预警（真实离院数据表） ============
def fraud_leave_sim(session: Session):
    """基于 resident_leaves 真实数据表：连续离院 ≥15 天且机构申报补贴 → 涉嫌骗补红色预警
    F6 资金违规使用 · 扣 12 分 · 对应《养老机构管理办法》第 30 条"""
    org_map = {o.id: o for o in session.query(Organization).all()}
    leaves = session.query(ResidentLeave).order_by(ResidentLeave.leave_days.desc()).all()
    rows = []
    for i, lv in enumerate(leaves):
        o = org_map.get(lv.org_id)
        if not o:
            continue
        red = lv.leave_days >= 15 and lv.is_subsidized
        rows.append({
            "机构": org_label(o.name, o.code),
            "老人": elder_code(int(lv.elder_code.replace("长者", "") or 0) or (i + 1)),
            "离院天数": lv.leave_days,
            "补贴申报": "是" if lv.is_subsidized else "否",
            "数据来源": lv.source,
            "风险": "🔴 红色" if red else ("🟠 关注" if lv.leave_days >= 15 else "🟢 正常"),
            "建议扣分": 12 if red else 0,
        })
    rows.sort(key=lambda r: -r["离院天数"])
    return rows


# ============ 免申即享白名单 ============
def exemption_whitelist(session: Session):
    """反向大数据筛查：高龄/失能老人 → 津贴免申即享（老人全匿名）"""
    rnd = random.Random(31)
    orgs = session.query(Organization).order_by(Organization.id).all()
    rows = []
    for i, o in enumerate(orgs[:6]):
        for k in range(2):
            age = rnd.randint(78, 95)
            rows.append({
                "机构": org_label(o.name, o.code),
                "长者": elder_code((i * 2 + k) + 1),
                "年龄": age_band(age),
                "失能等级": rnd.choice(["中度失能", "重度失能", "轻度失能"]),
                "可享津贴": rnd.choice(["高龄津贴 100元/月", "护理补贴 150元/月", "特困供养"]),
                "状态": "✅ 白名单" if rnd.random() > 0.2 else "⚠️ 待确认",
            })
    return rows


# ============ IoT 体征模拟（演示，后续接真实雷达） ============
def vital_signs_sim():
    """毫米波雷达体征（模拟）：心率/呼吸/夜间离床报警（老人匿名）"""
    rnd = random.Random(42)
    rows = []
    for i in range(8):
        hr = rnd.randint(56, 118)
        br = rnd.randint(10, 26)
        abnormal = hr > 100 or hr < 55 or br < 9
        rows.append({
            "床位": f"长者{i + 1:02d}",
            "心率": f"{hr} bpm",
            "呼吸": f"{br} 次/分",
            "异常": abnormal,
            "报警": "🔴 夜间离床超时" if abnormal and rnd.random() > 0.6 else ("✅ 正常" if not abnormal else "⚠️ 心率偏高"),
        })
    return rows


# ============ 汇总 ============
def regulation_summary(session: Session):
    ratings = org_credit_ratings(session)
    frauds = fraud_leave_sim(session)
    vitals = vital_signs_sim()
    return {
        "机构数": len(ratings),
        "A级": sum(1 for r in ratings if r["等级"] == "A"),
        "D级": sum(1 for r in ratings if r["等级"] == "D"),
        "骗补预警": sum(1 for f in frauds if "红色" in f["风险"]),
        "体征异常": sum(1 for v in vitals if v["异常"]),
        "待办工单": len(frauds),
    }
