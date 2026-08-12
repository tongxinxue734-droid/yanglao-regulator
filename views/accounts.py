# -*- coding: utf-8 -*-
"""账号管理：一级管全部，二级仅管自己的三级下级；扩展角色预留"""
import streamlit as st
from sqlalchemy.orm import Session

from auth import current_user, require_role, can_manage_users, visible_user_ids
from models import User
from services.accounts import create_user, update_user, delete_user
from services.mask import staff_mask
from views.common import badge


def render(session: Session):
    user = current_user(session)
    require_role(2)
    st.header("账号管理")
    st.caption("三级权限体系：一级管理全部账号；二级仅能创建/管理自己管辖的三级账号；扩展角色（维修员/访客/监管人员）预留")

    # ---- 新建 ----
    with st.expander("➕ 新建账号", expanded=False):
        with st.form("new_user"):
            c1, c2 = st.columns(2)
            username = c1.text_input("登录账号")
            name = c2.text_input("姓名")
            c3, c4 = st.columns(2)
            role_level = c3.selectbox("角色级别", [1, 2, 3], format_func=lambda x: {1: "一级·超级管理员", 2: "二级·部门管理员", 3: "三级·一线执行"}[x])
            dept = c4.text_input("部门/管辖范围")
            c5, c6 = st.columns(2)
            password = c5.text_input("初始密码", type="password")
            phone = c6.text_input("手机号")
            if user.role_level == 2:
                st.caption("（二级管理员只能创建三级账号，且自动归属自己管辖）")
            if st.form_submit_button("创建"):
                parent_id = user.id if role_level == 3 and user.role_level == 2 else None
                ok, msg = create_user(session, user, username=username.strip(),
                                      password=password or "123456", name=name.strip(),
                                      role_level=role_level, dept_name=dept.strip(),
                                      parent_id=parent_id, phone=phone.strip())
                if ok:
                    st.success(msg)
                    st.rerun()
                else:
                    st.error(msg)

    st.divider()

    # ---- 账号列表 ----
    st.subheader("账号列表")
    vis_ids = visible_user_ids(session, user)
    if user.role_level == 1:
        users = session.query(User).filter(User.active == True).all()
    else:
        users = [u for u in session.query(User).filter(User.active == True).all() if u.id in vis_ids]
    for u in sorted(users, key=lambda x: x.role_level):
        with st.container(border=True):
            c1, c2, c3, c4 = st.columns([2, 2, 2, 3])
            lvl_name = {1: "一级·超级管理员", 2: "二级·部门管理员", 3: "三级·一线执行"}[u.role_level]
            c1.markdown(f"**{staff_mask(u.name)}**（{u.username}）")
            c2.markdown(badge(lvl_name, "#1f6feb"), unsafe_allow_html=True)
            c3.markdown(f"{u.dept_name}　{u.phone}")
            c4.caption(f"上级ID：{u.parent_id or '—'}")
            if can_manage_users(session, user, u) and u.id != user.id:
                with st.expander(f"管理 {u.username}"):
                    with st.form(f"mgmt_{u.id}"):
                        npw = st.text_input("重置密码（留空不改）", type="password", key=f"npw_{u.id}")
                        ndept = st.text_input("部门", value=u.dept_name, key=f"ndept_{u.id}")
                        nphone = st.text_input("手机号", value=u.phone, key=f"nphone_{u.id}")
                        c1, c2 = st.columns(2)
                        if c1.form_submit_button("保存修改"):
                            ok, msg = update_user(session, user, u.id,
                                                  password=npw or None, dept_name=ndept, phone=nphone)
                            st.success(msg) if ok else st.error(msg)
                            st.rerun()
                        if c2.form_submit_button("停用账号"):
                            ok, msg = delete_user(session, user, u.id)
                            st.success(msg) if ok else st.error(msg)
                            st.rerun()

    st.divider()
    # ---- 已停用账号（可重新启用，用户名可复用） ----
    st.subheader("已停用账号")
    if user.role_level == 1:
        inactive = session.query(User).filter(User.active == False).all()
    else:
        inactive = [u for u in session.query(User).filter(User.active == False).all() if u.id in vis_ids]
    if not inactive:
        st.caption("暂无停用账号")
    for u in inactive:
        with st.container(border=True):
            c1, c2, c3 = st.columns([3, 3, 2])
            c1.markdown(f"**{staff_mask(u.name)}**（{u.username}）")
            c2.caption(f"{u.dept_name} · 停用前级别：{u.role_level} 级")
            if can_manage_users(session, user, u):
                if c3.button(f"重新启用 {u.username}", key=f"reenable_{u.id}"):
                    ok, msg = update_user(session, user, u.id, active=True)
                    st.success(msg) if ok else st.error(msg)
                    st.rerun()
