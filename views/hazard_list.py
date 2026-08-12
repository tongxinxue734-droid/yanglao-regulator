# -*- coding: utf-8 -*-
"""全周期隐患台账与整改闭环管控大厅"""
import streamlit as st
import pandas as pd
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import or_

from models import Hazard, User, Space, Rectification, Review, AuditLog, Organization
from services.mask import org_label
from auth import current_user, visible_hazard_filter, visible_org_ids
from config import HAZARD_STATUS, HAZARD_STATUS_REV


def fetch_hazards_dataframe(session: Session, user: User, status_filter=None):
    """
    获取满足当前政府监管人员数据权限（按管辖片区机构）的检查问题台账
    """
    vis_org_ids = visible_org_ids(session, user)
    query = session.query(Hazard)
    if vis_org_ids:
        query = query.filter(Hazard.org_id.in_(vis_org_ids))

    if status_filter:
        query = query.filter(Hazard.status.in_(status_filter))

    hazards = query.order_by(Hazard.created_at.desc()).all()

    data = []
    for h in hazards:
        # 计算是否逾期
        is_overdue = False
        overdue_days = 0
        if h.deadline and h.status not in ["closed", "archived"]:
            if datetime.now() > h.deadline:
                is_overdue = True
                overdue_days = (datetime.now() - h.deadline).days

        data.append({
            "id": h.id,
            "所属机构": org_label(h.org.name, h.org.code) if h.org else "-",
            "工单编号": h.code,
            "隐患简述": h.title,
            "风险等级": h.level,
            "当前状态": HAZARD_STATUS.get(h.status, "未知"),
            "上报时间": h.created_at.strftime("%Y-%m-%d %H:%M"),
            "整改期限": h.deadline.strftime("%Y-%m-%d %H:%M") if h.deadline else "无限制",
            "是否逾期": "❌ 逾期" if is_overdue else "✅ 正常",
            "逾期天数": overdue_days,
            "关联指标": h.indicator_code if h.indicator_code else "-",
            "预估扣分": h.deducted,
            "_raw_hazard": h  # 存储原始对象以供操作
        })
    return pd.DataFrame(data)


def render(session: Session):
    user = current_user(session)
    st.markdown("<h3 style='color: #1E293B;'>📋 检查发现问题台账</h3>", unsafe_allow_html=True)

    # 逾期预警推送（本会话首次检测到逾期时触发外部推送）
    vis_org_ids = visible_org_ids(session, user)
    try:
        if not st.session_state.get("_od_pushed"):
            from models import Notification as _N
            overdue_open = session.query(Hazard).filter(
                Hazard.org_id.in_(vis_org_ids) if vis_org_ids else True,
                Hazard.status.in_(["pending_rectify", "rectifying", "pending_review", "rejected"]),
                Hazard.deadline < datetime.now()).count()
            if overdue_open:
                from services.notify import push as push_notify
                ok_w, ok_m = push_notify("逾期预警",
                                         f"辖区共 {overdue_open} 项整改任务已逾期未闭环，请监管人员及时督办。")
                if ok_w or ok_m:
                    session.add(AuditLog(user_id=user.id, username=user.username,
                                         action="逾期预警推送", target="辖区",
                                         detail=f"逾期 {overdue_open} 项，微信/邮件推送完成"))
                    session.commit()
                st.session_state["_od_pushed"] = True
    except Exception:
        pass

    if user.role_level == 1:
        st.caption("全辖区监管视角：可查看并干预辖区所有机构检查发现的问题")
    elif user.role_level == 2:
        st.caption(f"片区监管视角：管辖 - {user.dept_name}（按管辖机构过滤）")
    else:
        st.caption("检查员视角：本人片区机构检查发现的问题与整改跟踪")

    # 按状态分类的 Tabs
    t1, t2, t3 = st.tabs(["🔥 待整改任务", "👀 待复查核验", "📦 已闭环归档"])

    with t1:
        df_pending = fetch_hazards_dataframe(session, user, ["pending_rectify", "rectifying", "rejected"])
        if df_pending.empty:
            st.success("🎉 太棒了！当前没有任何待整改的隐患。")
        else:
            # 突出显示逾期数据
            overdue_count = df_pending[df_pending["是否逾期"] == "❌ 逾期"].shape[0]
            if overdue_count > 0:
                st.error(f"🚨 警告：当前有 {overdue_count} 个整改任务已严重逾期，即将触发升级处罚机制，请立即督办！")

            # 使用可交互的 dataframe
            st.dataframe(df_pending.drop(columns=["id", "_raw_hazard"]), use_container_width=True, hide_index=True)

            st.markdown("#### ⚡ 快速执行整改")
            target_id = st.selectbox("选择要处理的工单编号", df_pending["工单编号"].tolist(), key="sel_rect")

            if target_id:
                # 获取选中的原始对象
                selected_row = df_pending[df_pending["工单编号"] == target_id].iloc[0]
                h: Hazard = selected_row["_raw_hazard"]

                with st.expander(f"展开整改工作台 - {h.title}", expanded=True):
                    st.write(f"**问题描述：** {h.description}")
                    st.write(f"**扣分风险：** 关联指标 {h.indicator_code}，涉及扣除 {h.deducted} 分")

                    with st.form(f"form_rectify_{h.id}"):
                        plan = st.text_area("填写整改措施与结果说明",
                                            placeholder="例如：已清理通道杂物，并对相关人员进行了批评教育...")
                        # 生产环境这里应加入图片上传控件
                        if st.form_submit_button("✅ 提交整改结果，申请复查", type="primary"):
                            if not plan:
                                st.error("必须填写整改说明！")
                            else:
                                # 写入整改记录
                                rect = Rectification(hazard_id=h.id, assignee_id=user.id, plan=plan)
                                session.add(rect)
                                # 更新主表状态
                                h.status = "pending_review"
                                session.add(AuditLog(user_id=user.id, action="提交整改", target=h.code))
                                session.commit()
                                st.success("整改报告已提交，等待上级核验闭环！")
                                st.rerun()

    with t2:
        df_review = fetch_hazards_dataframe(session, user, ["pending_review"])
        if df_review.empty:
            st.info("当前没有等待复查的工单。")
        else:
            st.dataframe(df_review.drop(columns=["id", "_raw_hazard"]), use_container_width=True, hide_index=True)

            # 权限控制：三级人员不能自己复查自己的工单
            if user.role_level == 3:
                st.warning("⚠️ 权限限制：您提交的整改报告正在等待部门主管或安保处核验，您无权直接操作闭环。")
            else:
                st.markdown("#### ⚖️ 主管审核与核验")
                rev_id = st.selectbox("选择要核验的工单", df_review["工单编号"].tolist(), key="sel_rev")
                if rev_id:
                    selected_row = df_review[df_review["工单编号"] == rev_id].iloc[0]
                    h: Hazard = selected_row["_raw_hazard"]

                    # 查找对应的最新整改记录
                    rect = session.query(Rectification).filter(Rectification.hazard_id == h.id).order_by(
                        Rectification.submitted_at.desc()).first()

                    with st.expander("复查核验操作台", expanded=True):
                        st.info(f"**一线执行人反馈：**\n\n{rect.plan if rect else '暂无说明'}")

                        col_a, col_b = st.columns(2)
                        with col_a:
                            if st.button("🟢 审核通过，正式闭环", use_container_width=True, type="primary"):
                                h.status = "closed"
                                h.closed_at = datetime.now()
                                review = Review(hazard_id=h.id, reviewer_id=user.id, result="通过",
                                                comment="现场已核验无误。")
                                session.add(review)
                                session.add(AuditLog(user_id=user.id, action="审核闭环", target=h.code))
                                session.commit()
                                st.success(f"{h.code} 已成功闭环，本次免于扣分惩罚！")
                                st.rerun()
                        with col_b:
                            if st.button("🔴 打回重改，未达标准", use_container_width=True):
                                h.status = "rejected"
                                review = Review(hazard_id=h.id, reviewer_id=user.id, result="不通过",
                                                comment="整改不彻底，要求返工。")
                                session.add(review)
                                session.add(AuditLog(user_id=user.id, action="打回重改", target=h.code))
                                session.commit()
                                st.error("已将该工单打回，责令重新整改。")
                                st.rerun()

    with t3:
        df_closed = fetch_hazards_dataframe(session, user, ["closed", "archived"])
        if df_closed.empty:
            st.write("暂无历史归档记录。")
        else:
            st.dataframe(df_closed.drop(columns=["id", "_raw_hazard"]), use_container_width=True, hide_index=True)
            st.download_button(
                label="📥 导出归档数据 (CSV)",
                data=df_closed.drop(columns=["id", "_raw_hazard"]).to_csv(index=False).encode('utf-8-sig'),
                file_name=f"hazards_archive_{datetime.now().strftime('%Y%m%d')}.csv",
                mime="text/csv"
            )