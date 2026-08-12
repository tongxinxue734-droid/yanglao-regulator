# -*- coding: utf-8 -*-
"""韧性康养 · 极端天气与演练归档 — 模块三
演练归档库（消防/防噎食/防跌倒）· 超半年自动扣分亮红灯 · 季节预案
"""
from datetime import datetime
import pandas as pd
import streamlit as st
from sqlalchemy.orm import Session

from auth import require_role
from services.drills import drill_records, drill_summary
from views.theme import app_header, metric_card, section_title


def _season_plan():
    """按当前月份返回应触发的季节预案"""
    m = datetime.now().month
    if 6 <= m <= 9:
        return "☀️ 高温防中暑预案", "夏季高温，系统已自动触发「防中暑巡检专项」：上午 10 点后减少户外活动、饮水提醒、空调巡检。", "夏季"
    if 11 <= m <= 2:
        return "❄️ 供暖与防煤气中毒预案", "冬季低温，系统已自动触发「供暖故障/防煤气中毒专项巡检」：锅炉房安全、一氧化碳浓度、老人保暖检查。", "冬季"
    return "🍂 换季健康预案", "春秋换季，系统已自动触发「呼吸道感染防控专项」：通风消毒、体温监测、流感疫苗接种提醒。", "换季"


def render(session: Session):
    require_role(1)
    app_header("韧性康养 · 应急管理", "季节预案自动触发 · 演练归档库（超半年未演练自动扣分 · E3 指标）")

    total, overdue = drill_summary(session)
    c1, c2, c3 = st.columns(3)
    with c1:
        metric_card("归档演练", total, "全部演练记录")
    with c2:
        metric_card("逾期未演练", overdue, "超 180 天未做", icon_str="🔴")
    with c3:
        metric_card("演练合规率", f"{100 - round(overdue / max(total, 1) * 100)}%", "按机构统计")

    # ============ 季节预案 ============
    title, desc, season = _season_plan()
    section_title("🌦️", "极端天气应急管理（西安气候）", f"当前触发：{season}预案")
    st.markdown(f"""
    <div style="background:linear-gradient(135deg,#EFF6FF,#DBEAFE);border:1px solid #BFDBFE;
        border-radius:12px;padding:16px 20px;margin-bottom:18px;">
        <b style="color:#1E40AF;font-size:16px;">{title}</b><br>
        <span style="color:#1E40AF;font-size:13px;">{desc}</span>
    </div>""", unsafe_allow_html=True)

    # ============ 演练归档库 ============
    st.markdown("<hr style='border-top:1px dashed #CBD5E1;margin:24px 0;'>", unsafe_allow_html=True)
    section_title("📋", "演练归档库", "消防 / 防噎食 / 防跌倒 · 强制记录现场照片 · 超半年未做自动扣分（E3）")
    recs = drill_records(session)
    df = pd.DataFrame(recs)
    overdue_df = df[df["逾期"]]
    if not overdue_df.empty:
        st.markdown("""
        <div style="background:linear-gradient(135deg,#FEF2F2,#FEE2E2);border-left:6px solid #DC2626;
            border-radius:10px;padding:12px 16px;color:#991B1B;margin-bottom:10px;">
            🔴 <b>以下机构演练已超半年未做，系统已自动扣分并在大屏亮红灯：</b>
        </div>""", unsafe_allow_html=True)
    st.dataframe(df[["机构", "演练项目", "对应指标", "最近演练", "距今", "状态", "现场照片", "参与人数"]],
                 use_container_width=True, hide_index=True)

    # 新增演练登记（演示入口）
    st.markdown("<hr style='border-top:1px dashed #CBD5E1;margin:24px 0;'>", unsafe_allow_html=True)
    with st.expander("➕ 新增演练登记"):
        c1, c2, c3 = st.columns(3)
        with c1:
            org = st.selectbox("机构", sorted(df["机构"].unique().tolist()))
        with c2:
            dtype = st.selectbox("演练项目", [d[0] for d in [
                ("消防疏散演练", "E3", ""), ("防噎食应急演练", "E3", ""), ("防跌倒应急预案演练", "E3", "")]])
        with c3:
            date = st.date_input("演练日期", value=datetime.now().date())
        people = st.number_input("参与人数", min_value=5, max_value=200, value=30, step=5)
        note = st.text_area("演练情况说明", placeholder="例如：全员参加，2 分 30 秒完成疏散，应急灯正常……")
        if st.button("归档演练记录", type="primary"):
            st.success(f"✅ 已归档「{org} · {dtype} · {date}」演练记录（演示模式，仅本次会话可见）")
