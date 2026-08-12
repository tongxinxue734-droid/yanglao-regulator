# -*- coding: utf-8 -*-
"""长者能力评估与动态排班配比雷达 — 模块三（政府监管视角）
《老年人能力综合评估》电子量表 · 机构老人档案（脱敏） · 排班护患比校验（失能区 <1:3 拒绝保存 · C1/D3）

定位说明：本页面面向【政府监管人员】（一级·市民政局领导）——
按机构查看能力评估开展情况、在院老人结构（脱敏）与护患比配比，作为监管考核依据；
机构内部的排班操作由机构端自行完成，本页面只做监管校验与展示。
"""
import random
from datetime import datetime

import pandas as pd
import streamlit as st
from sqlalchemy.orm import Session

from auth import require_role, current_user, visible_org_ids
from models import Organization, Elderly
from services.mask import age_band, staff_mask, aigc_note, org_label, mask_phone, mask_id
from views.theme import app_header, metric_card, section_title

# 能力等级
LEVELS = ["自理", "轻度失能", "中度失能", "重度失能"]
# 护患比警戒线（护士/护工 : 老人）
RATIO_ALERT = {"重度失能": (1, 3), "中度失能": (1, 6), "轻度失能": (1, 10), "自理": (1, 15)}
ZONE_OF_LEVEL = {"自理": "自理区", "轻度失能": "轻度失能区", "中度失能": "中度失能区", "重度失能": "重度失能区"}


def _roster_sim(org_id: int, session: Session):
    """基于机构实际在院老人数计算各区域排班配比（护工数按监管口径模拟）"""
    rnd = random.Random(202 + org_id)
    rows = []
    for lvl in LEVELS:
        elders = session.query(Elderly).filter(
            Elderly.org_id == org_id, Elderly.health_level == lvl,
            Elderly.status == "在院").count()
        if elders == 0:
            continue
        staff = max(1, rnd.randint(1, max(2, elders // 10)))  # 模拟在班护工
        ratio = elders / staff
        lim = RATIO_ALERT[lvl][1]
        ok = ratio <= lim
        rows.append({
            "区域": ZONE_OF_LEVEL[lvl], "在班护工": staff, "在住老人": elders,
            "实际配比": f"1:{round(ratio, 1)}",
            "警戒线": f"1:{lim}",
            "校验": "✅ 通过" if ok else "🔴 低于警戒线，已拒绝保存",
            "ok": ok,
        })
    return rows


def render(session: Session):
    require_role(1)
    user = current_user(session)
    app_header("长者能力评估 · 排班配比雷达",
               "监管视角：全市养老机构能力评估开展情况 · 机构老人档案（脱敏）· 护患比强制校验（C1 人员配备不足）")
    st.markdown(aigc_note(), unsafe_allow_html=True)

    # ============ 机构选择与详情（机构名称不再脱敏） ============
    vis_org_ids = visible_org_ids(session, user)
    orgs = session.query(Organization).filter(
        Organization.active == True,
        Organization.id.in_(vis_org_ids) if vis_org_ids else True).all()
    if not orgs:
        st.warning("暂无机构数据，请先初始化演示数据")
        return

    sel_label = st.selectbox("🏛️ 选择养老机构查看评估与在院老人详情",
                             [org_label(o.name, o.code) for o in orgs], key="assess_org")
    org = next(o for o in orgs if org_label(o.name, o.code) == sel_label)

    # 机构详情卡
    st.markdown(f"""
    <div class="lg-card-hover" style="background:white;border:1px solid #E2E8F0;border-radius:16px;
        padding:1.1rem 1.3rem;box-shadow:0 4px 16px rgba(15,23,42,0.05);margin-bottom:1rem;">
        <div style="display:flex;flex-wrap:wrap;gap:10px 32px;align-items:center;">
            <div><b style="font-size:1.2rem;color:#0F172A;">{org.name}</b>
                <span style="color:#94A3B8;font-size:14px;">（{org.code}）</span></div>
            <div style="color:#475569;font-size:14px;">⭐ {org.level} · {org.org_type}</div>
            <div style="color:#475569;font-size:14px;">🛏️ 核定床位 <b>{org.capacity}</b> 床</div>
            <div style="color:#475569;font-size:14px;">📍 {org.address}</div>
            <div style="color:#475569;font-size:14px;">👤 {org.legal_person} · {org.manager_name}</div>
            <div style="color:#475569;font-size:14px;">📞 {org.phone}</div>
            <div style="color:#475569;font-size:14px;">📄 {org.license_status}</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    elders = session.query(Elderly).filter(
        Elderly.org_id == org.id, Elderly.status == "在院").all()
    n_valid = sum(1 for e in elders if e.assessment_valid)
    roster = _roster_sim(org.id, session)
    n_alert = sum(1 for r in roster if not r["ok"])

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        metric_card("在院老人", len(elders), f"占核定床位 {round(len(elders) / max(org.capacity, 1) * 100)}%")
    with c2:
        metric_card("评估有效", n_valid, "6 个月内有效")
    with c3:
        metric_card("排班区域", len(roster), "按能力等级分区")
    with c4:
        metric_card("配比报警", n_alert, "低于警戒线", icon_str="🔴")

    # ============ 所属机构老人档案（脱敏） ============
    section_title("👴", f"{org.name} 在院老人档案",
                  "老人信息已脱敏：姓名仅姓氏+称谓 · 年龄范围化 · 手机/身份证打码 · 家属打码")
    f_c1, f_c2, f_c3 = st.columns([1.2, 1.2, 2])
    with f_c1:
        sel_levels = st.multiselect("按能力等级筛选", LEVELS, default=LEVELS, key="assess_lvl")
    with f_c2:
        sel_status = st.multiselect("按评估状态筛选", ["有效", "即将到期"], default=["有效", "即将到期"], key="assess_st")
    with f_c3:
        keyword = st.text_input("🔍 搜索（编号 / 房间 / 姓名）", placeholder="如：一号楼、101、张", key="assess_kw")

    rows = []
    for e in elders:
        if e.health_level not in sel_levels:
            continue
        valid = e.assessment_valid
        if valid and "有效" not in sel_status:
            continue
        if not valid and "即将到期" not in sel_status:
            continue
        if keyword:
            kw = keyword.strip()
            if kw and kw not in e.code and kw not in e.room and kw not in e.name:
                continue
        rows.append({
            "院内编号": e.code,
            "老人": e.name,
            "性别": e.gender,
            "年龄": age_band(e.age),
            "能力等级": e.health_level,
            "房间": e.room,
            "手机": mask_phone(e.phone),
            "身份证": mask_id(e.id_card),
            "家属": e.guardian,
            "入住日期": e.admitted_at,
            "最近评估": e.assessed_at,
            "评估状态": "✅ 有效" if valid else "⚠️ 即将到期",
        })
    if rows:
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True,
                     column_config={"身份证": st.column_config.TextColumn(width="small")})
        st.caption(f"共显示 {len(rows)} 位在院老人（全机构 {len(elders)} 位）· 演示数据为模拟样本，个人信息已脱敏")
    else:
        st.info("当前筛选条件下暂无老人记录")

    # ============ 能力评估 ============
    st.markdown("<hr style='border-top:1px dashed #CBD5E1;margin:24px 0;'>", unsafe_allow_html=True)
    section_title("📋", "《老年人能力综合评估》电子量表", "对应 D3 指标 · 评估结果决定护理等级与收费档次（按机构抽查展示）")
    evaluators = ["赵文静", "钱丽华", "孙明", "李慧敏", "周志强", "吴丽"]
    df_a = pd.DataFrame([{
        "院内编号": e.code,
        "长者": e.name,
        "年龄": age_band(e.age),
        "能力等级": e.health_level,
        "评估日期": e.assessed_at,
        "评估人": staff_mask(random.Random(e.id).choice(evaluators)),
        "评估有效期": "✅ 有效" if e.assessment_valid else "⚠️ 即将到期",
    } for e in elders[:30]])
    st.dataframe(df_a, use_container_width=True, hide_index=True)

    # ============ 评估备案（MZ/T 039 四维量表 · 留痕供补贴依据） ============
    st.markdown("<hr style='border-top:1px dashed #CBD5E1;margin:24px 0;'>", unsafe_allow_html=True)
    section_title("🗂️", "能力评估备案", "MZ/T 039 四维量表（生活自理/认知/情绪行为/视听觉）· 备案留痕 · 护理补贴与护患比依据")
    from services.assessment import assess, list_records, assessment_stats, MAX_SCORES, VALID_MONTHS
    st.markdown(f"""
    <div style="border:1px dashed #CBD5E1;border-radius:10px;padding:12px 16px;background:#FAFBFC;margin-bottom:12px;">
        <span style="font-size:14px;color:#475569;">
        📐 量表满分：生活自理 40 + 认知 16 + 情绪行为 8 + 视听觉 8 = <b>72 分</b> ·
        等级映射：&gt;60 自理 / 41-60 轻度失能 / 21-40 中度失能 / ≤20 重度失能 ·
        评估有效期 {VALID_MONTHS} 个月，超期未复评不得作为补贴发放依据
        </span>
    </div>""", unsafe_allow_html=True)

    # 备案统计（全辖区）
    a_stats = assessment_stats(session, vis_org_ids)
    ac1, ac2, ac3, ac4, ac5, ac6 = st.columns(6)
    with ac1:
        metric_card("备案总数", a_stats["备案总数"], "留痕在册")
    with ac2:
        metric_card("自理", a_stats["自理"], ">60 分", icon_str="🟢")
    with ac3:
        metric_card("轻度失能", a_stats["轻度失能"], "41-60 分", icon_str="🟡")
    with ac4:
        metric_card("中度失能", a_stats["中度失能"], "21-40 分", icon_str="🟠")
    with ac5:
        metric_card("重度失能", a_stats["重度失能"], "≤20 分", icon_str="🔴")
    with ac6:
        metric_card("超期未复评", a_stats["超期未复评"], "须重新评估", icon_str="⚠️")

    # 备案录入表单（选择本机构老人 → 四维打分 → 自动定级）
    with st.expander("＋ 录入评估备案（监管复核/备案）", expanded=False):
        eligible = [e for e in elders if e.status == "在院"]
        if not eligible:
            st.info("该机构暂无在院老人可评估")
        else:
            e_opts = {f"{e.code} · {e.name}（{e.room}）": e for e in eligible[:200]}
            with st.form("assess_form"):
                fc1, fc2 = st.columns(2)
                with fc1:
                    sel_e = st.selectbox("👴 选择老人", list(e_opts.keys()))
                    adl = st.slider("生活自理得分（进食/穿衣/如厕/行走/洗浴）", 0, 40, 30,
                                    help="失能老人此项通常较低")
                    emotion = st.slider("情绪行为得分（情绪/行为/沟通）", 0, 8, 7)
                with fc2:
                    assessor = st.text_input("评估员（姓名打码存）", value="评估员")
                    assessor_org = st.text_input("评估机构", value="西安市养老服务评估中心")
                    cognition = st.slider("认知能力得分（记忆/定向/判断）", 0, 16, 14)
                    sensory = st.slider("视听觉得分", 0, 8, 7)
                submitted_a = st.form_submit_button("💾 提交备案")
            if submitted_a:
                e = e_opts[sel_e]
                total = adl + cognition + emotion + sensory
                from services.assessment import calc_level
                lvl = calc_level(total)
                assess(session, org_id=org.id, elder_id=e.id,
                       adl=adl, cognition=cognition, emotion=emotion, sensory=sensory,
                       assessor=assessor[:1] + "*", assessor_org=assessor_org, user=user)
                st.success(f"评估备案成功：{e.name} 四维 {adl}+{cognition}+{emotion}+{sensory}={total} 分 → **{lvl}**，有效期 6 个月")
                st.rerun()

    # 备案台账（本机构）
    recs = [r for r in list_records(session, [org.id], limit=500) if r["机构"]]
    if recs:
        st.caption(f"该机构评估备案台账（共 {len(recs)} 条 · 老人信息已脱敏）")
        st.dataframe(pd.DataFrame(recs), use_container_width=True, hide_index=True,
                     column_config={"生活自理": st.column_config.TextColumn(width="small"),
                                    "认知": st.column_config.TextColumn(width="small"),
                                    "情绪行为": st.column_config.TextColumn(width="small"),
                                    "视听觉": st.column_config.TextColumn(width="small")})
    else:
        st.info("该机构暂无评估备案记录，请先在表单中录入")

    # ============ 排班配比雷达 ============
    st.markdown("<hr style='border-top:1px dashed #CBD5E1;margin:24px 0;'>", unsafe_allow_html=True)
    section_title("👩‍⚕️", "动态排班 · 护患比校验雷达", "按该机构在院老人实际结构校验 · 低于警戒线强制拒绝保存（C1）")
    if not roster:
        st.info("该机构暂无可统计的排班区域")
    for r in roster:
        if r["ok"]:
            st.markdown(f"**{r['区域']}**：护工 {r['在班护工']} 人 / 老人 {r['在住老人']} 人 → 配比 {r['实际配比']}（警戒 {r['警戒线']}）✅")
        else:
            st.markdown(f"""
            <div style="background:linear-gradient(135deg,#FEF2F2,#FEE2E2);border-left:6px solid #DC2626;
                border-radius:8px;padding:10px 14px;color:#991B1B;">
                🔴 <b>{r['区域']}</b>：配比 {r['实际配比']} 低于警戒线 1:{r['警戒线'].split(':')[1]}，
                <b>排班已强制拒绝保存</b>，请增加 {max(1, int(round(r['在住老人'] / int(r['警戒线'].split(':')[1]))) - r['在班护工'])} 名护工！
            </div>
            """, unsafe_allow_html=True)

    st.markdown("""
    <div style="border:1px dashed #CBD5E1;border-radius:10px;padding:14px 18px;background:#FAFBFC;margin-top:14px;">
        <b>⚖️ 护患比警戒线（参照民政部《养老机构岗位设置及人员配备规范》）</b><br>
        <span style="font-size:14px;color:#475569;">
        重度失能 ≤1:3 · 中度失能 ≤1:6 · 轻度失能 ≤1:10 · 自理 ≤1:15<br>
        未做能力评估（D3）扣 6 分 · 人员配备不足（C1）扣 6 分
        </span>
    </div>
    """, unsafe_allow_html=True)
