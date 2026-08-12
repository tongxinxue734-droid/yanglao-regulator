# -*- coding: utf-8 -*-
"""巡检任务：管理员下发计划（日/周/月）+ 自动推送待办 + 到期提醒"""
from datetime import datetime, timedelta

import streamlit as st
from sqlalchemy.orm import Session

from auth import current_user, visible_user_ids
from models import InspectionTask, TaskInstance, AuditLog, Notification, User, Space
from services.mask import staff_mask
from views.common import space_select, user_select


def render(session: Session):
    user = current_user(session)
    st.header("巡检任务管理")
    st.caption("管理员制定巡检计划（每日/每周/每月），自动推送到对应人员账号，到期提醒")

    # ---- 一级/二级：下发任务 ----
    if user.role_level <= 2:
        with st.expander("➕ 下发巡检计划（点击展开填写）", expanded=True):
            with st.form("new_task"):
                title = st.text_input("任务名称", "一号楼每日安全巡检")
                c1, c2 = st.columns(2)
                freq = c1.selectbox("频次", ["每日", "每周", "每月"])
                scope_users = [u for u in session.query(User).filter(User.active == True).all()
                               if u.id in visible_user_ids(session, user) and u.role_level == 3]
                if not scope_users:
                    st.warning("当前权限范围内暂无三级人员可指派为执行人，"
                               "请先在「账号管理」中创建三级账号（一级账号可先到账号管理查看）。")
                assignee = user_select(session, scope_users, key="task_asg", label="执行人（三级人员）")
                c3, c4 = st.columns(2)
                start = c3.date_input("开始日期", value=datetime.now().date())
                end = c4.date_input("结束日期", value=datetime.now().date() + timedelta(days=30))
                scope = st.multiselect("巡检范围（空间）",
                                       [f"{sp.full_name}（{sp.space_type}）" for sp in
                                        session.query(Space).order_by(Space.building).all()],
                                       key="task_spaces")
                if st.form_submit_button("保存计划"):
                    if not assignee:
                        st.error("请选择执行人")
                    elif not scope:
                        st.error("请选择巡检范围")
                    else:
                        sp_map = {f"{sp.full_name}（{sp.space_type}）": sp.id for sp in session.query(Space).all()}
                        t = InspectionTask(title=title, freq=freq, assignee_id=assignee.id,
                                           space_ids=[sp_map[s] for s in scope],
                                           start_date=start.strftime("%Y-%m-%d"),
                                           end_date=end.strftime("%Y-%m-%d"),
                                           created_by=user.id)
                        session.add(t)
                        session.flush()
                        # 按频次生成首批实例（下 3 期）
                        step = {"每日": 1, "每周": 7, "每月": 30}[freq]
                        for k in range(3):
                            due = start + timedelta(days=k * step)
                            session.add(TaskInstance(task_id=t.id, assignee_id=assignee.id,
                                                     title=title, due_date=due.strftime("%Y-%m-%d")))
                        session.add(Notification(user_id=assignee.id, ntype="待办",
                                                 content=f"新巡检任务「{title}」（{freq}），请按时完成。",
                                                 link="巡检任务"))
                        session.add(AuditLog(user_id=user.id, username=user.username,
                                             action="下发巡检计划", target=title,
                                             detail=f"{freq}，执行人 {staff_mask(assignee.name)}"))
                        session.commit()
                        st.success("巡检计划已下发，任务实例已生成并推送")
                        st.rerun()

    st.divider()

    # ---- 我的待办（三级执行人） ----
    st.subheader("我的巡检待办")
    visible_ids = visible_user_ids(session, user)
    instances = session.query(TaskInstance).filter(TaskInstance.assignee_id.in_(visible_ids)) \
        .order_by(TaskInstance.due_date.desc()).all()
    if not instances:
        st.caption("暂无巡检任务")
    for ti in instances:
        overdue = ti.status == "待执行" and ti.due_date < datetime.now().strftime("%Y-%m-%d")
        icon = "✅" if ti.status == "已完成" else ("⚠️" if overdue else "⬜")
        c1, c2, c3 = st.columns([3, 1, 2])
        c1.markdown(f"{icon} **{ti.title}**（{ti.due_date}）")
        c2.markdown(ti.status)
        if ti.status == "待执行" and ti.assignee_id == user.id:
            if c3.button("标记完成", key=f"done_{ti.id}"):
                ti.status = "已完成"
                ti.completed_at = datetime.now()
                session.add(AuditLog(user_id=user.id, username=user.username,
                                     action="完成巡检任务", target=ti.title, detail=ti.due_date))
                session.commit()
                st.success("任务已完成")
                st.rerun()
        else:
            c3.caption("")

    st.divider()
    st.subheader("巡检计划列表")
    # 行级过滤：一级全部 / 二级仅管辖范围 / 三级仅自己
    plan_ids = visible_user_ids(session, user)
    plans = session.query(InspectionTask).filter(
        InspectionTask.assignee_id.in_(plan_ids)).order_by(InspectionTask.id.desc()).all()
    if not plans:
        st.caption("权限范围内暂无巡检计划")
    for t in plans:
        asg = session.query(User).get(t.assignee_id)
        with st.expander(f"{t.title}（{t.freq}）· 执行人 {staff_mask(asg.name) if asg else '—'}"):
            st.markdown(f"**周期**：{t.start_date} ~ {t.end_date}")
            st.markdown(f"**范围**：{len(t.space_ids or [])} 个空间")
            if user.role_level == 1:
                if st.button(f"停用计划 #{t.id}", key=f"stop_t_{t.id}"):
                    t.active = False
                    session.commit()
                    st.rerun()
