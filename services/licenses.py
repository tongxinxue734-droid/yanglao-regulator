# -*- coding: utf-8 -*-
"""机构证照备案 — 数据服务（民政监管：营业执照 / 备案凭证 / 消防验收 / 食品经营许可）
到期前 30 天 → 「临期」黄色预警；已过期 → 「过期」红色预警。
"""
from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from models import License, Organization
from services.mask import org_label

# 证照类型（民政监管关注的核心证照）
LIC_TYPES = ["营业执照", "养老机构备案凭证", "消防验收合格证明", "食品经营许可证"]

# 提前预警天数
WARN_DAYS = 30


def calc_status(expire_at: str) -> str:
    """按有效期计算证照状态：有效 / 临期 / 过期"""
    try:
        d = datetime.strptime(expire_at, "%Y-%m-%d").date()
    except (ValueError, TypeError):
        return "有效"
    today = datetime.now().date()
    if d < today:
        return "过期"
    if d <= today + timedelta(days=WARN_DAYS):
        return "临期"
    return "有效"


def list_licenses(session: Session, org_ids=None):
    """列出证照（可按管辖机构过滤），附动态状态"""
    q = session.query(License)
    if org_ids:
        q = q.filter(License.org_id.in_(org_ids))
    rows = []
    for lic in q.order_by(License.org_id, License.id).all():
        status = calc_status(lic.expire_at)
        rows.append({
            "id": lic.id,
            "机构": org_label(lic.org.name, lic.org.code),
            "org_id": lic.org_id,
            "证照类型": lic.lic_type,
            "证照号": lic.lic_no,
            "发证日期": lic.issued_at,
            "有效期至": lic.expire_at,
            "状态": status,
        })
    return rows


def license_stats(session: Session, org_ids=None):
    """监管统计：有效 / 临期 / 过期 证照数量 + 有临期证照的机构数"""
    rows = list_licenses(session, org_ids)
    stat = {"有效": 0, "临期": 0, "过期": 0}
    orgs_warn = set()
    for r in rows:
        stat[r["状态"]] += 1
        if r["状态"] in ("临期", "过期"):
            orgs_warn.add(r["org_id"])
    return {
        "证照总数": len(rows),
        "有效": stat["有效"],
        "临期": stat["临期"],
        "过期": stat["过期"],
        "预警机构数": len(orgs_warn),
    }


def org_license_matrix(session: Session, org_ids=None):
    """机构 × 证照类型 矩阵（用于总览表）"""
    rows = list_licenses(session, org_ids)
    matrix = {}
    for r in rows:
        key = r["机构"]
        matrix.setdefault(key, {})[r["证照类型"]] = r["状态"]
    return matrix
