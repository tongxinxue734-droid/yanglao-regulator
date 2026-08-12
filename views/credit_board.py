# -*- coding: utf-8 -*-
"""员工合规信誉分 · 红黑榜 — 游戏化绩效
主动上报加分 · 事故/逾期扣分 · 变「被动防查」为「主动排雷」
"""
import pandas as pd
import streamlit as st
from sqlalchemy.orm import Session

from auth import require_role
from services.credit_score import employee_credit, credit_summary
from views.theme import app_header, metric_card, section_title


def render(session: Session):
    require_role(1)
    app_header("员工合规信誉分 · 红黑榜", "主动上报有效隐患加分 · 事故/整改逾期扣分 · 游戏化正向激励")

    rows, red, black = credit_summary(session)
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        metric_card("参与员工", len(rows), "组长 + 检查员")
    with c2:
        metric_card("红榜", red, "信誉分 ≥100", icon_str="🏆")
    with c3:
        metric_card("黄榜", sum(1 for r in rows if r["榜单"] == "黄榜"), "90-99", icon_str="⭐")
    with c4:
        metric_card("黑榜", black, "信誉分 <90", icon_str="⚫")

    section_title("🏆", "渐变红黑榜", "由被动防查 → 主动排雷")

    # 红黑榜卡片
    cols = st.columns(min(3, len(rows)))
    for i, r in enumerate(rows):
        with cols[i % len(cols)]:
            if r["榜单"] == "红榜":
                bg, border, fg = "linear-gradient(135deg,#FFF7ED,#FFEDD5)", "#FED7AA", "#9A3412"
                icon = "🏆"
            elif r["榜单"] == "黑榜":
                bg, border, fg = "linear-gradient(135deg,#F8FAFC,#E2E8F0)", "#CBD5E1", "#334155"
                icon = "⚫"
            else:
                bg, border, fg = "linear-gradient(135deg,#FEFCE8,#FEF9C3)", "#FDE68A", "#854D0E"
                icon = "⭐"
            score = r["信誉分"]
            pct = min(100, max(0, (score - 60) / 60 * 100))
            st.markdown(f"""
            <div style="background:{bg};border:1px solid {border};border-radius:12px;
                padding:14px 16px;margin-bottom:10px;">
                <div style="font-size:15px;font-weight:700;color:{fg};">{icon} {r['姓名']}</div>
                <div style="font-size:12px;color:{fg};opacity:.85;">{r['角色']}</div>
                <div style="margin:8px 0 6px;height:8px;background:#E5E7EB;border-radius:4px;">
                    <div style="height:8px;width:{pct}%;background:linear-gradient(90deg,#34D399,#F59E0B,#EF4444);border-radius:4px;"></div>
                </div>
                <div style="font-size:20px;font-weight:800;color:{fg};">{score} 分</div>
                <div style="font-size:11px;color:{fg};opacity:.8;margin-top:4px;">
                    上报 {r['上报隐患']} · 闭环 {r['整改闭环']} · 逾期 {r['逾期记录']}
                </div>
            </div>
            """, unsafe_allow_html=True)

    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

    # 规则说明
    st.markdown("""
    <div style="border:1px dashed #CBD5E1;border-radius:10px;padding:14px 18px;background:#FAFBFC;margin-top:14px;">
        <b>📜 信誉分规则</b><br>
        <span style="font-size:13px;color:#475569;">
        • 基础分 100<br>
        • 主动上报有效隐患 <b style="color:#059669;">+5</b> · 整改闭环 <b style="color:#059669;">+2</b><br>
        • 整改逾期 <b style="color:#DC2626;">−5</b> · 发生责任事故 <b style="color:#DC2626;">−10</b><br>
        • 红榜（≥100）：年度评优优先 · 黑榜（<90）：培训提醒
        </span>
    </div>
    """, unsafe_allow_html=True)
