# -*- coding: utf-8 -*-
"""账号管理服务：创建/停用/重置密码，带三级权限约束"""
import bcrypt
from sqlalchemy.orm import Session

from models import User, AuditLog
from auth import can_manage_users


def hash_pw(pw: str) -> str:
    return bcrypt.hashpw(pw.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def create_user(session: Session, operator: User, *, username, password, name,
                role_level, dept_name="", parent_id=None, phone="") -> tuple:
    """返回 (ok, msg)。权限：一级可建任意角色；二级只能建自己的三级下级。
    若存在已停用的同名账号，则自动恢复并更新为新信息（软删除不占用用户名）。"""
    if operator.role_level not in (1, 2):
        return False, "权限不足：只有一级/二级管理员可以创建账号"
    if operator.role_level == 2 and role_level != 3:
        return False, "二级管理员只能创建三级一线账号"
    parent = session.query(User).get(parent_id) if parent_id else None
    if operator.role_level == 2 and (parent is None or parent.id != operator.id):
        return False, "二级管理员创建的三级账号必须归属自己管辖"
    if role_level == 1:
        parent = None

    existing = session.query(User).filter(User.username == username).first()
    if existing and existing.active:
        return False, f"用户名 {username} 已存在"
    if existing and not existing.active:
        # 复用停用账号：重新激活并更新为新账号信息
        existing.active = True
        existing.password_hash = hash_pw(password)
        existing.name = name
        existing.role_level = role_level
        existing.dept_name = dept_name
        existing.parent_id = parent.id if parent else None
        existing.phone = phone
        session.flush()
        session.add(AuditLog(user_id=operator.id, username=operator.username,
                             action="恢复账号", target=username,
                             detail=f"原停用账号重新启用为 {role_level} 级 {name}"))
        session.commit()
        return True, f"账号 {username} 已恢复启用（原同名账号曾停用）"

    u = User(username=username, password_hash=hash_pw(password), name=name,
             role_level=role_level, dept_name=dept_name,
             parent_id=parent.id if parent else None, phone=phone)
    session.add(u)
    session.flush()
    session.add(AuditLog(user_id=operator.id, username=operator.username,
                         action="创建账号", target=username,
                         detail=f"新建 {role_level} 级账号 {name}"))
    session.commit()
    return True, f"账号 {username} 创建成功"


def update_user(session: Session, operator: User, target_id: int, **fields) -> tuple:
    """重置密码/停用启用/调整部门。只能操作自己有权限管理的账号。"""
    target = session.query(User).get(target_id)
    if not target:
        return False, "账号不存在"
    if not can_manage_users(session, operator, target):
        return False, "权限不足：只能管理自己管辖范围内的账号"
    if fields.get("password"):
        target.password_hash = hash_pw(fields["password"])
    if "dept_name" in fields:
        target.dept_name = fields["dept_name"]
    if "phone" in fields:
        target.phone = fields["phone"]
    if "active" in fields:
        target.active = bool(fields["active"])
    session.add(AuditLog(user_id=operator.id, username=operator.username,
                         action="修改账号", target=target.username,
                         detail=",".join(k for k in fields if fields[k] and k != "password")))
    session.commit()
    return True, f"账号 {target.username} 已更新"


def delete_user(session: Session, operator: User, target_id: int) -> tuple:
    target = session.query(User).get(target_id)
    if not target:
        return False, "账号不存在"
    if not can_manage_users(session, operator, target):
        return False, "权限不足"
    if target.id == operator.id:
        return False, "不能删除自己"
    # 软删除：停用而非物理删除，保留历史数据引用
    target.active = False
    session.add(AuditLog(user_id=operator.id, username=operator.username,
                         action="停用账号", target=target.username, detail="软删除"))
    session.commit()
    return True, f"账号 {target.username} 已停用"
