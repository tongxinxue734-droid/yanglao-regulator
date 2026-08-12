# -*- coding: utf-8 -*-
"""报告中心：月度机构报告 / 年度总报告生成、导出（Excel/HTML/PDF）、永久存档"""
import os
from datetime import datetime

import streamlit as st
from sqlalchemy.orm import Session

import config
from auth import current_user, require_role, visible_org_ids
from models import Report, AuditLog, Organization
from services.mask import org_label
from services.reports import monthly_report, annual_report, export_excel, export_html, analysis_text, export_docx
from views.common import kpi_card

AIGC_NOTE = "本报告由系统自动生成并含 AI 辅助分析内容（依据 AIGC 标识规范标注）"


def _read_bytes(path: str) -> bytes:
    with open(path, "rb") as f:
        return f.read()


def render(session: Session):
    user = current_user(session)
    require_role(2)
    st.header("报告中心")
    st.caption("按机构自动生成月度与年度检查报告，支持导出带机构抬头/公章位/签字栏的 PDF 与明细 Excel，永久存档按年回溯")

    # 机构选择（按管辖片区）
    vis_org_ids = visible_org_ids(session, user)
    orgs = session.query(Organization).filter(
        Organization.active == True,
        Organization.id.in_(vis_org_ids) if vis_org_ids else True).all()
    org_opts = {org_label(o.name, o.code): o for o in orgs} if orgs else {"全辖区汇总": None}
    org_sel = st.selectbox("报告机构", list(org_opts.keys()), key="rep_org")
    org = org_opts[org_sel]
    org_id = org.id if org else None
    st.caption(f"报告对象：{org_label(org.name, org.code) if org else '全辖区汇总'} · {AIGC_NOTE}")

    # ---------- 月度报告 ----------
    st.subheader("📅 月度机构报告")
    periods = []
    # 从数据推导可选期间
    from models import Hazard, ComplianceScore
    for h in session.query(Hazard).all():
        if h.created_at:
            p = h.created_at.strftime("%Y-%m")
            if p not in periods:
                periods.append(p)
    for c in session.query(ComplianceScore).all():
        if c.period not in periods:
            periods.append(c.period)
    periods.sort(reverse=True)
    if not periods:
        periods = [datetime.now().strftime("%Y-%m")]
    m_period = st.selectbox("月度期间", periods, key="rep_m")

    if st.button("🔄 生成/刷新月度报告", key="gen_m"):
        rep = monthly_report(session, m_period, org_id)
        st.session_state["rep_m_data"] = rep
        st.session_state["rep_m_type"] = "月度"

    rep = st.session_state.get("rep_m_data")
    if rep and st.session_state.get("rep_m_type") == "月度" and rep.get("period") == m_period:
        cs = rep["compliance"]
        c1, c2, c3, c4, c5 = st.columns(5)
        with c1:
            kpi_card("隐患总数", rep["total"])
        with c2:
            kpi_card("整改完成率", f"{rep['rect_rate']}%", "#00b894")
        with c3:
            kpi_card("逾期数", rep["overdued"], "#d63031")
        with c4:
            kpi_card("综合得分", cs["score"], "#1f6feb")
        with c5:
            kpi_card("处罚档次", cs["tier"]["grade"], "#e17055")
        st.markdown(f"**环比**：{'较上月上升' if (rep['mom'] or 0) > 0 else '较上月下降'} {abs(rep['mom'] or 0)}%"
                    if rep["mom"] is not None else "**环比**：首月无对比数据")
        st.markdown(f"**分析结论**：{analysis_text(rep, '月度')}")
        c1, c2, c3 = st.columns(3)
        if c1.download_button("⬇️ 下载 HTML 报告（可打印 PDF）", export_html(rep, "月度"),
                              file_name=f"{org_label(org.name, org.code) if org else '全辖区'}_月度报告_{m_period}.html",
                              mime="text/html"):
            pass
        if c2.download_button("📄 下载 Word 公文（红头）", _read_bytes(export_docx(rep, "月度")),
                              file_name=f"{org_label(org.name, org.code) if org else '全辖区'}_月度检查报告_{m_period}.docx",
                              mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"):
            pass
        if c3.button("💾 导出 Excel 明细并存档"):
            path = export_excel(rep, "月度")
            org_tag = org_label(org.name, org.code) if org else "全辖区"
            session.add(Report(title=f"{org_tag}月度报告 {m_period}", rtype="月度", period=m_period,
                               file_path=path, summary=analysis_text(rep, "月度") + f"（{AIGC_NOTE}）",
                               created_by=user.id))
            session.add(AuditLog(user_id=user.id, username=user.username,
                                 action="导出报告", target=f"月度-{m_period}", detail=path))
            session.commit()
            st.success(f"已导出并存档：{path}")

    st.divider()

    # ---------- 年度报告 ----------
    st.subheader("📊 年度总报告")
    years = sorted({(h.created_at.strftime("%Y") if h.created_at else "") for h in
                    session.query(Hazard).all()} | {datetime.now().strftime("%Y")}, reverse=True)
    a_year = st.selectbox("年度", list(years), key="rep_y")
    if st.button("🔄 生成/刷新年度报告", key="gen_y"):
        rep2 = annual_report(session, a_year, org_id)
        st.session_state["rep_y_data"] = rep2
        st.session_state["rep_y_type"] = "年度"

    rep2 = st.session_state.get("rep_y_data")
    if rep2 and st.session_state.get("rep_y_type") == "年度" and rep2.get("year") == a_year:
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            kpi_card("全年隐患", rep2["total"])
        with c2:
            kpi_card("整改完成率", f"{rep2['rect_rate']}%", "#00b894")
        with c3:
            kpi_card("全年扣分", rep2["year_deduct"], "#d63031")
        with c4:
            kpi_card("合规档次", rep2["tier"]["grade"], "#e17055")
        st.markdown(f"**月度趋势**：{' → '.join(f'{k}月:{v}' for k, v in rep2['trend'].items())}")
        st.markdown(f"**高频根因 TOP**：{'、'.join(f'{t}({n})' for t, n in rep2['root_causes'][:5])}")
        st.markdown(f"**分析结论**：{analysis_text(rep2, '年度')}")
        c1, c2, c3 = st.columns(3)
        if c1.download_button("⬇️ 下载 HTML 年度报告", export_html(rep2, "年度"),
                              file_name=f"{org_label(org.name, org.code) if org else '全辖区'}_年度报告_{a_year}.html",
                              mime="text/html"):
            pass
        if c2.download_button("📄 下载 Word 公文（红头）", _read_bytes(export_docx(rep2, "年度")),
                              file_name=f"{org_label(org.name, org.code) if org else '全辖区'}_年度检查报告_{a_year}.docx",
                              mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"):
            pass
        if c3.button("💾 导出 Excel 并存档"):
            path = export_excel(rep2, "年度")
            org_tag = org_label(org.name, org.code) if org else "全辖区"
            session.add(Report(title=f"{org_tag}年度报告 {a_year}", rtype="年度", period=a_year,
                               file_path=path, summary=analysis_text(rep2, "年度") + f"（{AIGC_NOTE}）",
                               created_by=user.id))
            session.add(AuditLog(user_id=user.id, username=user.username,
                                 action="导出报告", target=f"年度-{a_year}", detail=path))
            session.commit()
            st.success(f"已导出并存档：{path}")

    st.divider()

    # ---------- 存档回溯 ----------
    st.subheader("🗄️ 报告存档（可按年份回溯）")
    archive = session.query(Report).order_by(Report.id.desc()).all()
    if not archive:
        st.caption("暂无存档记录")
    for r in archive:
        with st.expander(f"{r.title}（{r.rtype}）· {r.created_at.strftime('%Y-%m-%d')}"):
            st.markdown(f"**摘要**：{r.summary}")
            st.markdown(f"**文件**：{r.file_path}")
            if r.file_path and os.path.exists(r.file_path):
                with open(r.file_path, "rb") as f:
                    st.download_button("⬇️ 下载 Excel", f.read(),
                                       file_name=os.path.basename(r.file_path),
                                       key=f"dl_{r.id}",
                                       mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

