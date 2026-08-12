# -*- coding: utf-8 -*-
"""分析中心：SLA 时效 · 根因柏拉图 · 财务惩罚测算 · 高频触红指标（深度版）"""
import re
from collections import Counter

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from sqlalchemy.orm import Session
from datetime import datetime

from auth import current_user, visible_user_ids, visible_org_ids
from models import Hazard, Indicator, Organization
from services.mask import org_label
from services.scoring import punishment_tier
from views.theme import metric_card

PLOTLY_LAYOUT = dict(
    template="plotly_white",
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font=dict(family="Noto Sans SC", color="#334155", size=12),
    margin=dict(l=20, r=20, t=50, b=20),
    title_font=dict(color="#0F172A", size=16),
)


def _tier_fine(deduct: int) -> int:
    """官方规则：累计扣分落入处罚档次后的一次性罚款金额（元）"""
    tier = punishment_tier(deduct)
    m = re.search(r"(\d[\d,]*)\s*元", tier.get("penalty", ""))
    return int(m.group(1).replace(",", "")) if m else 0


def render(session: Session):
    user = current_user(session)
    vis_org_ids = visible_org_ids(session, user)

    st.markdown("""
        <div style='margin-bottom: 24px;'>
            <h2 style='color: #0F172A; font-weight: 800; margin: 0;'>📈 深度数据分析中心</h2>
            <p style='color: #64748B; font-size: 14px; margin-top: 4px;'>
                多维穿透分析：SLA 流转时效 · 根因柏拉图 · 违规财务风险测算
            </p>
        </div>
    """, unsafe_allow_html=True)

    query = session.query(Hazard)
    if vis_org_ids:
        query = query.filter(Hazard.org_id.in_(vis_org_ids))
    elif user.role_level != 1:
        vis_users = visible_user_ids(session, user)
        query = query.filter((Hazard.reporter_id.in_(vis_users)) | (Hazard.assignee_id.in_(vis_users)))
    rows = query.all()
    orgs = session.query(Organization).filter(Organization.active == True).all()

    data = []
    for h in rows:
        data.append({
            "id": h.id, "org_id": h.org_id, "category": h.category, "level": h.level,
            "status": h.status, "created_at": h.created_at, "deadline": h.deadline,
            "deducted": h.deducted, "indicator_code": h.indicator_code,
        })
    df = pd.DataFrame(data)

    # ---------- SLA ----------
    st.subheader("⏱️ 整改 SLA (Service Level Agreement) 监控")
    now = datetime.now()
    sla_ok = sla_warn = sla_over = 0
    for h in rows:
        if h.status in ("closed", "archived") or not h.deadline:
            continue
        remain = (h.deadline - now).total_seconds() / 86400
        if h.overdued or remain < 0:
            sla_over += 1
        elif remain <= 1:
            sla_warn += 1
        else:
            sla_ok += 1
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        metric_card("SLA 履约正常", sla_ok, "期限内（安全）", icon_str="🟢")
    with c2:
        metric_card("24h 内临期预警", sla_warn, "即将到期（需提醒）", icon_str="🟡")
    with c3:
        metric_card("已严重逾期", sla_over, "超期未改（将扣分）", icon_str="🔴")
    with c4:
        total_active = sla_ok + sla_warn + sla_over
        rate = round(sla_ok / total_active * 100, 1) if total_active else 100.0
        metric_card("SLA 整体达标率", f"{rate}%", f"总计 {total_active} 项进行中", icon_str="📊")

    st.markdown("<hr style='border-top: 1px dashed #CBD5E1; margin: 26px 0;'>", unsafe_allow_html=True)

    # ---------- 根因柏拉图 ----------
    st.subheader("🔍 违规根因分析 (80/20 柏拉图)")
    st.caption("分析哪些类别的隐患占总问题数的绝大部分（二八定律），帮助管理层精准投放监管资源。")
    if not df.empty:
        cat_counts = df['category'].value_counts().reset_index()
        cat_counts.columns = ['类别', '频次']
        cat_counts['累计占比'] = cat_counts['频次'].cumsum() / cat_counts['频次'].sum() * 100
        fig_pareto = go.Figure()
        fig_pareto.add_trace(go.Bar(x=cat_counts['类别'], y=cat_counts['频次'],
                                    name='频次', marker=dict(color='#3B82F6')))
        fig_pareto.add_trace(go.Scatter(x=cat_counts['类别'], y=cat_counts['累计占比'],
                                        name='累计占比(%)', mode='lines+markers', yaxis='y2',
                                        line=dict(color='#EF4444', width=3)))
        fig_pareto.update_layout(
            **PLOTLY_LAYOUT, height=380,
            yaxis=dict(title='问题频次 (次)'),
            yaxis2=dict(title='累计占比 (%)', overlaying='y', side='right',
                        range=[0, 105], tickfont=dict(color='#EF4444')),
            legend=dict(x=0.01, y=0.99))
        st.plotly_chart(fig_pareto, use_container_width=True)
    else:
        st.info("数据量不足，无法生成根因分析柏拉图。")

    st.markdown("<hr style='border-top: 1px dashed #CBD5E1; margin: 26px 0;'>", unsafe_allow_html=True)

    c_fin1, c_fin2 = st.columns([1, 1.5])
    with c_fin1:
        st.subheader("💰 违规财务惩罚测算")
        st.caption("按《评价指标》处罚档次规则：机构累计扣分落入档次 → 对应一次性罚款（估算）")

        # 官方规则：按机构累计扣分落档次，映射罚款金额
        org_deduct = Counter()
        for h in rows:
            if h.org_id and h.status not in ("closed", "archived"):
                org_deduct[h.org_id] += h.deducted or 0
        total_penalty = 0
        breakdown = Counter()
        for oid, ded in org_deduct.items():
            amt = _tier_fine(ded)
            total_penalty += amt
            if amt:
                breakdown[f"{amt}元({punishment_tier(ded)['grade']})"] += 1

        st.markdown(f"""
        <div style="background-color: #F8FAFC; border: 1px solid #E2E8F0; padding: 20px;
            border-radius: 12px; text-align: center;">
            <div style="font-size: 14px; color: #64748B;">当前挂账机构预估罚金总额</div>
            <div style="font-size: 34px; font-weight: bold; color: #B91C1C; margin: 10px 0;">¥ {total_penalty:,.0f}</div>
            <div style="font-size: 12px; color: #94A3B8;">*按累计扣分落档次估算，逾期未整改将正式生成罚单</div>
        </div>
        """, unsafe_allow_html=True)
        df_punish = pd.DataFrame(list(breakdown.items()), columns=["罚款档次", "机构数"]) \
            if breakdown else pd.DataFrame([("暂无挂账", 0)], columns=["罚款档次", "机构数"])
        st.dataframe(df_punish, use_container_width=True, hide_index=True)

    with c_fin2:
        st.subheader("📌 高频触红指标 TOP 10")
        st.caption("统计系统中最常被触发的具体扣分标准条款")
        if not df.empty and 'indicator_code' in df.columns:
            ind_counts = df[df['indicator_code'].notna()]['indicator_code'].value_counts().head(10).reset_index()
            ind_counts.columns = ['指标编号', '触发次数']
            ind_details = []
            for code in ind_counts['指标编号']:
                ind_obj = session.query(Indicator).filter(Indicator.code == code).first()
                ind_details.append(f"[{code}] {ind_obj.item} (扣{ind_obj.deduct}分)" if ind_obj
                                   else f"[{code}] 未知指标")
            ind_counts['指标说明'] = ind_details
            fig_bar = px.bar(ind_counts, x='触发次数', y='指标说明', orientation='h',
                             color='触发次数', color_continuous_scale='Reds')
            fig_bar.update_layout(**PLOTLY_LAYOUT, height=360,
                                  yaxis={'categoryorder': 'total ascending'})
            st.plotly_chart(fig_bar, use_container_width=True)
        else:
            st.info("暂无关联指标的数据统计。")

    # ========== 新增：整改闭环流向桑基图 ==========
    st.markdown("<hr style='border-top: 1px dashed #CBD5E1; margin: 30px 0;'>", unsafe_allow_html=True)
    st.subheader("🔀 整改闭环流向分析")
    st.caption("展示隐患从上报到闭环的流转路径与各阶段积压量，辅助识别流程堵点。")
    status_order = ["pending_rectify", "rectifying", "pending_review", "rejected", "closed"]
    status_label = {"pending_rectify": "待整改", "rectifying": "整改中", "pending_review": "待复查",
                    "rejected": "打回重改", "closed": "已闭环"}
    status_count = {s: 0 for s in status_order}
    for h in rows:
        if h.status in status_count:
            status_count[h.status] += 1
    totals = [status_count[s] for s in status_order]
    sankey_labels = ["待整改", "整改中", "待复查", "已闭环", "打回重改"]
    source = [0, 1, 2, 2, 2]
    target = [1, 2, 3, 4, 1]
    value = [totals[0], totals[1] + totals[4], totals[3], totals[4], totals[2]]
    fig_sankey = go.Figure(go.Sankey(
        node=dict(pad=20, thickness=22, line=dict(color="#475569", width=1),
                  label=sankey_labels,
                  color=["#EF4444", "#F59E0B", "#3B82F6", "#10B981", "#F472B6"]),
        link=dict(source=source, target=target, value=value,
                  color=["rgba(239,68,68,.35)", "rgba(245,158,11,.35)",
                         "rgba(16,185,129,.35)", "rgba(244,114,182,.35)",
                         "rgba(59,130,246,.35)"])))
    fig_sankey.update_layout(**PLOTLY_LAYOUT, height=340)
    st.plotly_chart(fig_sankey, use_container_width=True, config={'displayModeBar': False})

    # ========== 新增：各机构平均整改时效对比 ==========
    st.markdown("<hr style='border-top: 1px dashed #CBD5E1; margin: 30px 0;'>", unsafe_allow_html=True)
    st.subheader("⏱️ 各机构整改时效对比")
    st.caption("平均闭环天数（仅统计已闭环隐患），越低说明整改越快。")
    org_names = []
    org_days = []
    for o in orgs:
        oh = [h for h in rows if h.org_id == o.id and h.status in ("closed", "archived")
              and h.closed_at and h.created_at]
        if oh:
            avg = sum((h.closed_at - h.created_at).total_seconds() / 86400 for h in oh) / len(oh)
            org_names.append(org_label(o.name, o.code))
            org_days.append(round(avg, 1))
    if org_days:
        fig_bar2 = go.Figure(go.Bar(
            x=org_names, y=org_days,
            marker_color=["#EF4444" if d > 7 else "#F59E0B" if d > 4 else "#10B981" for d in org_days],
            text=org_days, textposition="outside",
            hovertemplate="%{x}：%{y} 天<extra></extra>"))
        fig_bar2.update_layout(**PLOTLY_LAYOUT, height=300, title="平均闭环天数",
                               showlegend=False)
        st.plotly_chart(fig_bar2, use_container_width=True, config={'displayModeBar': False})
    else:
        st.caption("暂无已闭环隐患数据")
