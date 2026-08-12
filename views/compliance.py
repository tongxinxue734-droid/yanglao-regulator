# -*- coding: utf-8 -*-
"""检查评分：按 39 条违规指标逐项月度检查打分（A-F 六类分组版）"""
from datetime import datetime, timedelta

import streamlit as st
from sqlalchemy.orm import Session

import config
from auth import current_user, visible_org_ids
from models import Indicator, ComplianceScore, AuditLog, ViolationRecord, Organization, Hazard
from services.mask import org_label
from views.common import kpi_card


def render(session: Session):
    user = current_user(session)
    st.markdown("""
        <div style='margin-bottom: 24px;'>
            <h2 style='color: #0F172A; font-weight: 800; margin: 0;'>🎯 机构合规考核与检查评分体系</h2>
            <p style='color: #64748B; font-size: 14px; margin-top: 4px;'>
                严格对照《养老机构运营违规评价指标》39 项要求逐项打分，机构得分 = 100 − 当月扣分。
            </p>
        </div>
    """, unsafe_allow_html=True)

    c_filter1, c_filter2 = st.columns(2)
    vis_org_ids = visible_org_ids(session, user)
    orgs = session.query(Organization).filter(
        Organization.active == True,
        Organization.id.in_(vis_org_ids) if vis_org_ids else True).all()

    with c_filter1:
        if orgs:
            org_opts = {org_label(o.name, o.code): o for o in orgs}
            org_sel = st.selectbox("🎯 检查对象机构", list(org_opts.keys()), key="comp_org")
            org_id = org_opts[org_sel].id
        else:
            org_id = None
            st.error("管辖范围内暂无可检查机构")

    with c_filter2:
        cur = datetime.now().strftime("%Y-%m")
        periods = sorted({c.period for c in session.query(ComplianceScore).all()} | {cur}, reverse=True)
        period = st.selectbox("📅 考核期间", periods, key="comp_period")

    st.markdown("<hr style='border: 1px solid #E2E8F0; margin: 20px 0;'>", unsafe_allow_html=True)

    if org_id is None:
        st.warning("请先选择检查机构")
        return

    # 指标概览（机构得分）
    from services.scoring import compliance_score
    cs = compliance_score(period, session, org_id)
    c1, c2, c3, c4 = st.columns(4)
    kpi_card("综合得分", f"{cs['score']} 分", "#1f6feb", f"100 − 扣 {cs['deducted']} 分")
    kpi_card("累计扣分", cs["deducted"], "#d63031", f"{cs['violations']} 条违规记录")
    kpi_card("处罚档次", cs["tier"]["grade"], "#e17055", cs["tier"]["penalty"])

    st.subheader(f"📝 {period} 详细评价指标审核表")
    st.caption("请逐项核实。勾选【发现违规】系统将自动按标准扣减对应分数，并可关联要求限期整改。")

    indicators = session.query(Indicator).filter(Indicator.active == True).order_by(Indicator.code).all()

    # 获取当前机构、当前期间已保存的分数
    saved_scores = session.query(ComplianceScore).filter(
        ComplianceScore.period == period,
        ComplianceScore.org_id == org_id).all()
    saved_map = {sc.indicator_code: sc for sc in saved_scores}

    # 按 A-F 六类分组展示（expander 分组，保证 form 提交正常）
    groups = {
        "A 类：主体资格": [i for i in indicators if i.code.startswith("A")],
        "B 类：设施安全": [i for i in indicators if i.code.startswith("B")],
        "C 类：人员配备": [i for i in indicators if i.code.startswith("C")],
        "D 类：服务规范": [i for i in indicators if i.code.startswith("D")],
        "E 类：制度管理": [i for i in indicators if i.code.startswith("E")],
        "F 类：资金收费": [i for i in indicators if i.code.startswith("F")],
    }

    with st.form("massive_compliance_form"):
        for group_name, group_inds in groups.items():
            with st.expander(f"{group_name}（{len(group_inds)} 项）", expanded=False):
                for ind in group_inds:
                    st.markdown(
                        f"<div style='background-color:#F8FAFC; padding:14px; border-radius:8px; "
                        f"margin-bottom:10px; border-left: 4px solid #3B82F6;'>",
                        unsafe_allow_html=True)
                    c_title, c_score = st.columns([4, 1])
                    c_title.markdown(f"**[{ind.code}] {ind.item}**")
                    c_score.markdown(
                        f"<span style='color:#EF4444; font-weight:bold;'>扣 {ind.deduct} 分</span>",
                        unsafe_allow_html=True)
                    st.markdown(
                        f"<div style='font-size:13px; color:#64748B; margin-bottom: 10px;'>{ind.content}</div>",
                        unsafe_allow_html=True)

                    existed = saved_map.get(ind.code)
                    default_found = existed.found if existed else False
                    default_comment = existed.comment if existed else ""

                    c_chk, c_cmnt = st.columns([1, 4])
                    found = c_chk.checkbox("⚠️ 发现违规", value=default_found, key=f"chk_{ind.code}")
                    comment = c_cmnt.text_input("整改要求 / 现场备注", value=default_comment,
                                                key=f"cmt_{ind.code}", placeholder="若违规，请简述现场情况...")
                    st.markdown("</div>", unsafe_allow_html=True)

        submit_btn = st.form_submit_button("💾 汇总保存本期考核评分结果", type="primary",
                                           use_container_width=True)

        if submit_btn:
            n_found = 0
            total_deduct_now = 0
            for ind in indicators:
                found = st.session_state.get(f"chk_{ind.code}", False)
                comment = st.session_state.get(f"cmt_{ind.code}", "")
                existed = saved_map.get(ind.code)
                deduct_val = ind.deduct if found else 0

                if existed:
                    existed.found = found
                    existed.deducted = deduct_val
                    existed.comment = comment
                    existed.checked_by = user.id
                else:
                    session.add(ComplianceScore(
                        indicator_code=ind.code, period=period, org_id=org_id,
                        checked_by=user.id, found=found, deducted=deduct_val, comment=comment))

                if found:
                    n_found += 1
                    total_deduct_now += deduct_val
                    # 同步违规扣分记录（机构月度扣分依据）
                    vr = session.query(ViolationRecord).filter(
                        ViolationRecord.indicator_code == ind.code,
                        ViolationRecord.period == period,
                        ViolationRecord.org_id == org_id,
                        ViolationRecord.source == "人工检查").first()
                    if not vr:
                        session.add(ViolationRecord(indicator_code=ind.code, period=period,
                                                    org_id=org_id, found_by=user.id,
                                                    deducted=deduct_val, source="人工检查"))
                    # 自动生成整改任务（进入整改闭环：发现问题→机构整改→政府复查）
                    existing = session.query(Hazard).filter(
                        Hazard.indicator_code == ind.code,
                        Hazard.org_id == org_id,
                        Hazard.source == "检查评分",
                        Hazard.status.in_(["pending_rectify", "rectifying", "pending_review", "rejected"])).first()
                    if not existing:
                        lvl = ("红色" if deduct_val >= 12 else "橙色" if deduct_val >= 6
                               else "黄色" if deduct_val >= 3 else "蓝色")
                        session.add(Hazard(
                            code=f"HZ-{datetime.now().strftime('%Y%m%d%H%M%S')}-{ind.code}",
                            category=ind.category, hazard_type=ind.item,
                            title=f"[检查评分] {ind.category}-{ind.item}",
                            description=comment or ind.content[:200],
                            level=lvl, source="检查评分", indicator_code=ind.code,
                            deducted=deduct_val, org_id=org_id, reporter_id=user.id,
                            status="pending_rectify",
                            deadline=datetime.now() + timedelta(days=config.HAZARD_LEVELS.get(lvl, {}).get("days", 7))))

            session.add(AuditLog(user_id=user.id, username=user.username,
                                 action="更新综合打分", target=f"{org_id}-{period}",
                                 detail=f"发现 {n_found} 项违规，预估扣除 {total_deduct_now} 分"))
            session.commit()
            # 重大违规预警推送（触发停业整顿档）
            try:
                if n_found > 0:
                    from services.notify import push as push_notify
                    org_obj = session.query(Organization).get(org_id)
                    level_note = "（含停业整顿级重大违规）" if total_deduct_now >= 12 else ""
                    push_notify("检查结果", f"{org_label(org_obj.name, org_obj.code) if org_obj else '辖区'} {period} 检查发现 "
                                            f"{n_found} 项违规，共扣 {total_deduct_now} 分{level_note}。")
            except Exception:
                pass
            st.success(f"✅ 考核数据保存成功！本期共检出 {n_found} 项违规，累计扣分 {total_deduct_now} 分。")
            st.rerun()

    st.divider()
    st.subheader(f"{period} 该机构已扣分指标明细")
    hits = session.query(ComplianceScore).filter(
        ComplianceScore.period == period, ComplianceScore.org_id == org_id,
        ComplianceScore.found == True).all()
    if not hits:
        st.caption("本期无违规扣分记录")
    for cs_row in hits:
        ind = session.query(Indicator).filter(Indicator.code == cs_row.indicator_code).first()
        st.markdown(f"- **{cs_row.indicator_code}** {ind.item if ind else ''}　扣 **{cs_row.deducted}** 分"
                    f"　备注：{cs_row.comment or '—'}")
