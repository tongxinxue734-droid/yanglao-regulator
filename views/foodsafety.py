# -*- coding: utf-8 -*-
"""阳光明厨与食药溯源台账 — 模块三 · 高频合规雷区
48h 食品留样数字化台账（拍照+时间戳）· 餐具每日消杀 · 许可证到期预警
"""
import pandas as pd
import streamlit as st
from sqlalchemy.orm import Session

from auth import require_role
from services.foodsafety import sample_logs, disinfection_logs, license_alerts, license_summary
from views.theme import app_header, metric_card, section_title


def render(session: Session):
    require_role(1)
    app_header("阳光明厨 · 食药溯源", "48h 留样数字化台账 · 餐具消杀记录 · 许可证到期预警（D8 食品安全）")

    red, total = license_summary(session)
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        metric_card("在库留样", "96", "48h 留样批次")
    with c2:
        metric_card("今日已消毒", "10/12", "餐具消杀完成率")
    with c3:
        metric_card("许可证预警", red, "到期≤30天", icon_str="🚨")
    with c4:
        metric_card("监管机构", total, "持证机构")

    # ============ 许可证到期预警 ============
    section_title("🚨", "食品经营许可证到期预警", "到期前 30 天自动抛出红色警报工单")
    df_lic = pd.DataFrame(license_alerts(session))
    red_rows = df_lic[df_lic["预警"].str.contains("红色")]
    if not red_rows.empty:
        names = "、".join(red_rows["机构"].tolist())
        st.markdown(f"""
        <div style="background:linear-gradient(135deg,#FEF2F2,#FEE2E2);border-left:6px solid #DC2626;
            border-radius:10px;padding:14px 18px;color:#991B1B;">
            🔴 <b>{len(red_rows)} 家机构许可证即将到期：{names}</b>，请督办续办！
        </div>""", unsafe_allow_html=True)
    st.dataframe(df_lic, use_container_width=True, hide_index=True)

    # ============ 留样台账 ============
    st.markdown("<hr style='border-top:1px dashed #CBD5E1;margin:24px 0;'>", unsafe_allow_html=True)
    section_title("🥗", "48 小时食品留样数字化台账", "拍照 + 时间戳 + 留样克重，杜绝 D8 食品安全违规")
    logs = sample_logs(session)
    df_s = pd.DataFrame(logs)
    c_l, c_r = st.columns([2, 1])
    with c_l:
        org_filter = st.selectbox("筛选机构", ["全部"] + sorted(df_s["机构"].unique().tolist()))
        view = df_s if org_filter == "全部" else df_s[df_s["机构"] == org_filter]
        st.dataframe(view, use_container_width=True, hide_index=True)
    with c_r:
        st.markdown("""
        <div style="border:1px solid #E5E7EB;border-radius:10px;padding:14px;background:#FAFBFC;">
            <b>📎 留样要求（GB 31621）</b><br>
            • 每餐成品 ≤2h 内留样<br>
            • 克重 ≥125g / 份<br>
            • 冷藏保存 48h<br>
            • 标注餐次与留样人<br>
            <br><b>🔍 违规后果</b><br>
            D8 未按规定留样：扣 6 分
        </div>
        """, unsafe_allow_html=True)

    # ============ 餐具消杀 ============
    st.markdown("<hr style='border-top:1px dashed #CBD5E1;margin:24px 0;'>", unsafe_allow_html=True)
    section_title("🧼", "餐具每日消杀记录", "三餐后热力/红外/化学消毒，全程留痕")
    df_d = pd.DataFrame(disinfection_logs(session))
    st.dataframe(df_d, use_container_width=True, hide_index=True)
