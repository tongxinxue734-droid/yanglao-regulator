# -*- coding: utf-8 -*-
"""登录界面 — 极简浅色风格
与内部页面统一浅色配色，清晰可读
"""
import streamlit as st
import time

from auth import do_login
import config


def render(session):
    st.markdown("""
    <style>
    .stApp { background-color: #F9FAFB !important; }
    header { display: none !important; }
    .block-container {
        max-width: 440px !important; padding: 0 1rem !important;
        margin: 0 auto !important; padding-top: 12vh !important;
    }
    .login-header { text-align: center; margin-bottom: 28px; }
    .login-logo {
        width: 46px; height: 46px;
        background-color: #2563EB; border-radius: 12px;
        margin: 0 auto 18px auto;
        display: flex; justify-content: center; align-items: center;
        color: white; font-size: 22px; font-weight: bold;
        box-shadow: 0 4px 12px rgba(37,99,235,0.2);
    }
    .login-title { font-size: 24px; font-weight: 700; color: #111827; margin: 0 0 6px; letter-spacing: -0.3px; }
    .login-sub { font-size: 15px; color: #6B7280; margin: 0; }
    [data-testid="stForm"] {
        border: 1px solid #E5E7EB !important; border-radius: 12px !important;
        background: #FFFFFF !important; padding: 24px !important;
        box-shadow: 0 1px 3px rgba(0,0,0,0.02) !important;
    }
    .stTextInput label p { font-size: 15px !important; color: #374151 !important; font-weight: 500 !important; }
    .stTextInput input {
        border: 1px solid #D1D5DB !important; border-radius: 8px !important;
        padding: 11px 14px !important; font-size: 16px !important;
        background-color: #FFFFFF !important; color: #111827 !important;
        box-shadow: 0 1px 2px rgba(0,0,0,0.02) inset !important; transition: all 0.2s !important;
    }
    .stTextInput input:focus { border-color: #2563EB !important; box-shadow: 0 0 0 3px rgba(37,99,235,0.1) !important; }
    [data-testid="stForm"] button[kind="formSubmit"] {
        width: 50% !important; margin: 16px auto 0 auto !important; display: block !important;
        background-color: #111827 !important; color: white !important; border: none !important;
        border-radius: 8px !important; padding: 11px 24px !important;
        font-size: 16px !important; font-weight: 500 !important; transition: background-color 0.2s !important;
    }
    [data-testid="stForm"] button[kind="formSubmit"]:hover { background-color: #374151 !important; }
    .demo-box {
        margin-top: 24px; padding: 16px;
        border: 1px solid #E5E7EB; border-radius: 10px;
        background-color: transparent; font-size: 14px; color: #6B7280; line-height: 1.8;
    }
    .demo-box code { background: #F3F4F6; color: #2563EB; padding: 2px 6px; border-radius: 4px; }
    .copyright { text-align: center; margin-top: 32px; font-size: 14px; color: #9CA3AF; }
    .pwa-hint {
        text-align: center; margin-top: 14px; padding: 10px;
        background: #EFF6FF; border: 1px solid #BFDBFE; border-radius: 8px;
        font-size: 13px; color: #1E40AF;
    }
    </style>
    """, unsafe_allow_html=True)

    # 顶部 Header
    st.markdown(f"""
        <div class="login-header">
            <div class="login-logo">✦</div>
            <h1 class="login-title">{config.APP_NAME}</h1>
            <p class="login-sub">安全巡检 · 整改闭环 · 合规考核 · 智慧监管</p>
        </div>
    """, unsafe_allow_html=True)

    # 登录表单
    with st.form("login_form", clear_on_submit=False):
        username = st.text_input("账号", placeholder="请输入您的监管账号")
        password = st.text_input("密码", type="password", placeholder="请输入密码")

        _l, _c, _r = st.columns([2, 1.5, 2])
        with _c:
            submit = st.form_submit_button("登 录", use_container_width=True)

        if submit:
            if not username or not password:
                st.error("⚠️ 账号和密码不能为空")
            elif do_login(session, username, password):
                st.success("✅ 登录成功")
                time.sleep(0.4)
                st.rerun()
            else:
                st.error("❌ 账号或密码错误")

    # 底部信息
    st.markdown("""
        <div class="demo-box">
            演示账号：<br>
            <code>admin / admin123</code>（市民政局领导）<br>
            <code>li</code> / <code>wang</code>（区县组长）— <code>123456</code><br>
            <code>zhao</code> / <code>qian</code> / <code>sun</code>（检查员）— <code>123456</code>
        </div>
        <div class="copyright">© 2026 养老机构智慧监管平台 · 政务数据安全合规</div>
        <div class="pwa-hint">📱 手机上打开？添加到桌面体验更佳：Safari「分享→添加到主屏幕」｜Chrome「菜单→添加到主屏幕」</div>
    """, unsafe_allow_html=True)
