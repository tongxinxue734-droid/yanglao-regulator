# -*- coding: utf-8 -*-
"""全局主题与 UI 组件库 — Real-Time Monitoring 精化版
设计依据：ui-ux-pro-max 设计系统（高对比藏青+蓝 / Fira Code 数字 / 状态灯动画 / 渐变卡片）
"""
import streamlit as st


def inject_theme():
    """注入全局 CSS：在基础浅色政务风格上增强质感（阴影体系/渐变/hover/动画/等宽数字）"""
    st.markdown("""
    <style>
    /* ================= 基础 ================= */
    /* 字体：优先使用系统自带的「微软雅黑」（清晰、本地渲染，不依赖外网字体 CDN）
       数字使用 Consolas 等宽字体，保证报表观感专业 */
    html, body, [class*="css"], .stApp, .stMarkdown, .stText, p, span, div, label {
        font-family: 'Microsoft YaHei', '微软雅黑', 'PingFang SC', 'Hiragino Sans GB',
                     'Noto Sans SC', 'WenQuanYi Micro Hei', sans-serif;
    }
    html, body, [class*="css"] {
        font-size: 16px;
        line-height: 1.6;
        color: #0F172A;
    }
    /* 标题统一放大 */
    h1 { font-size: 30px !important; font-weight: 700 !important; }
    h2 { font-size: 24px !important; font-weight: 700 !important; }
    h3 { font-size: 20px !important; font-weight: 700 !important; }
    /* 隐藏 Streamlit 顶部多余按钮（Deploy/主菜单/装饰），保留左上角「≡」汉堡按钮（手机端展开菜单用）
       注意：stExpandSidebarButton（汉堡）也在 stToolbar 内，不能整块隐藏 stToolbar */
    [data-testid="stToolbar"] [data-testid="stBaseButton-header"] { display: none; }
    [data-testid="stToolbar"] [data-testid="stMainMenuButton"] { display: none; }
    [data-testid="stDecoration"] { display: none; }
    header { background: transparent !important; }
    .block-container {
        padding-top: 1.6rem;
        padding-bottom: 2.5rem;
        max-width: 1500px;
    }
    .stApp {
        background: linear-gradient(180deg, #F8FAFC 0%, #F1F5F9 100%);
        background-attachment: fixed;
    }
    ::-webkit-scrollbar { width: 8px; height: 8px; }
    ::-webkit-scrollbar-track { background: transparent; }
    ::-webkit-scrollbar-thumb { background: #CBD5E1; border-radius: 4px; }
    ::-webkit-scrollbar-thumb:hover { background: #94A3B8; }

    /* 数据数字使用等宽字体，更专业 */
    .lg-num, [data-testid="stMetricValue"] {
        font-family: 'Consolas', 'Courier New', 'Fira Code', monospace !important;
        letter-spacing: -0.5px;
    }

    /* ================= 登录页 ================= */
    .login-wrapper { display:flex; justify-content:center; align-items:center; margin-top:8vh; margin-bottom:2rem; }
    .login-card {
        background: rgba(255,255,255,0.92);
        backdrop-filter: blur(14px); -webkit-backdrop-filter: blur(14px);
        border-radius: 22px; padding: 42px;
        box-shadow: 0 20px 60px rgba(15,23,42,0.12), inset 0 1px 0 rgba(255,255,255,0.9);
        border: 1px solid rgba(255,255,255,0.7);
        text-align: center;
        position: relative; overflow: hidden;
    }
    .login-card::before {
        content: ''; position: absolute; top: 0; left: 0; right: 0; height: 4px;
        background: linear-gradient(90deg, #0369A1, #3B82F6, #10B981);
    }
    .login-icon { font-size: 48px; margin-bottom: 10px; }
    .login-title { font-size: 26px; font-weight: 700; color: #0F172A; margin-bottom: 8px; letter-spacing: .5px; }
    .login-subtitle { font-size: 14px; color: #64748B; letter-spacing: 1px; }

    /* ================= 侧边栏（深色模式） ================= */
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #0B1220 0%, #111827 100%) !important;
        border-right: 1px solid #1E293B;
        min-width: 280px !important;
        max-width: 320px !important;
        box-shadow: 2px 0 30px rgba(0,0,0,0.25);
    }
    [data-testid="stSidebar"] .stButton > button {
        color: #94A3B8 !important;
        border-radius: 10px; border: none;
        padding: 0.65rem 1rem;
        text-align: left; justify-content: flex-start;
        font-weight: 500;
        font-size: 15px;
        background-color: transparent !important;
        transition: all 0.2s ease;
    }
    [data-testid="stSidebar"] .stButton > button:hover {
        background-color: #1E293B !important;
        color: #F1F5F9 !important;
        transform: translateX(2px);
    }
    [data-testid="stSidebar"] .stButton > button[kind="primary"] {
        background: linear-gradient(90deg, #1E3A8A, #2563EB) !important;
        color: #FFFFFF !important; font-weight: 600;
        box-shadow: inset 3px 0 0 #60A5FA, 0 4px 14px rgba(37,99,235,0.35);
    }
    [data-testid="stSidebar"] hr { border-color: #1E293B; }
    [data-testid="stSidebar"] .stMarkdown p, [data-testid="stSidebar"] .stMarkdown div {
        color: #CBD5E1;
    }
    .user-profile-card {
        background: linear-gradient(135deg, #1E3A8A 0%, #2563EB 55%, #0EA5E9 100%);
        color: white; padding: 20px; border-radius: 16px; margin-bottom: 24px;
        box-shadow: 0 12px 30px -6px rgba(37,99,235,0.55);
        position: relative; overflow: hidden;
    }
    .user-profile-card::after {
        content: ''; position: absolute; top: -30px; right: -30px;
        width: 110px; height: 110px; border-radius: 50%;
        background: radial-gradient(circle, rgba(255,255,255,0.18), transparent 70%);
    }
    .user-profile-card::before {
        content: ''; position: absolute; bottom: -40px; left: -20px;
        width: 90px; height: 90px; border-radius: 50%;
        background: radial-gradient(circle, rgba(16,185,129,0.25), transparent 70%);
    }
    .user-name { font-size: 20px; font-weight: 700; margin-bottom: 4px; position: relative; z-index: 1; }
    .user-role { font-size: 14px; opacity: 0.92; display: flex; align-items: center; gap: 6px; position: relative; z-index: 1; }

    /* 侧边栏菜单按钮 */
    div[data-testid="stSidebar"] .stButton > button {
        border-radius: 10px; border: none;
        padding: 0.65rem 1rem;
        text-align: left; justify-content: flex-start;
        font-weight: 500; color: #475569;
        font-size: 15px;
        background-color: transparent;
        transition: all 0.2s ease;
        position: relative;
    }
    div[data-testid="stSidebar"] .stButton > button:hover {
        background-color: #F1F5F9; color: #0F172A;
        transform: translateX(2px);
    }
    div[data-testid="stSidebar"] .stButton > button[kind="primary"] {
        background: linear-gradient(90deg, #EFF6FF 0%, #DBEAFE 100%);
        color: #1D4ED8; font-weight: 600;
        box-shadow: inset 3px 0 0 #2563EB;
    }

    /* ================= 按钮 ================= */
    .stButton > button, .stFormSubmitButton > button {
        border-radius: 10px; font-weight: 600;
        font-size: 15px;
        transition: all 0.25s ease;
        border: 1px solid #E2E8F0; color: #334155;
    }
    .stButton > button:hover, .stFormSubmitButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 8px 20px rgba(15,23,42,0.12);
        border-color: #3B82F6; color: #1D4ED8;
    }
    .stButton > button[kind="primary"], .stFormSubmitButton > button[kind="primary"] {
        background: linear-gradient(135deg, #2563EB, #1D4ED8);
        color: #fff; border: none;
        box-shadow: 0 6px 18px rgba(37,99,235,0.35);
    }
    .stButton > button[kind="primary"]:hover {
        background: linear-gradient(135deg, #1D4ED8, #1E40AF);
        box-shadow: 0 10px 26px rgba(37,99,235,0.45);
        color: #fff;
    }

    /* ================= 输入框/选择器 ================= */
    [data-testid="stTextInput"] input, [data-testid="stNumberInput"] input,
    [data-testid="stDateInput"] input, [data-testid="stTextArea"] textarea {
        border: 1.5px solid #E2E8F0; border-radius: 10px;
        font-size: 16px;
        transition: border-color .2s, box-shadow .2s;
        background: #fff;
    }
    [data-testid="stTextInput"] input:focus, [data-testid="stTextArea"] textarea:focus {
        border-color: #3B82F6;
        box-shadow: 0 0 0 3px rgba(59,130,246,0.15);
    }
    [data-testid="stSelectbox"] > div > div, [data-testid="stMultiselect"] > div > div {
        border: 1.5px solid #E2E8F0; border-radius: 10px; background: #fff;
        font-size: 16px;
    }
    [data-testid="stSelectbox"] span, [data-testid="stMultiselect"] span { font-size: 16px; }

    /* ================= Tabs ================= */
    .stTabs [data-baseweb="tab-list"] { gap: 6px; }
    .stTabs [data-baseweb="tab"] {
        border-radius: 8px 8px 0 0; padding: 9px 20px;
        color: #64748B; font-weight: 500; transition: all .2s;
        font-size: 16px;
    }
    .stTabs [aria-selected="true"] {
        color: #1D4ED8 !important; font-weight: 600;
        box-shadow: inset 0 -2px 0 #2563EB;
    }

    /* ================= 表格 ================= */
    [data-testid="stDataFrame"] {
        border-radius: 12px; overflow: hidden;
        border: 1px solid #E2E8F0;
        box-shadow: 0 4px 16px rgba(15,23,42,0.05);
        font-size: 15px;
    }
    [data-testid="stDataFrame"] thead th {
        background: linear-gradient(180deg, #F8FAFC, #F1F5F9) !important;
        color: #334155 !important; font-weight: 600 !important;
        font-size: 15px !important;
    }
    [data-testid="stDataFrame"] tbody td, [data-testid="stDataFrame"] tbody th {
        font-size: 15px !important;
    }
    /* 表格行高加大，更易读 */
    [data-testid="stDataFrame"] tbody tr { min-height: 38px !important; }

    /* ================= Expander / Form ================= */
    [data-testid="stExpander"] {
        border: 1px solid #E2E8F0; border-radius: 12px;
        background: #fff; box-shadow: 0 2px 10px rgba(15,23,42,0.04);
    }
    /* 侧边栏分组折叠（深色主题适配） */
    [data-testid="stSidebar"] [data-testid="stExpander"] {
        border: 1px solid #1E293B; background: transparent;
        border-radius: 10px; margin: 4px 0; box-shadow: none;
    }
    [data-testid="stSidebar"] [data-testid="stExpander"] summary {
        color: #CBD5E1; font-weight: 600; font-size: 14px;
        padding: 6px 10px; border-radius: 8px;
    }
    [data-testid="stSidebar"] [data-testid="stExpander"] summary:hover {
        background-color: #1E293B; color: #F1F5F9;
    }
    [data-testid="stSidebar"] [data-testid="stExpander"] [data-testid="stExpanderDetails"] {
        padding: 4px 6px;
    }
    [data-testid="stForm"] {
        border: 1px solid #E2E8F0; border-radius: 14px;
        background: rgba(255,255,255,0.7); padding: 1rem;
    }

    /* ================= 指标卡（原生 Metric） ================= */
    [data-testid="stMetric"] {
        background: #fff; border: 1px solid #E2E8F0; border-radius: 14px;
        padding: 0.9rem 1rem;
        box-shadow: 0 4px 16px rgba(15,23,42,0.05);
        transition: transform .2s, box-shadow .2s;
        position: relative; overflow: hidden;
    }
    [data-testid="stMetric"]:hover { transform: translateY(-3px); box-shadow: 0 10px 28px rgba(15,23,42,0.10); }
    [data-testid="stMetric"]::after {
        content: ''; position: absolute; top: 0; left: 0; right: 0; height: 3px;
        background: linear-gradient(90deg, #2563EB, #7C3AED, #10B981);
    }
    [data-testid="stMetricLabel"] { color: #64748B; font-size: 14px; }
    [data-testid="stMetricValue"] {
        color: #1E3A8A; font-size: 30px; font-weight: 700;
    }
    [data-testid="stMetricDelta"] { font-size: 13px; }

    /* ================= 图表/卡片入场动画 ================= */
    @keyframes lg-rise {
        from { opacity: 0; transform: translateY(16px); }
        to { opacity: 1; transform: translateY(0); }
    }
    [data-testid="stPlotlyChart"] {
        animation: lg-rise 0.55s cubic-bezier(.2,.7,.3,1) both;
    }
    [data-testid="stMetric"], [data-testid="stDataFrame"] {
        animation: lg-rise 0.45s ease both;
    }
    .lg-card-hover { animation: lg-rise 0.45s ease both; transition: transform .2s, box-shadow .2s; }

    /* ================= 状态灯动画（告警脉冲） ================= */
    @keyframes lg-pulse {
        0% { box-shadow: 0 0 0 0 rgba(239,68,68,0.4); }
        70% { box-shadow: 0 0 0 8px rgba(239,68,68,0); }
        100% { box-shadow: 0 0 0 0 rgba(239,68,68,0); }
    }
    .lg-dot { display:inline-block; width:8px; height:8px; border-radius:50%; margin-right:5px; }
    .lg-dot-red { background:#EF4444; animation: lg-pulse 1.8s infinite; }
    .lg-dot-green { background:#10B981; }
    .lg-dot-amber { background:#F59E0B; }
    .lg-dot-blue { background:#3B82F6; }

    /* 卡片通用 hover */
    .lg-card-hover { transition: transform .2s, box-shadow .2s; }
    .lg-card-hover:hover { transform: translateY(-3px); box-shadow: 0 10px 28px rgba(15,23,42,0.10); }

    @media (prefers-reduced-motion: reduce) {
        *, *::before, *::after { animation-duration: 0.01ms !important; transition-duration: 0.01ms !important; }
    }
    </style>
    """, unsafe_allow_html=True)


def app_header(title, subtitle):
    """主页面统一页眉"""
    st.markdown(f"""
        <div style="border-bottom: 2px solid #E2E8F0; padding-bottom: 16px; margin-bottom: 24px; margin-top: -10px;
                    position: relative;">
            <h2 style="margin: 0; color: #0F172A; font-weight: 700;">{title}</h2>
            <span style="color: #64748B; font-size: 16px; display: block; margin-top: 4px;">{subtitle}</span>
            <div style="position:absolute; left:0; bottom:-2px; width:96px; height:2px;
                        background: linear-gradient(90deg, #2563EB, #10B981);"></div>
        </div>
    """, unsafe_allow_html=True)


ICONS = {}


def icon(name, size=16, color=None):
    """图标占位符，兼容老代码"""
    return "🔹"


def badge(text, color="#1E293B", bg_color="#F1F5F9"):
    """通用状态徽章（带状态点）"""
    dot = '<span class="lg-dot" style="background:' + color + '"></span>'
    return (f'<span style="background-color:{bg_color};color:{color};padding:4px 12px;'
            f'border-radius:12px;font-size:13px;font-weight:600;display:inline-flex;'
            f'align-items:center;gap:4px;">{dot}{text}</span>')


def level_badge(level):
    """隐患等级专属徽章（红橙黄蓝）"""
    colors = {
        "红色": ("#991B1B", "#FEE2E2"),
        "橙色": ("#9A3412", "#FFEDD5"),
        "黄色": ("#854D0E", "#FEF08A"),
        "蓝色": ("#1E40AF", "#DBEAFE")
    }
    c, bg = colors.get(level, ("#1E293B", "#F1F5F9"))
    return badge(level, c, bg)


def status_badge(status):
    """工单状态专属徽章"""
    colors = {
        "待整改": ("#991B1B", "#FEE2E2"),
        "整改中": ("#854D0E", "#FEF08A"),
        "待复查": ("#1E40AF", "#DBEAFE"),
        "打回重改": ("#9A3412", "#FFEDD5"),
        "已闭环": ("#166534", "#DCFCE7"),
        "已归档": ("#475569", "#F1F5F9")
    }
    c, bg = colors.get(status, ("#1E293B", "#F1F5F9"))
    return badge(status, c, bg)


def metric_card(title, value, subtitle="", delta=None, icon_str="📊"):
    """KPI 统计卡片（精化版：渐变数字 + 顶部色条 + hover 抬升）
    注意：HTML 块内不能有空行，否则 markdown 会截断 HTML 块导致裸标签显示"""
    delta_html = ""
    if delta:
        color = "#10B981" if str(delta).startswith("-") else "#EF4444"
        delta_html = f'<div style="color:{color};font-size:14px;margin-top:4px;font-weight:600;">{delta}</div>'

    st.markdown(f"""
    <div class="lg-card-hover" style="background:white;padding:22px 24px;border-radius:16px;
        box-shadow:0 4px 16px rgba(15,23,42,0.05);border:1px solid #E2E8F0;height:100%;
        position:relative;overflow:hidden;">
        <div style="position:absolute;top:0;left:0;right:0;height:3px;
            background:linear-gradient(90deg,#2563EB,#7C3AED,#10B981);"></div>
        <div style="color:#64748B;font-size:15px;font-weight:600;display:flex;justify-content:space-between;align-items:center;">
            {title} <span style="font-size:22px;">{icon_str}</span>
        </div>
        <div class="lg-num" style="font-size:34px;font-weight:700;margin-top:12px;margin-bottom:4px;
            color:#1E3A8A;">
            {value}
        </div>
        <div style="color:#94A3B8;font-size:13px;">{subtitle}</div>{delta_html}</div>
    """, unsafe_allow_html=True)


# ════════════════════════════════════════════════════════════
# 兼容组件（供老页面使用）
# ════════════════════════════════════════════════════════════

C = {
    "bg": "#F8FAFC", "text": "#0F172A", "text_dim": "#64748B",
    "primary": "#3B82F6", "accent": "#10B981", "danger": "#EF4444",
    "warn": "#F59E0B", "info": "#0EA5E9", "purple": "#8B5CF6",
    "glass": "rgba(255,255,255,0.9)", "glass_border": "#E2E8F0",
    "font": "'Microsoft YaHei', '微软雅黑', sans-serif", "font_mono": "'Consolas', monospace",
}


def glass_card(html: str):
    """玻璃卡片容器（增强阴影）"""
    return st.markdown(
        f'<div style="background:#fff;border:1px solid #E2E8F0;border-radius:16px;'
        f'padding:1rem 1.1rem;box-shadow:0 4px 16px rgba(15,23,42,0.05);margin:0.4rem 0;">{html}</div>',
        unsafe_allow_html=True)


def section_title(icon_name: str, text: str, sub: str = ""):
    """分区标题（渐变条）"""
    sub_html = f'<div style="color:#94A3B8;font-size:14px;margin-top:2px;">{sub}</div>' if sub else ""
    return st.markdown(
        f'<div style="margin:1.1rem 0 0.4rem;">'
        f'<span style="font-size:1.15rem;font-weight:700;color:#0F172A;'
        f'padding-left:10px;border-left:4px solid #2563EB;">{text}</span>{sub_html}</div>',
        unsafe_allow_html=True)


def page_header(icon_name: str, title: str, subtitle: str = ""):
    """页面头部（与 app_header 同风格）"""
    sub = f'<span style="color:#64748B;font-size:16px;display:block;margin-top:4px;">{subtitle}</span>' if subtitle else ""
    return st.markdown(
        f'<div style="border-bottom:2px solid #E2E8F0;padding-bottom:16px;margin-bottom:20px;position:relative;">'
        f'<h2 style="margin:0;color:#0F172A;font-weight:700;">{title}</h2>{sub}'
        f'<div style="position:absolute;left:0;bottom:-2px;width:96px;height:2px;'
        f'background:linear-gradient(90deg,#2563EB,#10B981);"></div></div>',
        unsafe_allow_html=True)


def page_footer(text: str = None):
    """页脚"""
    import config as _cfg
    return st.markdown(
        f'<div style="margin-top:2rem;padding-top:0.8rem;border-top:1px solid #E2E8F0;'
        f'color:#94A3B8;font-size:14px;text-align:center;">'
        f'{text or f"{_cfg.ORG_NAME} · {_cfg.APP_NAME}"}</div>',
        unsafe_allow_html=True)
