# -*- coding: utf-8 -*-
"""登录认证与三级权限（页面级 + 行级双重控制）"""
import bcrypt
import streamlit as st
from sqlalchemy.orm import Session

from models import User


# ---------------------------------------------------------------
# 行级数据过滤：返回当前用户「可见用户 id 集合」
# 一级：全院；二级：自己 + 直属下级（同级完全隔离）；三级：仅本人
# ---------------------------------------------------------------
def visible_user_ids(session: Session, user: User):
    if user.role_level == 1:
        return [u.id for u in session.query(User).filter(User.active == True).all()]
    if user.role_level == 2:
        subs = [u.id for u in session.query(User).filter(
            User.parent_id == user.id, User.active == True).all()]
        return [user.id] + subs
    return [user.id]


# 可见隐患 id 集合（上报人或整改责任人在可见范围内）
def visible_hazard_filter(session: Session, user: User):
    ids = visible_user_ids(session, user)
    from models import Hazard
    return Hazard.reporter_id.in_(ids) | Hazard.assignee_id.in_(ids)


# 可见机构 id（政府监管视角：一级全辖区；二级/三级按管辖片区 org_ids）
def visible_org_ids(session: Session, user: User):
    from models import Organization
    if user.role_level == 1:
        return [o.id for o in session.query(Organization).filter(Organization.active == True).all()]
    return list(user.org_ids or [])


def can_manage_users(session: Session, user: User, target: User) -> bool:
    """账号管理权限：一级管全部；二级只能管自己下级的三级账号"""
    if user.role_level == 1:
        return True
    if user.role_level == 2:
        return target.role_level == 3 and target.parent_id == user.id
    return False


# ---------------------------------------------------------------
# 登录与会话
# ---------------------------------------------------------------
def authenticate(session: Session, username: str, password: str):
    u = session.query(User).filter(User.username == username, User.active == True).first()
    if not u:
        return None
    try:
        ok = bcrypt.checkpw(password.encode("utf-8"), u.password_hash.encode("utf-8"))
    except Exception:
        ok = False
    return u if ok else None


def do_login(session: Session, username: str, password: str) -> bool:
    u = authenticate(session, username, password)
    if u:
        st.session_state["user_id"] = u.id
        st.session_state["username"] = u.username
        st.session_state["name"] = u.name
        st.session_state["role_level"] = u.role_level
        st.session_state["dept_name"] = u.dept_name
        from models import AuditLog
        session.add(AuditLog(user_id=u.id, username=u.username, action="登录",
                             target="系统", detail="用户登录系统"))
        session.commit()
        return True
    return False


def require_login():
    if "user_id" not in st.session_state:
        st.warning("请先登录")
        st.stop()


def current_user(session: Session) -> User:
    return session.query(User).get(st.session_state.get("user_id"))


def logout():
    for k in ["user_id", "username", "name", "role_level", "dept_name"]:
        st.session_state.pop(k, None)


ROLE_NAMES = {1: "一级 · 市级民政部门领导", 2: "二级 · 区县民政监管人员", 3: "三级 · 检查员"}


def role_name(level: int) -> str:
    return ROLE_NAMES.get(level, str(level))


def require_role(level: int):
    if st.session_state.get("role_level", 3) > level:
        st.error("权限不足：该操作需要更高级别账号")
        st.stop()
