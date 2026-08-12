# -*- coding: utf-8 -*-
"""投诉举报受理 — 政府监管职能模块
12345 转办 / 来信 / 来电 / 网络 → 登记 → 派单核查 → 处理反馈 → 归档（含不予受理）；
红色重大投诉可一键转隐患立案（关联 Hazard，纳入整改闭环与机构考核扣分）。
投诉人信息脱敏（姓氏+称谓/匿名 · 电话打码），机构为监管对象（公开信息不脱敏）。
"""
from datetime import datetime

import pandas as pd
import streamlit as st
from sqlalchemy.orm import Session

from auth import require_role, current_user, visible_org_ids, visible_user_ids
from models import Organization, Hazard, User
from services.complaints import (register, assign, close, reject, archive,
                                 list_complaints, complaint_stats)
from services.mask import aigc_note, org_label, staff_mask
from views.theme import app_header, metric_card, section_title, level_badge

# 状态流转与 SLA
STATUS_FLOW = ["待受理", "核查中", "已办结", "不予受理", "已归档"]
SOURCES = ["12345转办", "来信", "来电", "网络"]
CATEGORIES = ["服务质量", "收费问题", "安全隐患", "虐待老人", "其他"]
LEVELS = ["红色", "橙色", "黄色", "蓝色"]
SLA_DAYS = {"红色": 3, "橙色": 7, "黄色": 15, "蓝色": 30}
LEVEL_COLOR = {"红色": "#EF4444", "橙色": "#F59E0B", "黄色": "#EAB308", "蓝色": "#38BDF8"}
STATUS_COLOR = {"待受理": "#64748B", "核查中": "#2563EB",
                "已办结": "#059669", "不予受理": "#94A3B8", "已归档": "#94A3B8"}


def _org_map(session: Session):
    return {o.id: o for o in session.query(Organization).all()}


def _user_map(session: Session):
    return {u.id: u for u in session.query(User).filter(User.active == True).all()}


def _flow(session: Session, c, user) -> None:
    """逐件状态流转：待受理→派单 / 核查中→办结或不予受理 / 已办结→归档"""
    users = _user_map(session)
    # ---- 待受理：派单核查 ----
    if c.status == "待受理":
        assignees = [u for u in users.values() if u.role_level == 3]
        if not assignees:
            st.info("无可用检查员账号，请先在一级账号下建立三级账号")
            return
        opts = {f"{staff_mask(u.name)}（{u.dept_name}）": u for u in assignees}
        sel = st.selectbox("👤 选择承办检查员", list(opts.keys()), key=f"asg_{c.id}")
        if st.button("📨 派单核查", key=f"btn_asg_{c.id}"):
            assign(session, c, opts[sel].id, user=user)
            st.success(f"已派单给 {staff_mask(opts[sel].name)}，进入核查流程")
            st.rerun()
        if st.button("🚫 不予受理", key=f"btn_rej_{c.id}"):
            reject(session, c, "经初步审查，不属于民政部门职责范围，已建议转交相关部门处理", user=user)
            st.success("已登记为不予受理")
            st.rerun()
    # ---- 核查中：办结 / 转隐患立案 ----
    elif c.status == "核查中":
        result = st.text_area("📝 处理结果（核查结论 / 处置措施 / 回复投诉人情况）",
                              key=f"res_{c.id}", height=110)
        b1, b2 = st.columns(2)
        with b1:
            if st.button("✅ 提交结果并办结", key=f"btn_close_{c.id}"):
                if not result.strip():
                    st.warning("请填写处理结果后再办结")
                else:
                    close(session, c, result.strip(), user=user)
                    st.success("投诉已办结")
                    st.rerun()
        with b2:
            if st.button("🔗 转隐患立案（纳入整改闭环）", key=f"btn_hz_{c.id}"):
                if not c.hazard_id:
                    hz = Hazard(
                        code=f"HB-2026-{len(session.query(Hazard).all()) + 1:04d}",
                        org_id=c.org_id, category="其他", hazard_type=c.category,
                        title=f"[投诉转办] {c.title}", description=c.content,
                        level=c.level if c.level in ("红色", "橙色", "黄色") else "黄色",
                        source="投诉举报", reporter_id=user.id, status="pending_rectify",
                        assignee_id=c.assignee_id,
                        indicator_code="B3" if c.category == "安全隐患" else None,
                    )
                    session.add(hz)
                    session.flush()
                    c.hazard_id = hz.id
                    session.commit()
                    st.success(f"已转隐患立案（{hz.code}），可在问题台账跟踪整改")
                    st.rerun()
                else:
                    st.info("该投诉已关联隐患立案，无需重复操作")
    # ---- 已办结：归档 ----
    elif c.status == "已办结":
        if st.button("🗄️ 归档", key=f"btn_arch_{c.id}"):
            archive(session, c, user=user)
            st.success("已归档")
            st.rerun()


def render(session: Session):
    require_role(2)
    user = current_user(session)
    app_header("投诉举报受理", "12345 转办 · 来信来电 · 网络留言 —— 登记、派单、反馈、归档全流程留痕审计")
    st.markdown(aigc_note(), unsafe_allow_html=True)

    orgs = _org_map(session)
    users = _user_map(session)
    vis_org_ids = visible_org_ids(session, user)
    comps = list_complaints(session, vis_org_ids or None)

    # ============ 指标卡 ============
    s = complaint_stats(session, vis_org_ids or None)
    c1, c2, c3, c4, c5 = st.columns(5)
    with c1:
        metric_card("总件数", s["总件数"], "全部投诉")
    with c2:
        metric_card("待受理", s["待受理"], "需派单", icon_str="📥")
    with c3:
        metric_card("核查中", s["核查中"], "已派单跟踪", icon_str="🔍")
    with c4:
        metric_card("红色紧急", s["红色紧急"], "须 3 日内办结", icon_str="🚨")
    with c5:
        metric_card("本月新增", s["本月新增"], "当月受理", icon_str="🆕")

    # ============ 新增登记 ============
    section_title("📝", "登记新投诉", "受理渠道登记 → 自动生成编号 TS-YYYY-XXXX · 投诉人脱敏")
    with st.expander("＋ 新建投诉受理单", expanded=False):
        with st.form("complaint_form"):
            fc1, fc2, fc3 = st.columns(3)
            with fc1:
                src = st.selectbox("受理渠道", SOURCES)
                cat = st.selectbox("投诉类别", CATEGORIES)
            with fc2:
                lvl = st.selectbox("风险等级", LEVELS,
                                   help="红色=虐待/重大安全/群体事件，须 3 日内办结；橙色=较重，7 日；黄色=一般，15 日")
                org_sel = st.selectbox("被投诉机构", [org_label(o.name, o.code) for o in orgs.values()]
                                       if orgs else ["（无机构数据）"])
            with fc3:
                cname = st.text_input("投诉人（脱敏存姓氏）", placeholder="如：张 或 匿名")
                cphone = st.text_input("联系电话（打码存）", placeholder="如：13912345678")
            title = st.text_input("投诉标题 *", placeholder="一句话概括投诉事项")
            content = st.text_area("投诉内容 *", height=100,
                                   placeholder="详细描述：时间、地点、经过、诉求……")
            submitted = st.form_submit_button("🚀 提交受理")
        if submitted:
            if not title.strip() or not content.strip():
                st.warning("请填写投诉标题与内容")
            else:
                o = next((o for o in orgs.values() if org_label(o.name, o.code) == org_sel), None)
                nm = (cname.strip()[:1] + "*") if cname.strip() else "匿名"
                ph = (cphone.strip()[:3] + "****" + cphone.strip()[-4:]) if len(cphone.strip()) >= 7 else cphone.strip()
                c = register(session, org_id=o.id if o else None, source=src, title=title.strip(),
                             content=content.strip(), complainant=nm, phone=ph,
                             level=lvl, user=user)
                c.category = cat
                session.commit()
                st.success(f"投诉已受理，编号 {c.code}（{nm} · {ph}），状态：待受理")
                st.rerun()

    # ============ 台账列表 ============
    st.markdown("<hr style='border-top:1px dashed #CBD5E1;margin:20px 0;'>", unsafe_allow_html=True)
    section_title("📋", "投诉台账", "按状态/等级筛选 · 超期未办结红色高亮")
    f1, f2, f3 = st.columns([1, 1.2, 1.6])
    with f1:
        st_status = st.multiselect("状态", STATUS_FLOW, default=STATUS_FLOW)
    with f2:
        st_lvl = st.multiselect("风险等级", LEVELS, default=LEVELS)
    with f3:
        kw = st.text_input("🔍 搜索编号 / 标题 / 机构", placeholder="如：TS-2026-0001、押金")

    rows = []
    for c in comps:
        if c.status not in st_status or c.level not in st_lvl:
            continue
        if kw and kw.strip() and kw.strip() not in c.code and kw.strip() not in c.title:
            continue
        o = orgs.get(c.org_id)
        u = users.get(c.assignee_id) if c.assignee_id else None
        overdue = (c.status in ("待受理", "核查中")
                   and (datetime.now() - c.created_at).days >= SLA_DAYS.get(c.level, 15))
        rows.append({
            "编号": c.code,
            "受理时间": c.created_at.strftime("%m-%d %H:%M"),
            "渠道": c.source,
            "机构": org_label(o.name, o.code) if o else "—",
            "标题": c.title,
            "类别": c.category,
            "风险": c.level,
            "状态": c.status,
            "超期": "🔴 超期" if overdue else "",
            "承办人": staff_mask(u.name) if u else "—",
            "投诉人": c.complainant,
        })
    if rows:
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
    else:
        st.info("当前筛选条件下无投诉记录")

    # ============ 逐件处理 ============
    st.markdown("<hr style='border-top:1px dashed #CBD5E1;margin:20px 0;'>", unsafe_allow_html=True)
    section_title("⚙️", "逐件处理", "查看详情并流转：派单 → 反馈办结 → 归档")
    pending = [c for c in comps if c.status in ("待受理", "核查中", "已办结")]
    if not pending:
        st.success("✅ 当前无待处理投诉，全部已归档")
        return
    sel_code = st.selectbox("选择投诉单", [f"{c.code} · {c.title}" for c in pending], key="pick_complaint")
    c = next(c for c in pending if f"{c.code} · {c.title}" == sel_code)
    o = orgs.get(c.org_id)
    u = users.get(c.assignee_id) if c.assignee_id else None

    st.markdown(f"""
    <div style="border:1px solid #E2E8F0;border-radius:14px;padding:1rem 1.2rem;background:white;margin:10px 0;">
        <div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:8px;">
            <b style="font-size:1.05rem;color:#0F172A;">{c.title}</b>
            <span>{level_badge(c.level)}</span>
        </div>
        <div style="margin-top:10px;color:#475569;font-size:14px;display:flex;flex-wrap:wrap;gap:6px 22px;">
            <span>🏛️ {org_label(o.name, o.code) if o else '—'}</span>
            <span>📡 渠道：{c.source}</span>
            <span>🗂️ 类别：{c.category}</span>
            <span>📅 受理：{c.created_at.strftime('%Y-%m-%d %H:%M')}</span>
            <span>👤 投诉人：{c.complainant} · {c.phone}</span>
            <span>🧑‍💼 承办：{staff_mask(u.name) if u else '未派单'}</span>
            <span>状态：{c.status}</span>
        </div>
        <div style="margin-top:10px;background:#F8FAFC;border-radius:8px;padding:10px 14px;color:#334155;font-size:14px;">
            {c.content}
        </div>
        {'<div style="margin-top:10px;color:#065F46;background:#ECFDF5;border-radius:8px;padding:10px 14px;font-size:14px;">✅ 处理结果：' + c.result + '</div>' if c.result else ''}
        {'<div style="margin-top:8px;color:#1D4ED8;font-size:13px;">🔗 已关联隐患立案（' + str(c.hazard_id) + '），可在问题台账跟踪整改</div>' if c.hazard_id else ''}
    </div>
    """, unsafe_allow_html=True)

    _flow(session, c, user)
