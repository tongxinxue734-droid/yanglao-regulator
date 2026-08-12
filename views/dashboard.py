# -*- coding: utf-8 -*-
"""安全态势大屏 - 监管层上帝视角决策中心（真实数据版）
仪表盘/风险构成/趋势/热力图/事件流全部取自真实库，按管辖机构过滤
"""
import datetime
import random

import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from sqlalchemy.orm import Session

import config
from auth import current_user, require_role, visible_org_ids
from models import Hazard, Organization
from services.mask import org_label
from views.theme import metric_card


def _panel(title):
    """浅色面板容器（替代 glass_card(title=) 的错误用法）"""
    return st.markdown(
        f'<div style="background:#F8FAFC;border:1px solid #E2E8F0;border-radius:12px;'
        f'padding:14px 16px;margin-bottom:8px;"><b style="color:#0F172A;font-size:14px;">{title}</b></div>',
        unsafe_allow_html=True)


def render(session: Session):
    require_role(2)
    user = current_user(session)
    vis_org_ids = visible_org_ids(session, user)

    st.markdown("""
        <div style='margin-bottom: 24px;'>
            <h2 style='color: #0F172A; font-weight: 800; margin: 0;'>📊 辖区安全态势全景监控舱</h2>
            <p style='color: #64748B; font-size: 14px; margin-top: 4px;'>
                实时洞察机构合规健康度，AI 驱动风险预警与空间态势感知（数据实时来自检查记录）
            </p>
        </div>
    """, unsafe_allow_html=True)

    query = session.query(Hazard)
    if vis_org_ids:
        query = query.filter(Hazard.org_id.in_(vis_org_ids))
    all_hazards = query.all()

    total_hazards = len(all_hazards)
    closed_hazards = sum(1 for h in all_hazards if h.status in ["closed", "archived"])
    closure_rate = round((closed_hazards / total_hazards * 100) if total_hazards else 100, 1)
    now = datetime.datetime.now()
    overdue_count = sum(1 for h in all_hazards
                        if h.status not in ["closed", "archived"] and h.deadline and h.deadline < now)
    # 预扣分只统计未闭环隐患（已整改闭环的不再预扣，避免分数虚高失真）
    total_deducted = sum(h.deducted for h in all_hazards if h.status not in ("closed", "archived"))
    health_score = max(0, 100 - total_deducted)

    # 真实环比：本周新增 vs 上周新增
    week_ago = now - datetime.timedelta(days=7)
    two_weeks_ago = now - datetime.timedelta(days=14)
    new_this_week = sum(1 for h in all_hazards if h.created_at and h.created_at >= week_ago)
    new_last_week = sum(1 for h in all_hazards
                        if h.created_at and two_weeks_ago <= h.created_at < week_ago)
    week_delta = f"本周新增 {new_this_week} 起" + (f"（较上周{'增' if new_this_week > new_last_week else '减'}"
                                                f"{abs(new_this_week - new_last_week)} 起）" if new_last_week else "")

    # 停业整顿红线预警（真实：12 分档未闭环）
    critical = [h for h in all_hazards if h.deducted >= 12 and h.status != "archived"]
    if critical:
        st.markdown(f"""
        <div style="background: linear-gradient(135deg, #FEF2F2 0%, #FEE2E2 100%); color: #991B1B;
            padding: 22px; border-radius: 16px; margin-bottom: 22px; border-left: 8px solid #DC2626;
            display: flex; align-items: center; gap: 18px;">
            <div style="font-size: 44px;">🚨</div>
            <div>
                <h3 style="margin:0; font-size: 21px; color: #991B1B;">触发【停业整顿】红线预警！</h3>
                <p style="margin-top: 6px; font-size: 14px; opacity: 0.9;">
                    辖区存在 <b>{len(critical)}</b> 起面临停业整顿风险的重大违规未闭环
                    （如 B1 重大安全事故、F6 骗取补贴）。请立即督办相关机构自查整改！
                </p>
            </div>
        </div>
        """, unsafe_allow_html=True)

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        metric_card("累计发现问题", total_hazards, subtitle="全量追踪", delta=week_delta, icon_str="📋")
    with c2:
        metric_card("整改闭环率", f"{closure_rate}%", subtitle="目标: > 95%",
                    delta=f"{round(closure_rate - 90, 1)}% 较基准线", icon_str="🔄")
    with c3:
        metric_card("严重逾期挂单", overdue_count, subtitle="超期未处理", icon_str="⚠️")
    with c4:
        metric_card("辖区合规健康分", f"{health_score} 分", subtitle=f"预扣 {total_deducted} 分",
                    delta="已触发限期整改" if health_score < 90 else "状态良好", icon_str="🎯")

    st.markdown("<div style='height: 20px;'></div>", unsafe_allow_html=True)

    # 紧急预警横幅（逾期+高扣分未闭环隐患）
    alert_hazards = [h for h in all_hazards
                     if h.overdued and h.status not in ("closed", "archived")]
    if alert_hazards:
        lines = ""
        for h in alert_hazards[:8]:
            org_name = org_label(h.org.name, h.org.code) if h.org else "? "
            days = (now - h.deadline).days if h.deadline else 0
            lines += (f'<span style="display:inline-block;background:#FFE4E6;color:#991B1B;border-radius:6px;'
                      f'padding:3px 10px;margin:2px 6px 2px 0;font-size:12px">'
                      f'{org_name} · {h.title[:16]} · 逾期{max(days,1)}天</span>')
        st.markdown(f"""
        <div style="background:linear-gradient(135deg,#FEF2F2,#FEE2E2);border:1px solid #FECACA;
            border-radius:14px;padding:14px 18px;margin-bottom:18px;">
            <div style="display:flex;align-items:center;gap:8px;margin-bottom:8px;">
                <span style="font-size:18px">🔴</span>
                <b style="color:#991B1B;font-size:14px">紧急预警：{len(alert_hazards)} 项逾期未闭环问题</b>
            </div>
            <div style="line-height:2">{lines}</div>
        </div>
        """, unsafe_allow_html=True)

    col_chart1, col_chart2, col_chart3 = st.columns([1.5, 1, 1.5])
    with col_chart1:
        _panel("🎯 实时合规健康度 (Health Score)")
        fig_gauge = go.Figure(go.Indicator(
            mode="gauge+number+delta", value=health_score,
            domain={'x': [0, 1], 'y': [0, 1]},
            title={'text': "综合安全得分", 'font': {'size': 16, 'color': '#475569'}},
            delta={'reference': 90, 'increasing': {'color': "#10B981"}, 'decreasing': {'color': "#EF4444"}},
            gauge={'axis': {'range': [None, 100], 'tickwidth': 1, 'tickcolor': "darkblue"},
                   'bar': {'color': "#3B82F6"}, 'bgcolor': "white",
                   'steps': [{'range': [0, 60], 'color': '#FEE2E2'},
                             {'range': [60, 85], 'color': '#FEF3C7'},
                             {'range': [85, 100], 'color': '#DCFCE7'}],
                   'threshold': {'line': {'color': "red", 'width': 4}, 'thickness': 0.75, 'value': 90}}))
        fig_gauge.update_layout(template="plotly_white", paper_bgcolor="rgba(0,0,0,0)",
                                height=280, margin=dict(l=10, r=10, t=40, b=10))
        st.plotly_chart(fig_gauge, use_container_width=True, config={'displayModeBar': False})

    with col_chart2:
        _panel("⚠️ 风险等级构成")
        level_map = {lvl: 0 for lvl in config.HAZARD_LEVELS}
        for h in all_hazards:
            if h.level in level_map:
                level_map[h.level] += 1
        fig_donut = go.Figure(go.Pie(
            labels=list(level_map.keys()), values=list(level_map.values()), hole=.6,
            marker_colors=["#EF4444", "#F59E0B", "#EAB308", "#3B82F6"]))
        fig_donut.update_traces(textposition='inside', textinfo='percent+label')
        fig_donut.update_layout(template="plotly_white", height=280, showlegend=False,
                                margin=dict(t=10, b=10, l=10, r=10), paper_bgcolor="rgba(0,0,0,0)")
        st.plotly_chart(fig_donut, use_container_width=True, config={'displayModeBar': False})

    with col_chart3:
        _panel("📉 问题发现与闭环趋势（近 30 天）")
        # 真实数据：按近 30 天分 5 段统计新增/闭环
        days_30 = now - datetime.timedelta(days=30)
        recent = [h for h in all_hazards if h.created_at and h.created_at >= days_30]
        segs = []
        for i in range(4, -1, -1):
            start = now - datetime.timedelta(days=6 * (i + 1))
            end = now - datetime.timedelta(days=6 * i)
            segs.append((start, end))
        labels, new_cnt, closed_cnt = [], [], []
        for start, end in segs:
            labels.append(start.strftime("%m-%d"))
            new_cnt.append(sum(1 for h in recent if start <= h.created_at < end))
            closed_cnt.append(sum(1 for h in recent
                                  if h.closed_at and start <= h.closed_at < end))
        fig_trend = go.Figure()
        fig_trend.add_trace(go.Scatter(x=labels, y=new_cnt, mode='lines+markers',
                                       name='新增发现', line=dict(color='#EF4444', width=3)))
        fig_trend.add_trace(go.Bar(x=labels, y=closed_cnt, name='完成闭环',
                                   marker_color='#10B981', opacity=0.7))
        fig_trend.update_layout(template="plotly_white", height=280, barmode='group',
                                paper_bgcolor="rgba(0,0,0,0)",
                                legend=dict(orientation="h", yanchor="bottom", y=1.02,
                                            xanchor="right", x=1),
                                margin=dict(l=10, r=10, t=40, b=10))
        st.plotly_chart(fig_trend, use_container_width=True, config={'displayModeBar': False})

    st.markdown("<div style='height: 20px;'></div>", unsafe_allow_html=True)
    c_heat, c_feed = st.columns([2, 1])

    with c_heat:
        st.subheader("🏢 辖区机构风险分布矩阵 (Heatmap)")
        st.caption("真实统计：各机构 × 隐患类别 的未闭环问题数（颜色越深风险越高）。")
        orgs = session.query(Organization).filter(
            Organization.id.in_(vis_org_ids) if vis_org_ids else True).all()
        org_names = [org_label(o.name, o.code) for o in orgs] or ["未分配机构"]
        cat_keys = list({h.category for h in all_hazards})
        cat_keys = cat_keys[:8] or ["其他"]
        z_data = []
        for o in orgs:
            row = []
            for c in cat_keys:
                n = sum(1 for h in all_hazards
                        if h.org_id == o.id and h.category == c and h.status != "archived")
                row.append(n)
            z_data.append(row)
        if not z_data:
            z_data = [[0] * len(cat_keys)]
        fig_heat = px.imshow(z_data, labels=dict(x="隐患类目", y="机构", color="未闭环数"),
                             x=cat_keys, y=org_names, color_continuous_scale="Reds", aspect="auto")
        fig_heat.update_layout(template="plotly_white", paper_bgcolor="rgba(0,0,0,0)",
                               height=350, margin=dict(l=10, r=10, t=30, b=10))
        st.plotly_chart(fig_heat, use_container_width=True)

    with c_feed:
        st.subheader("⚡ 实时事件流 (Live Feed)")
        st.caption("最新 10 条 AI 识别或人工上报动态（限管辖机构）")
        recent_hazards = session.query(Hazard).order_by(Hazard.created_at.desc()).limit(10).all()
        recent_hazards = [h for h in recent_hazards
                          if not vis_org_ids or h.org_id in vis_org_ids]
        feed_html = "<div style='height: 350px; overflow-y: auto; padding-right: 10px;'>"
        if not recent_hazards:
            feed_html += "<p style='color: #94A3B8;'>暂无动态</p>"
        else:
            for h in recent_hazards:
                color = {"红色": "#EF4444", "橙色": "#F97316", "黄色": "#EAB308",
                         "蓝色": "#3B82F6"}.get(h.level, "#94A3B8")
                time_str = h.created_at.strftime("%m-%d %H:%M") if h.created_at else "刚刚"
                icon = "🤖" if h.source == "AI识别" else ("🎤" if h.source == "语音" else "📝")
                org_name = org_label(h.org.name, h.org.code) if h.org else "—"
                feed_html += f"""
                <div style='background: white; border-left: 4px solid {color}; padding: 11px;
                    margin-bottom: 11px; border-radius: 0 8px 8px 0; box-shadow: 0 1px 3px rgba(0,0,0,0.05);'>
                    <div style='display: flex; justify-content: space-between; margin-bottom: 3px;'>
                        <span style='font-size: 11px; color: #64748B;'>{icon} {time_str} · {org_name}</span>
                        <span style='font-size: 11px; font-weight: bold; color: {color};'>{h.level}风险</span>
                    </div>
                    <div style='font-size: 13px; font-weight: 600; color: #1E293B;'>{h.title[:26]}</div>
                    <div style='font-size: 11px; color: #94A3B8; margin-top: 3px;'>
                        {config.HAZARD_STATUS.get(h.status, "未知")}
                        {f" · 扣 {h.deducted} 分" if h.deducted else ""}</div>
                </div>"""
        feed_html += "</div>"
        st.markdown(feed_html, unsafe_allow_html=True)
