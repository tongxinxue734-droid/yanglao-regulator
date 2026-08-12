# -*- coding: utf-8 -*-
"""公共 UI 组件（委托 Liquid Glass 设计系统）"""
import streamlit as st

import config
from models import User, Space
from views.theme import badge as _theme_badge, level_badge as _level_badge, \
    status_badge as _status_badge, metric_card as _metric_card, icon, glass_card

LEVEL_COLORS = {"红色": "#EF4444", "橙色": "#F59E0B", "黄色": "#EAB308", "蓝色": "#38BDF8"}
STATUS_CN = config.HAZARD_STATUS
STATUS_REV = config.HAZARD_STATUS_REV


def badge(text: str, color: str = "#1f6feb") -> str:
    return _theme_badge(text, color)


def level_badge(level: str) -> str:
    return _level_badge(level)


def status_badge(status: str) -> str:
    return _status_badge(status)


def kpi_card(label: str, value, color: str = "#1f6feb", help_text: str = ""):
    """旧接口兼容：委托白色指标卡（浅色主题）"""
    return _metric_card(label, value, help_text)


def space_select(session, key="space", label="选择空间") -> Space:
    spaces = session.query(Space).order_by(Space.building, Space.floor, Space.room).all()
    if not spaces:
        st.warning("请先在一级账号「空间档案」中建立空间")
        return None
    opts = {f"{sp.full_name}（{sp.space_type}）": sp for sp in spaces}
    sel = st.selectbox(label, list(opts.keys()), key=key)
    return opts[sel]


def user_select(session, users, key="user", label="选择人员") -> User:
    if not users:
        return None
    from services.mask import staff_mask
    opts = {f"{staff_mask(u.name)}（{u.dept_name}）": u for u in users}
    sel = st.selectbox(label, list(opts.keys()), key=key)
    return opts[sel]


def photo_preview(paths):
    """渲染照片缩略预览"""
    import os
    for p in (paths or []):
        full = os.path.join(config.DATA_DIR, p)
        if os.path.exists(full):
            try:
                st.image(full, width=160)
            except Exception:
                pass


def fmt_dt(dt) -> str:
    return dt.strftime("%Y-%m-%d %H:%M") if dt else "—"


def fmt_date(dt) -> str:
    return dt.strftime("%Y-%m-%d") if dt else "—"
