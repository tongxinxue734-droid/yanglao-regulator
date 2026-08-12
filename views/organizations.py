# -*- coding: utf-8 -*-
"""机构管理：多养老机构档案 · 月度得分 · 扣分明细 · 检查记录（监管视角）"""
from collections import Counter
from datetime import datetime
import os

import plotly.graph_objects as go
import streamlit as st
from sqlalchemy.orm import Session

import config
from auth import require_role, current_user, visible_org_ids
from models import Organization, ViolationRecord, Indicator, ComplianceScore
from services.mask import org_label, staff_mask
from services.scoring import compliance_score, punishment_tier
from views.theme import app_header, metric_card, section_title, glass_card, C

PLOTLY = dict(template="plotly_white", paper_bgcolor="rgba(0,0,0,0)",
              plot_bgcolor="rgba(0,0,0,0)", font=dict(color="#334155", size=12),
              margin=dict(l=10, r=10, t=40, b=10))


def render(session: Session):
    require_role(2)
    user = current_user(session)
    app_header("机构管理", "监管辖区养老机构 · 100 分制月度评分 · 检查扣分明细")

    vis_org_ids = visible_org_ids(session, user)
    orgs = session.query(Organization).filter(
        Organization.active == True,
        Organization.id.in_(vis_org_ids) if vis_org_ids else True).all()
    if not orgs:
        st.warning("暂无机构数据，请先初始化演示数据")
        return
    now = datetime.now()
    period = now.strftime("%Y-%m")

    # ============ 机构卡片总览 ============
    section_title("🏛️", "辖区机构月度得分总览", f"{period} · 满分 100 分 · 扣分制")
    cards = ""
    for org in orgs:
        cs = compliance_score(period, session, org.id)
        color = C["accent"] if cs["score"] >= 90 else (C["warn"] if cs["score"] >= 80 else C["danger"])
        status_color = {"在营": "#10B981", "停业整改": "#EF4444", "注销": "#94A3B8"}.get(org.license_status, "#64748B")
        dot_class = {"在营": "lg-dot-green", "停业整改": "lg-dot-red", "注销": ""}.get(org.license_status, "")
        cards += (
            f'<div class="lg-card-hover" style="background:white;border:1px solid #E2E8F0;border-radius:16px;'
            f'padding:1rem 1.1rem;box-shadow:0 4px 16px rgba(15,23,42,0.05);margin-bottom:0.8rem;'
            f'display:flex;align-items:center;gap:14px;">'
            f'<div style="flex:2"><b style="font-size:1.05rem;color:#0F172A">{org_label(org.name, org.code)}</b>'
            f'<div style="color:#94A3B8;font-size:13px;margin-top:2px">{org.level} · {org.org_type}'
            f' · {org.capacity} 床</div></div>'
            f'<div style="color:#94A3B8;font-size:13px;flex:2">{org.address}</div>'
            f'<div style="text-align:center;min-width:120px">'
            f'<div class="lg-num" style="font-size:1.7rem;font-weight:700;color:{color}">{cs["score"]}</div>'
            f'<div style="color:#94A3B8;font-size:12px">本月得分（扣 {cs["deducted"]} 分）</div></div>'
            f'<div style="text-align:center;min-width:90px">'
            f'<span style="color:{status_color};background:{status_color}14;padding:3px 10px;'
            f'border-radius:999px;font-size:13px;font-weight:600">'
            f'<span class="lg-dot {dot_class}"></span>{org.license_status}</span></div>'
            f'</div>')
    st.markdown(cards, unsafe_allow_html=True)

    # ============ 机构选择与详情 ============
    st.divider()
    opts = {org_label(org.name, org.code): org for org in orgs}
    sel = st.selectbox("选择机构查看详情", list(opts.keys()), key="org_sel")
    org = opts[sel]

    cs = compliance_score(period, session, org.id)
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        metric_card("本月得分", f"{cs['score']} 分", f"满分 100 · 扣 {cs['deducted']} 分")
    with c2:
        metric_card("处罚档次", cs["tier"]["grade"], cs["tier"]["penalty"])
    with c3:
        metric_card("累计违规", f"{cs['violations']} 条", "本月检查发现")
    with c4:
        metric_card("机构状态", org.license_status, f"{org.level} · {org.org_type}")

    col_l, col_r = st.columns(2)
    with col_l:
        section_title("📉", "本月扣分明细（按指标）")
        viols = session.query(ViolationRecord).filter(
            ViolationRecord.period == period,
            ViolationRecord.org_id == org.id).all()
        if viols:
            detail = Counter()
            for v in viols:
                detail[v.indicator_code] += v.deducted
            ind_map = {i.code: i for i in session.query(Indicator).all()}
            rows_html = ""
            for code, ded in sorted(detail.items(), key=lambda x: -x[1]):
                ind = ind_map.get(code)
                rows_html += (
                    f'<div style="display:flex;gap:10px;padding:6px 0;border-bottom:1px solid #F1F5F9;">'
                    f'<b style="color:#0F172A;min-width:44px">{code}</b>'
                    f'<span style="flex:1;color:#475569">{ind.item if ind else ""}</span>'
                    f'<b style="color:#EF4444">-{ded} 分</b></div>')
            glass_card(rows_html)
        else:
            st.success("本月无违规扣分记录 🎉")
    with col_r:
        section_title("📈", "近 3 个月得分走势")
        months = []
        scores = []
        for k in range(2, -1, -1):
            ym = _prev_months(now, k)
            s = compliance_score(ym, session, org.id)
            months.append(ym[2:])
            scores.append(s["score"])
        fig = go.Figure(go.Scatter(x=months, y=scores, mode="lines+markers",
                                   line=dict(color="#3B82F6", width=3),
                                   marker=dict(size=9), fill="tozeroy",
                                   fillcolor="rgba(59,130,246,0.10)"))
        fig.update_layout(**PLOTLY, height=260, showlegend=False, yaxis=dict(range=[0, 100]))
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

    # ============ 检查记录 ============
    section_title("🧾", f"该机构近期合规检查记录（{period}）")
    checks = session.query(ComplianceScore).filter(
        ComplianceScore.org_id == org.id,
        ComplianceScore.period == period,
        ComplianceScore.found == True).all()
    if checks:
        ind_map = {i.code: i for i in session.query(Indicator).all()}
        data = []
        for ck in checks:
            ind = ind_map.get(ck.indicator_code)
            data.append({"指标": ck.indicator_code, "事项": ind.item if ind else "",
                         "类别": ind.category if ind else "", "扣分": ck.deducted,
                         "备注": ck.comment})
        import pandas as pd
        st.dataframe(pd.DataFrame(data), use_container_width=True, hide_index=True)
    else:
        st.caption("本月无违规检查记录")

    # ========== 新增：机构月度得分排名 ==========
    st.markdown("<hr style='border-top:1px dashed #CBD5E1; margin:28px 0;'>", unsafe_allow_html=True)
    section_title("🏁", "机构月度得分排名", f"{period} · 100 分制 · 按得分降序")
    rank_data = []
    prev_m = _prev_months(now, 1)
    for o in orgs:
        cs = compliance_score(period, session, o.id)
        prev_cs = compliance_score(prev_m, session, o.id)
        delta = cs["score"] - prev_cs["score"]
        d_text = ("+" + str(delta)) if delta > 0 else (str(delta) if delta < 0 else "→")
        rank_data.append({"机构": org_label(o.name, o.code), "得分": cs["score"], "扣分": cs["deducted"], "环比": d_text})
    rank_data.sort(key=lambda x: x["得分"], reverse=True)
    rows_html = ""
    medals = {0: "🥇", 1: "🥈", 2: "🥉"}
    arrow_colors = {"↑": "#EF4444", "↓": "#10B981", "→": "#94A3B8"}
    for i, r in enumerate(rank_data):
        m = medals.get(i, f"{i+1}")
        d = r["环比"]
        arrow = "↑" if d.startswith("+") else ("↓" if d.startswith("-") else "→")
        ac = arrow_colors[arrow]
        rows_html += (
            f'<div style="display:flex;align-items:center;gap:10px;padding:8px 0;'
            f'border-bottom:1px solid #F1F5F9">'
            f'<span style="width:28px;text-align:center;font-size:18px">{m}</span>'
            f'<span style="flex:2;font-weight:500">{r["机构"]}</span>'
            f'<span style="width:56px;text-align:right;font-weight:700">{r["得分"]}</span>'
            f'<span style="width:64px;text-align:right;font-size:12px;color:{ac}">{arrow} {d}</span>'
            f'</div>')
    glass_card(rows_html)

    # ========== 新增：检查员本月工作量面板 ==========
    st.markdown("<hr style='border-top:1px dashed #CBD5E1; margin:28px 0;'>", unsafe_allow_html=True)
    section_title("👤", "检查员本月工作量", f"{period} · 检查人次 / 发现问题数 / 扣分总额")
    from models import Hazard as _H, User as _U
    checker_stats = {}
    all_checks = session.query(_H).filter(
        _H.org_id.in_([o.id for o in orgs])).all()
    all_checks = [h for h in all_checks if h.created_at and h.created_at.strftime("%Y-%m") == period]
    for h in all_checks:
        uid = h.reporter_id
        if uid not in checker_stats:
            u = session.query(_U).get(uid)
            checker_stats[uid] = {"姓名": staff_mask(u.name) if u else str(uid), "部门": u.dept_name if u else "",
                                  "检查次数": 0, "发现问题": 0, "累计扣分": 0}
        checker_stats[uid]["检查次数"] += 1
        if h.deducted:
            checker_stats[uid]["发现问题"] += 1
            checker_stats[uid]["累计扣分"] += h.deducted
    if checker_stats:
        import pandas as pd
        df_stats = pd.DataFrame(list(checker_stats.values()))
        df_stats = df_stats.sort_values("检查次数", ascending=False)
        c1, c2 = st.columns(2)
        with c1:
            st.dataframe(df_stats, use_container_width=True, hide_index=True)
        with c2:
            fig_checker = go.Figure(go.Bar(
                x=df_stats["姓名"], y=df_stats["发现问题"],
                marker_color="#2563EB", text=df_stats["发现问题"], textposition="outside"))
            fig_checker.update_layout(template="plotly_white", paper_bgcolor="rgba(0,0,0,0)",
                                      height=260, title="发现违规数", showlegend=False,
                                      margin=dict(l=10, r=10, t=40, b=10))
            st.plotly_chart(fig_checker, use_container_width=True, config={'displayModeBar': False})
    else:
        st.caption("本月暂无检查记录")

    st.markdown("<hr style='border-top:1px dashed #CBD5E1; margin:28px 0;'>", unsafe_allow_html=True)

    # ============ 多机构对比报表（新增） ============
    section_title("📊", "多机构月度得分对比", "近 6 个月 · 100 分制 · 全辖区横向比较")
    import plotly.express as px
    import pandas as pd
    months = [_prev_months(now, k) for k in range(5, -1, -1)]
    score_matrix = {}
    for o in orgs:
        score_matrix[org_label(o.name, o.code)] = [compliance_score(m, session, o.id)["score"] for m in months]

    col_a, col_b = st.columns(2)
    with col_a:
        st.caption("得分热力矩阵（绿→红表示健康→风险）")
        dfm = pd.DataFrame(score_matrix, index=[m[2:] for m in months])
        fig_hm = px.imshow(dfm.T, labels=dict(x="月份", y="机构", color="得分"),
                           color_continuous_scale=["#EF4444", "#F59E0B", "#DCFCE7", "#10B981"],
                           aspect="auto", zmin=0, zmax=100)
        fig_hm.update_layout(template="plotly_white", paper_bgcolor="rgba(0,0,0,0)",
                             height=280, margin=dict(l=10, r=10, t=30, b=10))
        st.plotly_chart(fig_hm, use_container_width=True)
    with col_b:
        st.caption("各机构得分走势对比")
        fig_lines = go.Figure()
        colors = ["#2563EB", "#7C3AED", "#0EA5E9", "#10B981", "#F59E0B", "#EF4444"]
        for i, (name, scores) in enumerate(score_matrix.items()):
            fig_lines.add_trace(go.Scatter(x=[m[2:] for m in months], y=scores,
                                           mode="lines+markers", name=name,
                                           line=dict(width=2.5, color=colors[i % 6])))
        fig_lines.update_layout(template="plotly_white", paper_bgcolor="rgba(0,0,0,0)",
                                height=280, margin=dict(l=10, r=10, t=30, b=10),
                                yaxis=dict(range=[0, 100]), legend=dict(font=dict(size=10)))
        st.plotly_chart(fig_lines, use_container_width=True)

    # 导出多机构对比 Excel
    if st.button("💾 导出多机构得分对比 Excel"):
        path = os.path.join(config.REPORT_DIR, f"多机构得分对比_{period}.xlsx")
        with pd.ExcelWriter(path, engine="openpyxl") as w:
            pd.DataFrame(score_matrix, index=[m[2:] for m in months]).to_excel(
                w, sheet_name="得分矩阵", index_label="月份")
            detail = []
            for o in orgs:
                for m in months:
                    detail.append({"机构": org_label(o.name, o.code), "期间": m,
                                   "得分": compliance_score(m, session, o.id)["score"],
                                   "扣分": compliance_score(m, session, o.id)["deducted"]})
            pd.DataFrame(detail).to_excel(w, sheet_name="明细", index=False)
        st.success(f"已导出：{path}")

    # ========== 新增：得分趋势预测 ==========
    st.markdown("<hr style='border-top:1px dashed #CBD5E1; margin:28px 0;'>", unsafe_allow_html=True)
    section_title("📈", "得分趋势预测（线性回归 + 移动平均）", "基于近 6 月各机构得分预测下月走势")
    org_sel_pred = st.selectbox("选择机构查看预测", [org_label(o.name, o.code) for o in orgs], key="pred_org")
    o_pred = next(o for o in orgs if org_label(o.name, o.code) == org_sel_pred)
    months = [_prev_months(now, k) for k in range(5, -1, -1)]
    scores = []
    for m in months:
        cs = compliance_score(m, session, o_pred.id)
        scores.append(cs["score"])
    # 3 期移动平均
    ma = []
    for i in range(len(scores)):
        w = scores[max(0, i - 2):i + 1]
        ma.append(round(sum(w) / len(w), 1))
    # 线性回归预测下月
    if len(scores) >= 2:
        n = len(scores)
        x = list(range(n))
        sx, sy = sum(x), sum(scores)
        sxx, sxy = sum(i * i for i in x), sum(x[i] * scores[i] for i in range(n))
        slope = (n * sxy - sx * sy) / (n * sxx - sx * sx) if (n * sxx - sx * sx) else 0
        intercept = (sy - slope * sx) / n
        forecast = max(0, round(slope * n + intercept, 1))
    else:
        forecast = scores[-1]
    m_future = _next_month(now)
    fig_pred = go.Figure()
    fig_pred.add_trace(go.Scatter(
        x=[m[2:] for m in months], y=scores, mode="lines+markers", name="实际得分",
        line=dict(color="#2563EB", width=3), marker=dict(size=8)))
    fig_pred.add_trace(go.Scatter(
        x=[m[2:] for m in months], y=ma, mode="lines", name="3期移动平均",
        line=dict(color="#7C3AED", width=2, dash="dot")))
    fig_pred.add_trace(go.Scatter(
        x=[m[2:] for m in months] + [m_future[2:]], y=scores + [forecast],
        mode="lines+markers", name="预测",
        line=dict(color="#10B981", width=2.5, dash="dash"),
        marker=dict(symbol="diamond", size=10)))
    fig_pred.update_layout(template="plotly_white", paper_bgcolor="rgba(0,0,0,0)",
                           height=320, title=f"{org_label(o_pred.name, o_pred.code)} · 下月预测 {forecast} 分",
                           margin=dict(l=10, r=10, t=40, b=10),
                           yaxis=dict(range=[0, 100]))
    st.plotly_chart(fig_pred, use_container_width=True, config={'displayModeBar': False})


def _prev_months(now, k):
    y, m = now.year, now.month - k
    while m <= 0:
        m += 12
        y -= 1
    return f"{y}-{m:02d}"


def _next_month(now):
    y, m = now.year, now.month + 1
    if m > 12:
        m = 1
        y += 1
    return f"{y}-{m:02d}"
