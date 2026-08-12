# -*- coding: utf-8 -*-
"""消息中心：待办任务/整改提醒/逾期预警统一归集"""
import streamlit as st
from sqlalchemy.orm import Session

from auth import current_user
from models import Notification


def render(session: Session):
    user = current_user(session)
    st.header("消息中心")
    st.caption("待办任务、整改提醒、逾期预警统一归集，支持站内提醒 + 邮件/企业微信推送（可配置 webhook）")

    msgs = session.query(Notification).filter(Notification.user_id == user.id) \
        .order_by(Notification.created_at.desc()).all()
    unread = sum(1 for m in msgs if not m.is_read)

    c1, c2 = st.columns([1, 3])
    c1.metric("未读消息", unread)
    if c2.button("全部标为已读") and msgs:
        for m in msgs:
            m.is_read = True
        session.commit()
        st.rerun()

    if not msgs:
        st.caption("暂无消息")
    for m in msgs:
        color = {"待办": "#0984e3", "整改提醒": "#e17055", "逾期预警": "#d63031", "系统": "#636e72"}.get(m.ntype, "#636e72")
        icon = {"待办": "📌", "整改提醒": "⏰", "逾期预警": "🚨", "系统": "ℹ️"}.get(m.ntype, "ℹ️")
        with st.container(border=True):
            c1, c2, c3 = st.columns([5, 1, 1])
            c1.markdown(f"{icon} **[{m.ntype}]** {m.content}")
            c2.markdown(m.created_at.strftime("%m-%d %H:%M") if m.created_at else "")
            if m.is_read:
                c3.caption("已读")
            else:
                if c3.button("标已读", key=f"read_{m.id}"):
                    m.is_read = True
                    session.commit()
                    st.rerun()
