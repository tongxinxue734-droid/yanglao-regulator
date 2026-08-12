# -*- coding: utf-8 -*-
"""评分计算：合规考核得分、处罚档次、排行榜、智能预警"""
from datetime import datetime, timedelta

import pandas as pd
from sqlalchemy.orm import Session

import config
from models import (Hazard, ComplianceScore, ViolationRecord, User, Space,
                    TaskInstance, Organization)
from services.mask import staff_mask


def period_str(dt: datetime = None) -> str:
    return (dt or datetime.now()).strftime("%Y-%m")


# ---------------------------------------------------------------
# 处罚档次：按累计扣分落入对应档次（>= 下界）
# ---------------------------------------------------------------
def punishment_tier(total_deduct: int) -> dict:
    tier = None
    for t in config.PUNISHMENT_TIERS:
        if total_deduct >= t["deduct"]:
            tier = t
    return tier or {"deduct": 0, "grade": "合规", "penalty": "无"}


# ---------------------------------------------------------------
# 机构合规得分：100 - 当月违规扣分合计（扣完为止）
# ---------------------------------------------------------------
def compliance_score(period: str, session: Session, org_id: int = None) -> dict:
    """机构合规得分：100 - 该机构当月违规扣分合计（扣完为止）
    org_id=None 时汇总全部机构（全辖区视角）。"""
    q = session.query(ViolationRecord).filter(ViolationRecord.period == period)
    if org_id is not None:
        q = q.filter(ViolationRecord.org_id == org_id)
    rows = q.all()
    deducted = sum(v.deducted for v in rows)
    base = 100
    if org_id is not None:
        org = session.query(Organization).get(org_id)
        base = org.base_score if org and org.base_score else 100
    score = max(0, base - deducted)
    return {"period": period, "deducted": deducted, "score": score,
            "violations": len(rows),
            "tier": punishment_tier(deducted)}


def hazard_metrics(session: Session, start=None, end=None) -> dict:
    """隐患统计指标：总数/已闭环/整改率/逾期数/平均闭环天数"""
    q = session.query(Hazard)
    if start:
        q = q.filter(Hazard.created_at >= start)
    if end:
        q = q.filter(Hazard.created_at <= end)
    rows = q.all()
    total = len(rows)
    closed = sum(1 for h in rows if h.status in ("closed", "archived"))
    overdued = sum(1 for h in rows if h.overdued)
    rect_rate = (closed / total * 100) if total else 100.0
    days = [(h.closed_at - h.created_at).days for h in rows
            if h.closed_at and h.created_at]
    avg_days = round(sum(days) / len(days), 1) if days else 0
    return {"total": total, "closed": closed, "rect_rate": round(rect_rate, 1),
            "overdued": overdued, "avg_days": avg_days}


# ---------------------------------------------------------------
# 排行榜（人员/班组/整改榜，支持多周期）
# ---------------------------------------------------------------
def leaderboard(session: Session, period: str = "月", scope_user_ids=None,
                role_level: int = 1, user_id: int = None) -> dict:
    """period: 日/周/月/季/年；scope_user_ids: 行级过滤后的可见人员。"""
    rows = session.query(Hazard).all()
    now = datetime.now()
    today = now.date()

    def in_period(dt):
        if not dt:
            return False
        d = dt.date()
        if period == "日":
            return d == today
        if period == "周":
            monday = today - timedelta(days=today.weekday())
            return monday <= d <= today
        if period == "月":
            return d.strftime("%Y-%m") == now.strftime("%Y-%m")
        if period == "季":
            return (d.year == now.year
                    and (d.month - 1) // 3 == (now.month - 1) // 3)
        if period == "年":
            return d.year == now.year
        return True

    rows = [h for h in rows if in_period(h.created_at)]
    if scope_user_ids is not None:
        rows = [h for h in rows
                if h.reporter_id in scope_user_ids or h.assignee_id in scope_user_ids]

    # 人员榜：隐患发现量 / 整改及时率 / 巡检完成率 -> 综合得分
    from collections import defaultdict
    found = defaultdict(int)
    rect_ok = defaultdict(int)
    rect_total = defaultdict(int)
    overdued_by = defaultdict(int)
    for h in rows:
        found[h.reporter_id] += 1
        if h.assignee_id:
            rect_total[h.assignee_id] += 1
            if h.status in ("closed", "archived") and not h.overdued:
                rect_ok[h.assignee_id] += 1
            if h.overdued:
                overdued_by[h.assignee_id] += 1

    # 巡检任务完成率
    insts = session.query(TaskInstance).all()
    task_done = defaultdict(int)
    task_total = defaultdict(int)
    for ti in insts:
        if ti.assignee_id and in_period(ti.created_at):
            task_total[ti.assignee_id] += 1
            if ti.status == "已完成":
                task_done[ti.assignee_id] += 1

    people = []
    uid_set = set(scope_user_ids) if scope_user_ids is not None else None
    users = session.query(User).filter(User.active == True).all()
    for u in users:
        if uid_set is not None and u.id not in uid_set:
            continue
        f = found.get(u.id, 0)
        rt = rect_total.get(u.id, 0)
        timely = (rect_ok.get(u.id, 0) / rt * 100) if rt else 100.0
        tt = task_total.get(u.id, 0)
        tdone = (task_done.get(u.id, 0) / tt * 100) if tt else 100.0
        score = round(f * 40 + timely * 0.3 + tdone * 0.3, 1)
        people.append({"user_id": u.id, "姓名": staff_mask(u.name), "部门": u.dept_name,
                       "级别": u.role_level, "隐患发现量": f,
                       "整改及时率": round(timely, 1), "巡检完成率": round(tdone, 1),
                       "综合得分": score})
    people.sort(key=lambda x: x["综合得分"], reverse=True)

    # 班组/楼层榜：区域综合得分 + 闭环率
    groups = defaultdict(lambda: {"total": 0, "closed": 0, "deduct": 0})
    for h in rows:
        key = h.space.building if h.space else "未知区域"
        groups[key]["total"] += 1
        if h.status in ("closed", "archived"):
            groups[key]["closed"] += 1
        groups[key]["deduct"] += h.deducted or 0
    teams = []
    for k, v in groups.items():
        closed_rate = (v["closed"] / v["total"] * 100) if v["total"] else 100.0
        base = 100 - min(v["deduct"], 100)
        teams.append({"区域": k, "隐患数": v["total"], "闭环率": round(closed_rate, 1),
                      "区域扣分": v["deduct"], "区域得分": round(base * 0.6 + closed_rate * 0.4, 1)})
    teams.sort(key=lambda x: x["区域得分"], reverse=True)

    # 整改榜：整改速度 + 复查通过率
    from models import Review
    reviews = session.query(Review).all()
    rev_ok = defaultdict(int)
    rev_total = defaultdict(int)
    for rv in reviews:
        if rv.reviewer_id:
            pass
        h = session.query(Hazard).get(rv.hazard_id)
        if h and h.assignee_id and in_period(h.created_at):
            rev_total[h.assignee_id] += 1
            if rv.result == "通过":
                rev_ok[h.assignee_id] += 1
    rectify = []
    for u in users:
        if uid_set is not None and u.id not in uid_set:
            continue
        rt = rect_total.get(u.id, 0)
        if rt == 0:
            continue
        pass_rate = (rev_ok.get(u.id, 0) / rev_total.get(u.id, 1) * 100) if rev_total.get(u.id) else 100.0
        rectify.append({"user_id": u.id, "姓名": staff_mask(u.name), "整改数": rt,
                        "逾期数": overdued_by.get(u.id, 0),
                        "复查通过率": round(pass_rate, 1),
                        "整改得分": round((100 - overdued_by.get(u.id, 0) / rt * 100) * 0.5 + pass_rate * 0.5, 1)})
    rectify.sort(key=lambda x: x["整改得分"], reverse=True)

    return {"people": people, "teams": teams, "rectify": rectify}


# ---------------------------------------------------------------
# 智能预警
# ---------------------------------------------------------------
def smart_alerts(session: Session) -> list:
    """返回预警列表：区域高频 / 逾期率超标 / 得分偏低"""
    alerts = []
    now = datetime.now()
    cur = now.strftime("%Y-%m")
    # 1. 区域同类隐患月度 >= 3
    from collections import Counter
    rows = [h for h in session.query(Hazard).all()
            if h.created_at and h.created_at.strftime("%Y-%m") == cur]
    c = Counter((h.space.building if h.space else "未知", h.category) for h in rows)
    for (region, cat), n in c.items():
        if n >= config.ALERT_RULES["region_high_risk"]["threshold"]:
            alerts.append({
                "type": "区域同类隐患高频", "level": "高风险",
                "content": f"{region} 本月「{cat}」类隐患出现 {n} 次（阈值 3 次/月）",
                "rule": config.ALERT_RULES["region_high_risk"]["desc"]})
    # 2. 人员整改逾期率 > 30%
    from collections import defaultdict
    total = defaultdict(int)
    od = defaultdict(int)
    for h in rows:
        if h.assignee_id:
            total[h.assignee_id] += 1
            if h.overdued:
                od[h.assignee_id] += 1
    users = {u.id: u for u in session.query(User).all()}
    for uid, n in total.items():
        if n >= 3 and od[uid] / n > config.ALERT_RULES["overdue_rate"]["threshold"]:
            u = users.get(uid)
            alerts.append({
                "type": "整改逾期率超标", "level": "关注",
                "content": f"{staff_mask(u.name) if u else uid} 整改逾期率 {od[uid]/n*100:.0f}%（阈值 30%），触发上级关注",
                "rule": config.ALERT_RULES["overdue_rate"]["desc"]})
    # 3. 月度综合得分 < 80
    cs = compliance_score(cur, session)
    if cs["score"] < config.ALERT_RULES["score_low"]["threshold"]:
        alerts.append({
            "type": "月度综合得分偏低", "level": "提醒",
            "content": f"本月综合得分 {cs['score']} 分（阈值 80 分），自动生成整改提醒",
            "rule": config.ALERT_RULES["score_low"]["desc"]})
    return alerts


def to_df(lst: list) -> pd.DataFrame:
    return pd.DataFrame(lst) if lst else pd.DataFrame()
