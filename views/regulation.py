# -*- coding: utf-8 -*-
"""智慧监管中台 — G端一网统管
信用评级 A/B/C/D · 骗补智能预警 · 免申即享白名单 · IoT 无感体征 · 智能预警
"""
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from sqlalchemy.orm import Session

from auth import require_role
from services.regulation import (org_credit_ratings, fraud_leave_sim,
                                 exemption_whitelist, vital_signs_sim,
                                 regulation_summary)
from services.scoring import smart_alerts
from views.theme import app_header, metric_card, section_title, glass_card

PLOTLY = dict(template="plotly_white", paper_bgcolor="rgba(0,0,0,0)",
              plot_bgcolor="rgba(0,0,0,0)", font=dict(color="#334155", size=12),
              margin=dict(l=10, r=10, t=40, b=10))


def render(session: Session):
    require_role(1)
    app_header("智慧监管中台", "G 端一网统管 · 跨部门防线 · 信用分类监管 · IoT 无感监测")
    st.markdown("""
    <div style="border:1px dashed #F59E0B;border-radius:8px;padding:8px 14px;font-size:12px;
        color:#92400E;background:#FFFBEB;margin:0 0 14px 0;">
        🛡️ <b>数据安全声明</b>：本页数据为演示样本，已按《政务数据脱敏 5 步法》处理——
        老人全匿名（长者编号）、机构以编码标识、年龄范围化、号码截断；
        涉及个人信息一律不输出全名，操作日志全程留痕。
    </div>""", unsafe_allow_html=True)

    # ============ 指标总览 ============
    s = regulation_summary(session)
    c1, c2, c3, c4, c5, c6 = st.columns(6)
    with c1:
        metric_card("辖区机构", s["机构数"], "在册养老机构")
    with c2:
        metric_card("A 级机构", s["A级"], "信用优秀", icon_str="🟢")
    with c3:
        metric_card("D 级机构", s["D级"], "重点监管", icon_str="🔴")
    with c4:
        metric_card("骗补预警", s["骗补预警"], "涉嫌骗取补贴", icon_str="🚨")
    with c5:
        metric_card("体征异常", s["体征异常"], "雷达夜间异常", icon_str="❤️")
    with c6:
        metric_card("智能预警", s["待办工单"], "需督办事项", icon_str="⚠️")

    # ============ 信用评级看板 ============
    section_title("💠", "多维信用评级与分类监管", "违规扣分 + IoT 报警频次 → A/B/C/D 动态信用等级")
    ratings = org_credit_ratings(session)
    df = pd.DataFrame(ratings)

    col_map, col_tab = st.columns([1.2, 1])
    with col_map:
        st.caption("机构空间分布（D 级标红锁定）")
        fig_map = px.scatter(df, x="x", y="y", color="等级", size="得分",
                             color_discrete_map={"A": "#059669", "B": "#2563EB",
                                                 "C": "#D97706", "D": "#DC2626"},
                             hover_name="机构", hover_data=["得分", "监管策略"],
                             text="code", size_max=38)
        fig_map.update_layout(**PLOTLY, height=340, showlegend=True,
                              xaxis=dict(showticklabels=False, showgrid=False, zeroline=False),
                              yaxis=dict(showticklabels=False, showgrid=False, zeroline=False))
        fig_map.update_traces(textposition="top center", textfont=dict(size=9))
        st.plotly_chart(fig_map, use_container_width=True, config={'displayModeBar': False})
    with col_tab:
        st.caption("信用评级明细（按得分排序）")
        show = df[["排名", "code", "机构", "得分", "等级", "违规次数", "IoT报警", "监管策略"]]
        st.dataframe(show, use_container_width=True, hide_index=True)

    # D 级重点监管横幅
    d_orgs = df[df["等级"] == "D"]
    if not d_orgs.empty:
        names = "、".join(d_orgs["机构"].tolist())
        st.markdown(f"""
        <div style="background:linear-gradient(135deg,#FEF2F2,#FEE2E2);border:1px solid #FECACA;
            border-radius:12px;padding:14px 18px;margin:10px 0;">
            <b style="color:#991B1B;">🔴 D 级重点监管：{names}</b>
            <span style="color:#B91C1C;margin-left:12px;font-size:13px;">实施高频抽查、限制扩张</span>
        </div>
        """, unsafe_allow_html=True)

    # ============ 骗补智能预警 ============
    st.markdown("<hr style='border-top:1px dashed #CBD5E1;margin:24px 0;'>", unsafe_allow_html=True)
    section_title("🛡️", "智能反欺诈 · 资金合规引擎", "门禁/IoT 离院数据 vs 补贴申报 → 涉嫌骗补红色预警（对应 F6，扣 12 分）")
    frauds = fraud_leave_sim(session)
    df_fraud = pd.DataFrame(frauds)
    red_count = len(df_fraud[df_fraud["风险"].str.contains("红色")])
    if red_count:
        st.markdown(f"""
        <div style="background:linear-gradient(135deg,#FEF2F2,#FEE2E2);border-left:6px solid #DC2626;
            border-radius:10px;padding:14px 18px;margin-bottom:12px;color:#991B1B;">
            🚨 系统侦测到 <b>{red_count}</b> 起「老人连续离院 ≥15 天仍申报补贴」的涉嫌骗补事件，请立即核实并停发补贴！
        </div>""", unsafe_allow_html=True)
    st.dataframe(df_fraud[["机构", "老人", "离院天数", "补贴申报", "风险", "建议扣分"]],
                 use_container_width=True, hide_index=True)

    # ============ 免申即享白名单 ============
    st.markdown("<hr style='border-top:1px dashed #CBD5E1;margin:24px 0;'>", unsafe_allow_html=True)
    section_title("🎁", "津贴免申即享白名单", "反向大数据筛查：自动识别高龄/特困老人，提示机构一键确认")
    st.dataframe(pd.DataFrame(exemption_whitelist(session)), use_container_width=True, hide_index=True)

    # ============ IoT 体征看板 ============
    st.markdown("<hr style='border-top:1px dashed #CBD5E1;margin:24px 0;'>", unsafe_allow_html=True)
    section_title("📡", "IoT 无感体征监测（毫米波雷达）", "无需穿戴 · 实时心率/呼吸 · 夜间异常自动报警")
    vitals = vital_signs_sim()
    df_v = pd.DataFrame(vitals)
    c_v1, c_v2 = st.columns(2)
    with c_v1:
        st.dataframe(df_v, use_container_width=True, hide_index=True)
    with c_v2:
        # 心率/呼吸双轴图
        fig_v = go.Figure()
        fig_v.add_trace(go.Bar(x=df_v["床位"], y=[int(x.split()[0]) for x in df_v["心率"]],
                               name="心率", marker_color=["#EF4444" if e else "#3B82F6" for e in df_v["异常"]]))
        fig_v.add_trace(go.Scatter(x=df_v["床位"], y=[int(x.split()[0]) for x in df_v["呼吸"]],
                                   name="呼吸", yaxis="y2", mode="lines+markers",
                                   line=dict(color="#10B981", width=2)))
        fig_v.update_layout(**PLOTLY, height=300, yaxis=dict(title="心率 bpm", range=[50, 140]),
                            yaxis2=dict(title="呼吸 次/分", overlaying="y", side="right", range=[5, 35]),
                            legend=dict(orientation="h", y=1.1, x=0))
        st.plotly_chart(fig_v, use_container_width=True, config={'displayModeBar': False})

    # ============ 智能预警 ============
    st.markdown("<hr style='border-top:1px dashed #CBD5E1;margin:24px 0;'>", unsafe_allow_html=True)
    section_title("🚨", "智能预警引擎", "区域高频 · 逾期率超标 · 得分偏低")
    alerts = smart_alerts(session)
    if alerts:
        for a in alerts:
            color = {"高风险": "#DC2626", "关注": "#D97706", "提醒": "#B45309"}.get(a["level"], "#64748B")
            glass_card(f'<b style="color:{color}">{a["type"]}</b> · {a["content"]}')
    else:
        st.success("当前无触发预警")
