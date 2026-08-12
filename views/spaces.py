# -*- coding: utf-8 -*-
"""空间档案：楼栋-楼层-房间/公共区域四级架构"""
import streamlit as st
from sqlalchemy.orm import Session

from auth import current_user, require_role
from models import Space, User, AuditLog
from services.mask import staff_mask
from views.common import kpi_card, user_select


def render(session: Session):
    require_role(1)  # 空间档案管理：一级专属
    user = current_user(session)
    st.header("空间档案管理")
    st.caption("楼栋 - 楼层 - 房间 / 公共区域 四级架构，每个空间绑定责任人、巡检标准，隐患自动绑定空间可追溯")

    spaces = session.query(Space).order_by(Space.building, Space.floor, Space.room).all()
    c1, c2, c3 = st.columns(3)
    c1.metric("空间总数", len(spaces))
    c2.metric("房间数", sum(1 for s in spaces if s.space_type == "房间"))
    c3.metric("公共区域", sum(1 for s in spaces if s.space_type == "公共区域"))

    with st.expander("➕ 新增空间", expanded=False):
        with st.form("add_space"):
            b1, b2, b3 = st.columns(3)
            building = b1.text_input("楼栋", "一号楼")
            floor = b2.text_input("楼层", "1层")
            room = b3.text_input("房间/区域名", "104室")
            s1, s2 = st.columns(2)
            space_type = s1.selectbox("类型", ["房间", "公共区域"])
            managers = session.query(User).filter(User.role_level == 3, User.active == True).all()
            manager = user_select(session, managers, key="space_mgr", label="绑定责任人") if managers else None
            standard = st.text_area("巡检标准", "每日巡检：用电/消防/地面")
            if st.form_submit_button("保存"):
                if any(x.full_name == f"{building}-{floor}-{room}" for x in spaces):
                    st.error("该空间已存在")
                else:
                    sp = Space(building=building, floor=floor, room=room,
                               space_type=space_type,
                               manager_id=manager.id if manager else None,
                               check_standard=standard)
                    session.add(sp)
                    session.add(AuditLog(user_id=user.id, username=user.username,
                                         action="新增空间", target=sp.full_name,
                                         detail=f"类型：{space_type}"))
                    session.commit()
                    st.success(f"空间 {sp.full_name} 创建成功")
                    st.rerun()

    st.divider()
    st.subheader("空间清单")
    for sp in spaces:
        mgr = session.query(User).get(sp.manager_id) if sp.manager_id else None
        with st.expander(f"{sp.full_name}（{sp.space_type}）"):
            c1, c2 = st.columns([2, 1])
            c1.markdown(f"**责任人**：{staff_mask(mgr.name) if mgr else '未绑定'}（{mgr.dept_name if mgr else '—'}）")
            c1.markdown(f"**巡检标准**：{sp.check_standard or '—'}")
            c2.markdown(f"**创建时间**：{sp.created_at.strftime('%Y-%m-%d') if sp.created_at else '—'}")
            new_mgr = user_select(session, managers, key=f"mgr_{sp.id}", label="更换责任人") if managers else None
            if st.button(f"绑定/更新责任人 #{sp.id}", key=f"btn_{sp.id}") and new_mgr:
                sp.manager_id = new_mgr.id
                session.add(AuditLog(user_id=user.id, username=user.username,
                                     action="更新空间", target=sp.full_name,
                                     detail=f"责任人改为 {staff_mask(new_mgr.name)}"))
                session.commit()
                st.success("已更新")
                st.rerun()
