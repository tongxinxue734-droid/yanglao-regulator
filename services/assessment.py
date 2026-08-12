# -*- coding: utf-8 -*-
"""老人能力评估备案 — 数据服务（政府监管）
依据 MZ/T 039《老年人能力评估规范》四维评估量表：
  生活自理 ADL (0-40) · 认知能力 (0-16) · 情绪行为 (0-8) · 视听觉 (0-8) = 总分 (0-72)
失能等级映射（总分越低失能越重）：
  >60 自理 · 41-60 轻度失能 · 21-40 中度失能 · <=20 重度失能
评估结果备案留痕，作为护理补贴发放与护患比校验的依据。
"""
from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from models import Elderly, AssessmentRecord, Organization, AuditLog

# 评估有效期（月）——民政部要求能力评估每 6 个月复评一次
VALID_MONTHS = 6

# 各维度满分
MAX_SCORES = {"adl": 40, "cognition": 16, "emotion": 8, "sensory": 8}


def calc_level(total: int) -> str:
    """总分 → 失能等级（MZ/T 039 映射）"""
    if total > 60:
        return "自理"
    if total >= 41:
        return "轻度失能"
    if total >= 21:
        return "中度失能"
    return "重度失能"


def calc_valid_until(assessed_on: str) -> str:
    """评估日期 + 6 个月 = 有效期至"""
    try:
        d = datetime.strptime(assessed_on, "%Y-%m-%d")
    except (ValueError, TypeError):
        d = datetime.now()
    return (d + timedelta(days=30 * VALID_MONTHS)).strftime("%Y-%m-%d")


def assess(session: Session, *, org_id: int, elder_id: int,
           adl: int, cognition: int, emotion: int, sensory: int,
           assessor: str, assessor_org: str, assessed_on: str = None, user=None):
    """录入评估备案：四维打分 → 总分 → 失能等级 → 留痕并回写老人档案"""
    total = adl + cognition + emotion + sensory
    level = calc_level(total)
    on = assessed_on or datetime.now().strftime("%Y-%m-%d")
    rec = AssessmentRecord(
        org_id=org_id, elder_id=elder_id,
        adl_score=adl, cognition_score=cognition,
        emotion_score=emotion, sensory_score=sensory,
        total_score=total, level=level,
        assessor=assessor, assessor_org=assessor_org,
        valid_until=calc_valid_until(on),
        created_by=user.id if user else None,
        created_at=datetime.now(),
    )
    session.add(rec)
    # 回写脱敏老人档案：能力等级 / 最近评估日期 / 评估有效性
    elder = session.query(Elderly).get(elder_id)
    if elder:
        elder.health_level = level
        elder.assessed_at = on
        elder.assessment_valid = True
    if user:
        session.add(AuditLog(user_id=user.id, username=user.username,
                             action="评估备案", target=f"Elder#{elder_id}",
                             detail=f"四维评估 {adl}+{cognition}+{emotion}+{sensory}={total} → {level}"))
    session.commit()
    return rec


def list_records(session: Session, org_ids=None, limit=200):
    """评估备案列表（可按机构范围过滤，按时间倒序）"""
    q = session.query(AssessmentRecord)
    if org_ids:
        q = q.filter(AssessmentRecord.org_id.in_(org_ids))
    rows = []
    elders = {e.id: e for e in session.query(Elderly).all()}
    orgs = {o.id: o for o in session.query(Organization).all()}
    for r in q.order_by(AssessmentRecord.created_at.desc()).limit(limit).all():
        e = elders.get(r.elder_id)
        o = orgs.get(r.org_id)
        rows.append({
            "id": r.id,
            "机构": f"{o.name}（{o.code}）" if o else "—",
            "老人": e.name if e else "—",
            "年龄": f"{e.age}岁" if e else "—",
            "生活自理": f"{r.adl_score}/40",
            "认知": f"{r.cognition_score}/16",
            "情绪行为": f"{r.emotion_score}/8",
            "视听觉": f"{r.sensory_score}/8",
            "总分": r.total_score,
            "等级": r.level,
            "评估机构": r.assessor_org,
            "评估员": r.assessor,
            "评估日期": r.created_at.strftime("%Y-%m-%d") if r.created_at else "—",
            "有效期至": r.valid_until,
        })
    return rows


def assessment_stats(session: Session, org_ids=None):
    """监管统计：备案总数 / 各级别人数 / 即将到期 / 超期未复评"""
    rows = list_records(session, org_ids, limit=10000)
    now = datetime.now().date()
    levels = {"自理": 0, "轻度失能": 0, "中度失能": 0, "重度失能": 0}
    expiring, expired = 0, 0
    for r in rows:
        levels[r["等级"]] = levels.get(r["等级"], 0) + 1
        try:
            d = datetime.strptime(r["有效期至"], "%Y-%m-%d").date()
            days = (d - now).days
            if days < 0:
                expired += 1
            elif days <= 30:
                expiring += 1
        except (ValueError, TypeError):
            pass
    return {
        "备案总数": len(rows),
        "自理": levels["自理"], "轻度失能": levels["轻度失能"],
        "中度失能": levels["中度失能"], "重度失能": levels["重度失能"],
        "即将到期": expiring, "超期未复评": expired,
    }
