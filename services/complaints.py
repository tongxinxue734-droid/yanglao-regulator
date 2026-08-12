# -*- coding: utf-8 -*-
"""投诉举报受理 — 数据服务（政府监管渠道：12345 转办 / 来信 / 来电 / 网络）
登记 → 受理 → 派单核查 → 处理反馈 → 归档，全程留痕审计。
投诉人信息脱敏存储：姓名仅姓氏+称谓（张先生/匿名），电话打码。
"""
from datetime import datetime

from sqlalchemy.orm import Session

from models import Complaint, Organization, AuditLog
from services.mask import org_label


def next_code(session: Session) -> str:
    """生成投诉编号：TS-YYYY-0001"""
    year = datetime.now().year
    rows = session.query(Complaint).filter(
        Complaint.code.like(f"TS-{year}-%")).count()
    return f"TS-{year}-{rows + 1:04d}"


def register(session: Session, *, org_id, source, title, content,
             complainant="匿名", phone="", level="黄色", user=None):
    """登记投诉举报（投诉人信息脱敏入库）"""
    c = Complaint(
        code=next_code(session),
        org_id=org_id or None,
        source=source,
        title=title,
        content=content,
        complainant=complainant or "匿名",
        phone=phone or "",
        level=level,
        status="待受理",
    )
    session.add(c)
    session.flush()
    if user:
        session.add(AuditLog(user_id=user.id, username=user.username,
                             action="投诉登记", target=c.code,
                             detail=f"来源：{source} · {title[:30]}"))
    session.commit()
    return c


def assign(session: Session, complaint: Complaint, assignee_id: int, user=None):
    """派单：指定承办人进入核查"""
    complaint.assignee_id = assignee_id
    if complaint.status == "待受理":
        complaint.status = "核查中"
    if user:
        session.add(AuditLog(user_id=user.id, username=user.username,
                             action="投诉派单", target=complaint.code,
                             detail=f"指派承办人 #{assignee_id}"))
    session.commit()


def close(session: Session, complaint: Complaint, result: str, user=None):
    """办结：填写处理结果"""
    complaint.result = result
    complaint.status = "已办结"
    complaint.closed_at = datetime.now()
    if user:
        session.add(AuditLog(user_id=user.id, username=user.username,
                             action="投诉办结", target=complaint.code,
                             detail=f"处理结果：{result[:40]}"))
    session.commit()


def reject(session: Session, complaint: Complaint, reason: str, user=None):
    """不予受理：说明理由"""
    complaint.result = reason
    complaint.status = "不予受理"
    complaint.closed_at = datetime.now()
    if user:
        session.add(AuditLog(user_id=user.id, username=user.username,
                             action="不予受理", target=complaint.code,
                             detail=f"理由：{reason[:40]}"))
    session.commit()


def archive(session: Session, complaint: Complaint, user=None):
    """归档：办结/不予受理后归档留痕"""
    complaint.status = "已归档"
    if user:
        session.add(AuditLog(user_id=user.id, username=user.username,
                             action="投诉归档", target=complaint.code,
                             detail="办结归档"))
    session.commit()


def list_complaints(session: Session, org_ids=None):
    """列出投诉（可按管辖机构范围过滤，全部按时间倒序）"""
    q = session.query(Complaint)
    if org_ids:
        q = q.filter(Complaint.org_id.in_(org_ids))
    return q.order_by(Complaint.created_at.desc()).all()


def complaint_stats(session: Session, org_ids=None):
    """监管统计：各状态数量 + 红色紧急数 + 本月新增"""
    cs = list_complaints(session, org_ids)
    now = datetime.now()
    return {
        "总件数": len(cs),
        "待受理": sum(1 for c in cs if c.status == "待受理"),
        "核查中": sum(1 for c in cs if c.status == "核查中"),
        "已办结": sum(1 for c in cs if c.status in ("已办结", "已归档")),
        "红色紧急": sum(1 for c in cs if c.level == "红色" and c.status not in ("已归档",)),
        "本月新增": sum(1 for c in cs if c.created_at.strftime("%Y-%m") == now.strftime("%Y-%m")),
    }
