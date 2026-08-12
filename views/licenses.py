# -*- coding: utf-8 -*-
"""机构证照备案 — 民政监管（一级/二级）
营业执照 / 备案凭证 / 消防验收 / 食品经营许可 → 有效期管理 · 到期前 30 天「临期」黄色预警 · 过期红色预警
"""
import pandas as pd
import streamlit as st
from sqlalchemy.orm import Session

from auth import require_role, current_user, visible_org_ids
from models import Organization
from services.licenses import (list_licenses, license_stats, org_license_matrix,
                               LIC_TYPES)
from services.mask import aigc_note
from views.theme import app_header, metric_card, section_title, glass_card

STATUS_META = {
    "有效": ("✅", "#059669", "#ECFDF5"),
    "临期": ("⚠️", "#D97706", "#FFFBEB"),
    "过期": ("🔴", "#DC2626", "#FEF2F2"),
}


def render(session: Session):
    require_role(2)
    user = current_user(session)
    app_header("机构证照备案", "营业执照 · 备案凭证 · 消防验收 · 食品经营许可 · 到期预警")
    st.markdown(aigc_note(), unsafe_allow_html=True)

    vis_org_ids = visible_org_ids(session, user)
    orgs = session.query(Organization).filter(
        Organization.active == True,
        Organization.id.in_(vis_org_ids) if vis_org_ids else True).all()
    scoped = [o.id for o in orgs]

    # ============ 指标总览 ============
    s = license_stats(session, scoped)
    c1, c2, c3, c4, c5 = st.columns(5)
    with c1:
        metric_card("证照总数", s["证照总数"], "在册证照")
    with c2:
        metric_card("有效", s["有效"], "正常在有效期", icon_str="✅")
    with c3:
        metric_card("临期", s["临期"], "30 天内到期", icon_str="⚠️")
    with c4:
        metric_card("过期", s["过期"], "已超出有效期", icon_str="🔴")
    with c5:
        metric_card("预警机构", s["预警机构数"], "存在临期/过期", icon_str="🏛️")

    # 预警横幅
    if s["过期"]:
        st.markdown(f"""
        <div style="background:linear-gradient(135deg,#FEF2F2,#FEE2E2);border-left:6px solid #DC2626;
            border-radius:10px;padding:12px 16px;margin:10px 0;color:#991B1B;">
            🔴 有 <b>{s['过期']}</b> 张证照已过期、<b>{s['临期']}</b> 张临期未换发，
            请督促机构限期补办，逾期不办依法处理！
        </div>""", unsafe_allow_html=True)
    elif s["临期"]:
        st.markdown(f"""
        <div style="background:linear-gradient(135deg,#FFFBEB,#FEF3C7);border-left:6px solid #D97706;
            border-radius:10px;padding:12px 16px;margin:10px 0;color:#92400E;">
            ⚠️ 有 <b>{s['临期']}</b> 张证照将在 30 天内到期，请提醒机构提前换发。
        </div>""", unsafe_allow_html=True)

    # ============ 机构 × 证照矩阵 ============
    section_title("🏛️", "机构证照完备度矩阵", "× 证照类型 · 红=过期 / 黄=临期 / 绿=有效 / 灰=缺失")
    matrix = org_license_matrix(session, scoped)
    if matrix:
        rows_m = []
        for name, lic_map in matrix.items():
            row = {"机构": name}
            for t in LIC_TYPES:
                row[t] = lic_map.get(t, "缺失")
            rows_m.append(row)
        df_m = pd.DataFrame(rows_m)
        st.dataframe(df_m, use_container_width=True, hide_index=True)
    else:
        st.info("暂无证照数据")

    # ============ 明细与到期预警 ============
    st.markdown("<hr style='border-top:1px dashed #CBD5E1;margin:22px 0;'>", unsafe_allow_html=True)
    section_title("📄", "证照明细与到期预警", "按有效期倒序 · 临期/过期置顶预警")
    rows = list_licenses(session, scoped)
    if rows:
        df = pd.DataFrame(rows)
        order = {"过期": 0, "临期": 1, "有效": 2}
        df["_ord"] = df["状态"].map(order)
        df = df.sort_values(["_ord", "有效期至"]).drop(columns=["_ord", "id"])
        # 状态列着色
        st.dataframe(
            df, use_container_width=True, hide_index=True,
            column_config={"状态": st.column_config.TextColumn(
                help="有效=正常 · 临期=30天内到期 · 过期=已超期")})

        # 机构预警清单（按机构聚合）
        section_title("🔔", "机构证照预警清单", "存在临期/过期证照的机构，需督促限期补办")
        warn_rows = [r for r in rows if r["状态"] in ("临期", "过期")]
        if warn_rows:
            by_org = {}
            for r in warn_rows:
                by_org.setdefault(r["机构"], []).append(f"{r['证照类型']}（{r['状态']}，{r['有效期至']}）")
            html = ""
            for name, items in by_org.items():
                badge = "🔴" if any("过期" in i for i in items) else "⚠️"
                html += (f'<div style="padding:8px 0;border-bottom:1px solid #F1F5F9;'
                         f'font-size:14px;"><b>{badge} {name}</b>'
                         f'<span style="color:#64748B;margin-left:10px;">{"；".join(items)}</span></div>')
            glass_card(html)
        else:
            st.success("🎉 当前无临期/过期证照，所有机构证照齐备")
    else:
        st.info("暂无证照数据")

    st.markdown("""
    <div style="border:1px dashed #CBD5E1;border-radius:10px;padding:10px 14px;background:#FAFBFC;margin-top:12px;">
        <b>⚖️ 监管依据</b>：养老机构设立取消许可后实行<b>备案制</b>，备案凭证、消防验收合格证明、
        食品经营许可是民政监管核验的重点证照；证照到期未换发将纳入机构信用评级与考核扣分。
    </div>""", unsafe_allow_html=True)
