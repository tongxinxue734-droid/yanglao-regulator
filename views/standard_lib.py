# -*- coding: utf-8 -*-
"""隐患/违规标准库：内置 39 条《养老机构运营违规评价指标》+ 自定义扩展"""
import streamlit as st
from sqlalchemy.orm import Session

import config
from auth import current_user, require_role
from models import Indicator, AuditLog
from views.theme import app_header, metric_card, section_title


def render(session: Session):
    require_role(1)  # 标准库管理：一级专属
    user = current_user(session)

    # ── 页眉 ──
    app_header("检查标准库",
               "内置《养老机构运营违规评价指标》39 条（A 主体资格 / B 设施安全 / C 人员配备 / "
               "D 服务规范 / E 制度管理 / F 资金收费），支持自定义扩展")

    # ── 加载数据 ──
    rows = session.query(Indicator).filter(Indicator.active == True).order_by(Indicator.code).all()
    cats = {}
    for r in rows:
        cats.setdefault(r.category, []).append(r)

    # ── 统计卡片 ──
    builtin_count = sum(1 for r in rows if r.builtin)
    custom_count = sum(1 for r in rows if not r.builtin)

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        metric_card("有效指标", len(rows), f"内置 {builtin_count} 条 + 自定义 {custom_count} 条", icon_str="📚")
    with c2:
        metric_card("分类数量", len(cats), "、".join(list(cats.keys())[:4]), icon_str="📂")
    with c3:
        metric_card("扣分档次", "6 档", "1 / 2 / 3 / 6 / 9 / 12 分", icon_str="⚖️")
    with c4:
        metric_card("停业整顿线", "≥12 分", "重大违规 · 停业整顿", icon_str="🚨")

    # ── 处罚档次速查 ──
    with st.expander("📋 综合扣分处罚档次速查表", expanded=False):
        cols = st.columns(3)
        for i, t in enumerate(config.PUNISHMENT_TIERS):
            with cols[i % 3]:
                severity_color = {
                    "纸面瑕疵": "#94A3B8", "轻微违规": "#F59E0B", "一般违规": "#F59E0B",
                    "较重违规": "#F97316", "严重违规": "#EF4444", "重大违规": "#DC2626"
                }.get(t['grade'], "#64748B")
                st.markdown(f"""
                <div style="background:#fff;border:1px solid #E2E8F0;border-radius:12px;
                    padding:14px 16px;margin-bottom:10px;border-left:4px solid {severity_color};">
                    <div style="font-weight:700;font-size:15px;color:#0F172A;">≥{t['deduct']} 分 · {t['grade']}</div>
                    <div style="color:#64748B;font-size:13px;margin-top:4px;">{t['penalty']}</div>
                </div>
                """, unsafe_allow_html=True)

    st.divider()

    # ── 搜索 + 分类筛选工具栏 ──
    all_categories = list(cats.keys())
    c1, c2 = st.columns([2, 1])
    with c1:
        search = st.text_input("🔍 搜索指标（编号 / 事项 / 违规情形）", placeholder="输入关键词快速定位…", key="std_search")
    with c2:
        cat_filter = st.selectbox("📂 按分类筛选", ["全部类别"] + all_categories, key="std_cat")

    st.divider()

    # ── 渲染指标列表 ──
    shown_count = 0
    for cat, cat_items in cats.items():
        # 分类筛选
        if cat_filter != "全部类别" and cat != cat_filter:
            continue

        # 搜索过滤
        items = cat_items
        if search:
            kw = search.strip().lower()
            items = [r for r in items if
                     kw in r.code.lower() or
                     kw in r.item.lower() or
                     kw in (r.content or "").lower() or
                     kw in (r.law_basis or "").lower()]
        if not items:
            continue
        shown_count += len(items)

        # 分类标题（带统计）
        builtin_in_cat = sum(1 for r in items if r.builtin)
        custom_in_cat = sum(1 for r in items if not r.builtin)
        sub_info = f"{len(items)} 条"
        if builtin_in_cat and custom_in_cat:
            sub_info += f"（内置 {builtin_in_cat} + 自定义 {custom_in_cat}）"
        section_title("📌", cat, sub_info)

        for r in items:
            # 扣分严重程度颜色
            severity_color = {
                1: "#94A3B8", 2: "#F59E0B", 3: "#F59E0B",
                6: "#F97316", 9: "#EF4444", 12: "#DC2626"
            }.get(r.deduct, "#64748B")

            # 内置 / 自定义标签
            tag_html = ""
            if r.builtin:
                tag_html = '<span style="background:#DBEAFE;color:#1E40AF;padding:2px 8px;border-radius:6px;font-size:11px;margin-left:6px;">内置</span>'
            else:
                tag_html = '<span style="background:#FEF3C7;color:#92400E;padding:2px 8px;border-radius:6px;font-size:11px;margin-left:6px;">自定义</span>'

            # 备注标签（如 ★停业整改）
            remark_html = ""
            if r.remark:
                remark_html = f'<span style="background:#FEE2E2;color:#991B1B;padding:2px 8px;border-radius:6px;font-size:11px;margin-left:4px;">{r.remark}</span>'

            expander_label = (f"{r.code}  {r.item}  ·  扣 {r.deduct} 分")

            with st.expander(expander_label):
                # 标题行（HTML 块内不能有空行，否则 markdown 截断导致裸标签显示）
                st.markdown(f"""
                <div style="display:flex;align-items:center;gap:8px;margin-bottom:12px;flex-wrap:wrap;">
                    <span style="font-weight:700;font-size:16px;color:#0F172A;">{r.code} {r.item}</span>{tag_html}{remark_html}
                    <span style="background:{severity_color};color:#fff;padding:2px 10px;border-radius:10px;font-size:12px;font-weight:600;">扣 {r.deduct} 分</span>
                </div>
                """, unsafe_allow_html=True)

                # 违规情形
                st.markdown(f"""
                <div style="background:#F8FAFC;border:1px solid #E2E8F0;border-radius:10px;padding:14px 16px;margin-bottom:10px;">
                    <div style="color:#64748B;font-size:12px;font-weight:600;margin-bottom:4px;">📝 违规情形</div>
                    <div style="color:#0F172A;font-size:15px;line-height:1.6;">{r.content}</div>
                </div>
                """, unsafe_allow_html=True)

                # 法规依据
                st.markdown(f"""
                <div style="background:#FFF7ED;border:1px solid #FED7AA;border-radius:10px;padding:14px 16px;margin-bottom:10px;">
                    <div style="color:#9A3412;font-size:12px;font-weight:600;margin-bottom:4px;">⚖️ 法规依据</div>
                    <div style="color:#431407;font-size:14px;">{r.law_basis or '—'}</div>
                </div>
                """, unsafe_allow_html=True)

                # 自定义指标：操作按钮
                if user.role_level == 1 and not r.builtin:
                    c1, c2 = st.columns([1, 4])
                    with c1:
                        if st.button(f"🗑️ 停用 {r.code}", key=f"stop_{r.id}", use_container_width=True):
                            r.active = False
                            session.add(AuditLog(user_id=user.id, username=user.username,
                                                 action="停用指标", target=r.code))
                            session.commit()
                            st.success(f"已停用指标 {r.code}")
                            st.rerun()

    # 无结果提示
    if not shown_count:
        if search and cat_filter != "全部类别":
            st.info(f"「{cat_filter}」分类中未找到匹配「{search}」的指标")
        elif search:
            st.info(f"未找到匹配「{search}」的指标，请尝试其他关键词")
        elif cat_filter != "全部类别":
            st.info(f"「{cat_filter}」分类下暂无指标")

    st.divider()

    # ── 新增自定义指标 ──
    if user.role_level == 1:
        with st.expander("➕ 新增自定义指标", expanded=False):
            with st.form("add_ind"):
                st.markdown("**填写以下信息新增一条自定义检查指标**")
                c1, c2, c3 = st.columns(3)
                with c1:
                    code = st.text_input("编号", placeholder="如 G1", key="add_code")
                with c2:
                    category = st.text_input("类别", placeholder="如 自定义", key="add_cat")
                with c3:
                    deduct = st.selectbox("扣分", [1, 2, 3, 6, 9, 12], key="add_deduct")

                item = st.text_input("事项名称", placeholder="如 消防安全通道堵塞", key="add_item")
                content = st.text_area("违规情形描述", placeholder="详细描述该指标对应的违规情形…", key="add_content")
                c1, c2 = st.columns(2)
                with c1:
                    basis = st.text_input("法规依据（可空）", placeholder="如《消防法》第 XX 条", key="add_basis")
                with c2:
                    remark = st.text_input("备注（可空）", placeholder="如 ★重点检查项", key="add_remark")

                submitted = st.form_submit_button("💾 保存指标", use_container_width=True)
                if submitted:
                    if not code.strip() or not item.strip() or not content.strip():
                        st.error("编号、事项名称、违规情形描述为必填项")
                    elif session.query(Indicator).filter(Indicator.code == code.strip()).first():
                        st.error(f"编号 {code.strip()} 已存在，请使用其他编号")
                    else:
                        session.add(Indicator(
                            code=code.strip(), category=category.strip() or "自定义",
                            item=item.strip(), content=content.strip(),
                            law_basis=basis.strip(), remark=remark.strip(),
                            deduct=deduct, builtin=False
                        ))
                        session.add(AuditLog(user_id=user.id, username=user.username,
                                             action="新增指标", target=code.strip(),
                                             detail=f"{category}-{item}，扣 {deduct} 分"))
                        session.commit()
                        st.success(f"指标 {code.strip()} 已保存")
                        st.rerun()
