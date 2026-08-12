# -*- coding: utf-8 -*-
"""操作日志审计：所有账号操作全留痕"""
import pandas as pd
import streamlit as st
from sqlalchemy.orm import Session

from auth import current_user, require_role
from models import AuditLog


def render(session: Session):
    user = current_user(session)
    require_role(1)  # 审计日志一级专属
    st.header("操作日志审计")
    st.caption("所有账号操作全程留痕（登录/上报/派单/整改/复查/归档/导出…），符合民政监管要求，可追溯")

    rows = session.query(AuditLog).order_by(AuditLog.id.desc()).limit(500).all()
    df = pd.DataFrame([{
        "时间": a.created_at.strftime("%Y-%m-%d %H:%M:%S") if a.created_at else "",
        "账号": a.username, "操作": a.action, "对象": a.target, "详情": a.detail,
    } for a in rows])

    c1, c2 = st.columns([1, 3])
    actions = ["全部"] + sorted({a.action for a in rows})
    act = c1.selectbox("按操作筛选", actions)
    if act != "全部":
        df = df[df["操作"] == act]
    c2.metric("展示记录数", len(df))

    st.dataframe(df, use_container_width=True, hide_index=True)
    st.download_button("⬇️ 导出审计日志 CSV", df.to_csv(index=False).encode("utf-8-sig"),
                       "audit_logs.csv", "text/csv")
