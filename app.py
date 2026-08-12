# -*- coding: utf-8 -*-
"""养老机构安全巡检与合规考核系统 - Streamlit 入口"""
import streamlit as st
import config
import db
import seed
from auth import current_user, logout, role_name
from models import Notification
from services.mask import staff_mask

# ---------------- 初始化 ----------------
db.init_db()
_session = db.get_session()
try:
    seed.seed_all(_session, with_demo=True)
finally:
    _session.close()

# 设置页面为宽屏模式并配置标题
st.set_page_config(page_title=config.APP_NAME, page_icon="🏥", layout="wide")

# ---------------- 登录门控 ----------------
if "user_id" not in st.session_state:
    from views import login

    _login_session = db.get_session()
    try:
        login.render(_login_session)
    finally:
        _login_session.close()
    st.stop()

# ---------------- 注入高级 CSS 主题 ----------------
from views.theme import inject_theme, app_header

inject_theme()

# ---------------- 侧边栏：用户信息 + 角色化菜单 ----------------
session = db.get_session()
user = current_user(session)

# 账号验证防线
if user is None or not user.active:
    logout()
    session.close()
    st.warning("账号已被停用，请重新登录")
    st.rerun()

# 定义各级角色菜单 (图标 Emoji, 页面标识, 菜单名称) —— 政府监管人员视角
# 一级=市级民政部门领导 · 二级=区县民政监管人员 · 三级=检查员
# 菜单按功能分组：(组名, [(图标, 页面标识, 菜单名), ...]) —— 侧边栏分组展示，免逐个翻找
GROUPED_MENUS = {
    1: [  # 一级·市级民政部门领导
        ("📊 监管总览", [
            ("📊", "dashboard", "辖区安全总览"),
            ("🛰️", "regulation", "智慧监管中台"),
            ("🏙️", "digital_twin", "3D 可视化"),
        ]),
        ("🏛️ 机构管理", [
            ("🏛️", "organizations", "机构档案"),
            ("📄", "licenses", "机构证照"),
            ("📋", "assessment", "评估排班"),
            ("📮", "complaints", "投诉举报"),
        ]),
        ("🔍 巡查检查", [
            ("📷", "report_hazard", "隐患上报"),
            ("📋", "hazard_list", "问题台账"),
            ("🎯", "compliance", "检查评分"),
        ]),
        ("🏆 考核评价", [
            ("🏆", "credit_board", "信誉红黑榜"),
            ("🏆", "leaderboard", "评分排行"),
            ("📁", "report_center", "报告中心"),
        ]),
        ("🥗 专项监管", [
            ("🥗", "foodsafety", "阳光明厨"),
            ("🧯", "drills", "演练归档"),
        ]),
        ("🤖 智能辅助", [
            ("🤖", "assistant", "AI 智能助理"),
            ("📈", "analytics", "分析中心"),
        ]),
        ("⚙️ 系统管理", [
            ("📚", "standard_lib", "检查标准库"),
            ("👥", "accounts", "账号管理"),
            ("🔔", "messages", "消息中心"),
            ("📜", "audit", "审计日志"),
        ]),
    ],
    2: [  # 二级·区县民政监管人员（管辖片区机构）
        ("🏛️ 片区管理", [
            ("🏛️", "organizations", "管辖机构"),
            ("📄", "licenses", "机构证照"),
            ("📮", "complaints", "投诉举报"),
        ]),
        ("🔍 巡查检查", [
            ("📷", "report_hazard", "隐患上报"),
            ("📋", "hazard_list", "问题台账"),
            ("🎯", "compliance", "检查评分"),
        ]),
        ("📊 数据与考核", [
            ("📈", "analytics", "片区数据分析"),
            ("🏆", "leaderboard", "片区评分排行"),
            ("📁", "report_center", "报告中心"),
        ]),
        ("📮 综合服务", [
            ("🔔", "messages", "消息中心"),
        ]),
    ],
    3: [  # 三级·检查员（执行机构现场检查）
        ("🔍 现场作业", [
            ("📷", "report_hazard", "隐患上报"),
            ("📋", "hazard_list", "我的问题记录"),
            ("🎯", "compliance", "执行检查评分"),
        ]),
        ("📊 个人中心", [
            ("🏆", "leaderboard", "我的检查记录"),
            ("🔔", "messages", "消息中心"),
        ]),
    ],
}

# 兼容旧接口：拍平成 {role: [(icon,key,label),...]}
ROLE_MENUS = {r: [item for grp in groups for item in grp[1]] for r, groups in GROUPED_MENUS.items()}

with st.sidebar:
    # 渐变色精美个人名片
    st.markdown(
        f'''
        <div class="user-profile-card">
            <div class="user-name">Hi, {staff_mask(st.session_state.get("name", "用户"))}</div>
            <div class="user-role">
                <span>🛡️</span> {role_name(user.role_level)} | {st.session_state.get("dept_name", "无部门")}
            </div>
        </div>
        ''', unsafe_allow_html=True)

    st.markdown(
        "<div style='font-size:13px; font-weight:bold; color:#64748B; margin:6px 5px 8px; letter-spacing:1px;'>系统菜单</div>",
        unsafe_allow_html=True)

    groups = GROUPED_MENUS.get(user.role_level, GROUPED_MENUS[3])
    flat_menu = [item for grp in groups for item in grp[1]]
    st.session_state.setdefault("page", flat_menu[0][1])
    current_page = st.session_state["page"]

    # 渲染分组菜单：每组用可折叠容器（expander），默认只展开当前所在分组，其余收起
    for group_name, items in groups:
        group_has_active = any(key == current_page for _, key, _ in items)
        with st.expander(group_name, expanded=group_has_active):
            for icon_emoji, key, label in items:
                active = (current_page == key)
                btn_label = f"{icon_emoji}  {label}"
                if st.button(btn_label, key=f"nav_{key}", use_container_width=True,
                             type="primary" if active else "secondary"):
                    st.session_state["page"] = key
                    st.rerun()

    st.divider()

    # 消息提醒区域
    unread = session.query(Notification).filter(
        Notification.user_id == user.id,
        Notification.is_read == False).count()
    if unread > 0:
        st.markdown(
            f"<div style='color: #EF4444; font-size: 15px; margin-bottom: 10px;'>🔔 您有 <b>{unread}</b> 条未读待办！</div>",
            unsafe_allow_html=True)
    else:
        st.markdown("<div style='color: #10B981; font-size: 15px; margin-bottom: 10px;'>✨ 当前暂无未读消息</div>",
                    unsafe_allow_html=True)

    if st.button("🚪 退出登录", use_container_width=True, key="nav_logout"):
        logout()
        st.rerun()

# ---------------- 顶栏全局标头 ----------------
app_header(config.APP_NAME, "AI 驱动的智能化安全巡检与闭环管理平台")

# ---------------- 页面路由分发 ----------------
page = st.session_state["page"]
try:
    if page == "dashboard":
        from views import dashboard

        dashboard.render(session)
    elif page == "regulation":
        from views import regulation

        regulation.render(session)
    elif page == "digital_twin":
        from views import digital_twin

        digital_twin.render(session)
    elif page == "foodsafety":
        from views import foodsafety

        foodsafety.render(session)
    elif page == "drills":
        from views import drills

        drills.render(session)
    elif page == "assessment":
        from views import assessment

        assessment.render(session)
    elif page == "credit_board":
        from views import credit_board

        credit_board.render(session)
    elif page == "assistant":
        from views import assistant

        assistant.render(session)
    elif page == "analytics":
        from views import analytics

        analytics.render(session)
    elif page == "report_hazard":
        from views import report_hazard

        report_hazard.render(session)
    elif page == "hazard_list":
        from views import hazard_list

        hazard_list.render(session)
    elif page == "inspection_tasks":
        from views import inspection_tasks

        inspection_tasks.render(session)
    elif page == "compliance":
        from views import compliance

        compliance.render(session)
    elif page == "organizations":
        from views import organizations

        organizations.render(session)
    elif page == "licenses":
        from views import licenses

        licenses.render(session)
    elif page == "complaints":
        from views import complaints

        complaints.render(session)
    elif page == "report_center":
        from views import report_center

        report_center.render(session)
    elif page == "leaderboard":
        from views import leaderboard

        leaderboard.render(session)
    elif page == "spaces":
        from views import spaces

        spaces.render(session)
    elif page == "standard_lib":
        from views import standard_lib

        standard_lib.render(session)
    elif page == "accounts":
        from views import accounts

        accounts.render(session)
    elif page == "messages":
        from views import messages

        messages.render(session)
    elif page == "audit":
        from views import audit

        audit.render(session)
    else:
        st.info("该模块正在开发中...")
finally:
    session.close()