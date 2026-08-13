# -*- coding: utf-8 -*-
"""隐患拍照/语音智能上报模块"""
import streamlit as st
import datetime
from sqlalchemy.orm import Session
import json

from models import Hazard, Space, User, Indicator, AuditLog, Organization, ViolationRecord
from services.mask import org_label
from auth import current_user, visible_org_ids
from views.theme import level_badge
from config import HAZARD_LEVELS, HAZARD_CATEGORIES
from indicators import BUILTIN_INDICATORS


def mock_ai_semantics_extraction(text: str) -> dict:
    """
    模拟大模型语义提取引擎：根据文本内容，自动匹配 39 项评价指标
    并判定风险等级、推荐整改期限
    """
    result = {
        "found": False,
        "indicator_code": None,
        "level": "黄色",  # 默认一般违规
        "category": "其他",
        "title": "常规隐患发现",
        "confidence": 0.0
    }

    if not text:
        return result

    # 关键词匹配规则引擎 (对应 39 项指标)
    rules = [
        {"keywords": ["火灾", "中毒", "伤人", "死亡"], "code": "B1", "level": "红色", "category": "设施安全"},
        {"keywords": ["堵塞", "消防通道", "轮椅", "杂物堆放", "安全出口"], "code": "B3", "level": "橙色",
         "category": "设施安全"},
        {"keywords": ["没签合同", "劳动合同", "未签合同"], "code": "C2", "level": "黄色", "category": "人员配备"},
        {"keywords": ["打人", "骂人", "虐待", "侮辱", "偷东西", "隐私"], "code": "C5", "level": "红色",
         "category": "人员配备"},
        {"keywords": ["没做评估", "入院评估", "健康档案"], "code": "D3", "level": "橙色", "category": "服务规范"},
        {"keywords": ["无证", "食品经营许可", "食堂卫生", "拉肚子"], "code": "D8", "level": "红色",
         "category": "服务规范"},
        {"keywords": ["乱收费", "押金", "预收费", "挪用"], "code": "F3", "level": "红色", "category": "资金收费"},
        {"keywords": ["扶手", "松动", "无障碍", "摔倒"], "code": "B6", "level": "黄色", "category": "设施安全"},
    ]

    for rule in rules:
        for kw in rule["keywords"]:
            if kw in text:
                result["found"] = True
                result["indicator_code"] = rule["code"]
                result["level"] = rule["level"]
                result["category"] = rule["category"]
                result["title"] = f"AI识别风险: 疑似触发 {rule['code']} 指标违规"
                result["confidence"] = 0.92
                return result

    return result


def _sync_violation(session, user, org_id, hazard):
    """政府现场检查发现的问题：关联违规指标则联动生成扣分记录（100 分制）+ 预警推送"""
    if hazard.indicator_code and org_id:
        exists = session.query(ViolationRecord).filter(
            ViolationRecord.hazard_id == hazard.id).first()
        if not exists:
            session.add(ViolationRecord(
                indicator_code=hazard.indicator_code,
                period=datetime.datetime.now().strftime("%Y-%m"),
                org_id=org_id, hazard_id=hazard.id, found_by=user.id,
                deducted=hazard.deducted or 0, source="现场检查"))
            # 预警推送
            try:
                from services.notify import push as push_notify
                org_obj = session.query(Organization).get(org_id)
                push_notify("问题立案", f"{org_label(org_obj.name, org_obj.code) if org_obj else '辖区'} 现场检查发现违规"
                                        f"（{hazard.indicator_code}，扣 {hazard.deducted or 0} 分）：{hazard.title}")
            except Exception:
                pass


def render(session: Session):
    st.markdown("<h3 style='color: #1E293B;'>📷 智能隐患上报终端（政府现场检查）</h3>", unsafe_allow_html=True)
    st.markdown(
        "<span style='color: #64748B; font-size: 14px;'>支持 AI 视觉识别、语音转写与手工补录，自动匹配违规指标；"
        "发现的问题自动关联机构并联动扣分（100 分制月度评分）。</span>",
        unsafe_allow_html=True)
    st.markdown("<br>", unsafe_allow_html=True)

    user = current_user(session)

    # 检查对象机构（按管辖片区）
    vis_org_ids = visible_org_ids(session, user)
    orgs = session.query(Organization).filter(
        Organization.active == True,
        Organization.id.in_(vis_org_ids) if vis_org_ids else True).all()
    if orgs:
        org_opts = {org_label(o.name, o.code): o for o in orgs}
        org_sel = st.selectbox("🏛️ 检查对象机构", list(org_opts.keys()), key="gov_org")
        org_id = org_opts[org_sel].id
    else:
        org_id = None
        st.warning("管辖范围内暂无可检查机构")

    # 空间列表获取
    spaces = session.query(Space).all()
    space_options = {s.id: s.full_name for s in spaces}

    # 选项卡布局：拍照、语音、纯文本
    tab1, tab2, tab3 = st.tabs(["📸 AI 拍照识别", "🎤 语音智能转写", "📝 快速图文录入"])

    with tab1:
        st.info("💡 请上传隐患照片或现场拍照，系统将自动调用视觉大模型识别，AI 结果仅供参考，请人工核实确认后提交。")
        # ---- 第一步：上传（整行） ----
        img_source = st.radio("获取图片方式", ["📂 本地相册", "📷 现场拍摄"], horizontal=True,
                              label_visibility="collapsed")
        photo = None
        if img_source == "📂 本地相册":
            photo = st.file_uploader("选择隐患照片（点击或拖拽）", type=['jpg', 'jpeg', 'png'])
        else:
            photo = st.camera_input("拍摄现场照片")

        if photo is not None:
            # 真实调用 AI 识别（offline 演示 / api 视觉大模型可插拔）
            from services.ai_vision import recognize as ai_recognize
            with st.spinner("AI 识别中..."):
                ai = ai_recognize(photo.getvalue())

            # ---- 第二步：下方左右两栏（左=AI 诊断报告，右=人工确认） ----
            st.markdown("---")
            col_diag, col_confirm = st.columns([1, 1.2])

            with col_diag:
                st.markdown("#### 🔍 AI 诊断报告")
                st.markdown(f"**识别类目**：{ai.get('category', '—')} · "
                            f"**风险等级**：{level_badge(ai.get('level', '黄色'))} · "
                            f"**置信度**：{ai.get('confidence', 0) * 100:.0f}%", unsafe_allow_html=True)
                st.markdown(f"**疑似问题**：{ai.get('title', '—')}")
                st.markdown(f"**规范依据**：{ai.get('law_basis', '—')}")
                st.markdown(f"**整改建议**：{ai.get('advice', '—')}")
                if ai.get("mode"):
                    st.caption(f"识别模式：{ai['mode']} · {ai.get('note', '')}")
                # 展示照片小图
                st.image(photo.getvalue(), width=240, caption="现场照片（待确认）")

            with col_confirm:
                st.markdown("#### 🧑‍💼 人工审核确认")
                st.caption("AI 结果仅供辅助，请核实修正后提交；错误识别可在此纠正，防止误报工单。")

                # 预填 AI 结果，供审核修改
                default_cat = ai.get("category", "其他")
                default_title = ai.get("title", "")
                default_level = ai.get("level", "黄色")

                # AI 类目 → 推荐指标映射（自动联动扣分，人工可改）
                CAT_INDICATOR_MAP = {
                    "消防": ["B2", "B3"],
                    "设施": ["B7", "D10"],
                    "用电": ["B7", "D10"],
                    "环境": ["B7", "D10"],
                    "护理": ["C1", "C5"],
                    "食品": ["D8", "D9"],
                    "应急": ["E3"],
                    "药品": ["D6"],
                    "其他": [],
                }
                rec_codes = CAT_INDICATOR_MAP.get(default_cat, [])
                ind_by_code = {i["code"]: i for i in BUILTIN_INDICATORS}
                rec_inds = [ind_by_code[c] for c in rec_codes if c in ind_by_code]
                # 指标下拉选项（推荐指标排最前，自动选第一个推荐）
                ind_opts = {f"{i['code']} {i['item']}（扣{i['deduct']}分）": i for i in BUILTIN_INDICATORS}
                if rec_inds:
                    default_ind_label = f"{rec_inds[0]['code']} {rec_inds[0]['item']}（扣{rec_inds[0]['deduct']}分）"
                    ind_choices = ["（不关联指标）"] + [f"{i['code']} {i['item']}（扣{i['deduct']}分）" for i in rec_inds] \
                                  + ["（不关联指标）"]  # 占位避免重复
                    # 去重保序
                    seen = set()
                    ind_choices = [x for x in ind_choices if not (x in seen or seen.add(x))]
                else:
                    default_ind_label = None
                    ind_choices = ["（不关联指标）"] + list(ind_opts.keys())

                with st.form("ai_review_form"):
                    fc1, fc2 = st.columns(2)
                    with fc1:
                        cat_opts = HAZARD_CATEGORIES + ([default_cat] if default_cat not in HAZARD_CATEGORIES else [])
                        r_cat = st.selectbox("隐患类别", cat_opts, index=cat_opts.index(default_cat) if default_cat in cat_opts else 0)
                        r_level = st.selectbox("风险等级", list(HAZARD_LEVELS.keys()),
                                               index=list(HAZARD_LEVELS.keys()).index(default_level) if default_level in HAZARD_LEVELS else 0)
                    with fc2:
                        r_title = st.text_input("隐患标题", value=default_title)
                        r_desc = st.text_area("隐患描述", value=default_title,
                                              height=70, placeholder="补充现场情况说明…")
                    # 关联违规指标（AI 按类目自动推荐并预选，人工可改；决定是否联动扣分）
                    default_idx = ind_choices.index(default_ind_label) if default_ind_label in ind_choices else 0
                    r_ind = st.selectbox("关联违规指标（按 AI 类目自动推荐，可修改）",
                                         ind_choices, index=default_idx,
                                         help="选择指标后提交将按该指标扣分并纳入机构月度评分")
                    r_remark = st.text_area("审核意见（容错备注，如识别有误请说明）", height=60,
                                            placeholder="例如：AI 识别为消防通道堵塞，现场核实为杂物堆放，已修正。")
                    submitted = st.form_submit_button("✅ 确认无误，提交工单", type="primary")

                if submitted:
                    # 保存水印照片（姓名+机构+时间，感知哈希去重）
                    photos = []
                    from services.watermark import save_photo
                    org_name = org_label(org_opts[org_sel].name, org_opts[org_sel].code) if orgs else "辖区"
                    p = save_photo(photo.getvalue(), name=user.name,
                                   room=org_name, location="现场检查", subdir="hazards")
                    if p:
                        photos.append(p)
                    else:
                        st.info("该照片与历史记录重复，已自动去重（问题仍立案）")
                    # 解析指标（推荐/手动选择的）
                    ind = ind_opts.get(r_ind) or ({i["code"]: i for i in BUILTIN_INDICATORS}.get(r_ind.split(" ")[0]) if r_ind != "（不关联指标）" else None)
                    ind_code = ind["code"] if ind else None
                    ded = ind["deduct"] if ind else 0
                    # 构建隐患记录（人工审核后的结果）
                    new_hazard = Hazard(
                        code=f"HZ-{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}",
                        category=r_cat,
                        title=f"[AI识别·人工审核] {r_title}",
                        description=(r_desc + (f"　（审核意见：{r_remark}）" if r_remark.strip() else "")),
                        level=r_level,
                        source="AI识别",
                        indicator_code=ind_code,
                        deducted=ded,
                        ai_result=ai,
                        org_id=org_id,
                        reporter_id=user.id,
                        photos=photos,
                        status="pending_rectify",
                        deadline=datetime.datetime.now() + datetime.timedelta(days=HAZARD_LEVELS[r_level]["days"])
                    )
                    session.add(new_hazard)
                    _sync_violation(session, user, org_id, new_hazard)
                    # 审计留痕：人工审核记录
                    session.add(AuditLog(user_id=user.id, username=user.username,
                                         action="上报-人工审核", target=new_hazard.code,
                                         detail=f"AI识别{ai.get('title','')} → 人工确认:{r_title}（{r_level}）扣{ded}分"))
                    session.commit()
                    st.balloons()
                    st.success(f"工单 {new_hazard.code} 已提交（{'联动扣 ' + str(ded) + ' 分' if ded else '未关联指标'}）！"
                               + ("（含防作弊水印照片）" if photos else ""))

    with tab2:
        st.caption("🎙️ 语音记录上报：现场口述 → 语音转写 → 自动匹配 39 条违规指标"
                   "（离线演示模式：直接输入转写文本；生产可配置 Whisper/讯飞转写，"
                   "见 config.py 的 AI_MODE / VOICE_API_URL）")

        # 语音转写上传入口（始终可见）
        audio_file = st.file_uploader("📤 上传现场语音记录（wav/mp3/m4a/webm）",
                                      type=["wav", "mp3", "m4a", "webm"], key="voice_upload")
        if audio_file:
            with st.spinner("🔊 语音转写中..."):
                from services.voice import transcribe
                text = transcribe(audio_file.getvalue())
                if text:
                    st.success(f"转写成功：{text[:100]}...")
                    st.session_state["real_voice_text"] = text
                else:
                    st.warning("转写失败，请尝试重新上传或使用文本模式")
        default_text = st.session_state.get("real_voice_text", "")
        st.write("输入语音描述隐患内容（系统自动提取要素）：")
        # 实际开发中这里可接入 streamlit-audiorecorder
        mock_voice_text = st.text_area("🎙️ 语音转写结果（模拟修改区）",
                                       placeholder="例如：一层大厅有人把轮椅放在了安全出口，挡住路了。或者，我听到有员工在骂老人。",
                                       value=default_text)

        if st.button("✨ 语义解析", key="btn_parse_voice"):
            if not mock_voice_text:
                st.warning("请输入语音文本内容")
            else:
                with st.spinner("大模型语义提取中..."):
                    analysis = mock_ai_semantics_extraction(mock_voice_text)
                    st.session_state["ai_analysis"] = analysis

        if "ai_analysis" in st.session_state and st.session_state["ai_analysis"]["found"]:
            analysis = st.session_state["ai_analysis"]
            st.markdown("---")
            st.markdown("#### 🧠 知识库匹配成功")
            st.markdown(f"> **提取核心事实**：{mock_voice_text}")

            # 找到对应指标详细内容
            ind_detail = next((item for item in BUILTIN_INDICATORS if item["code"] == analysis["indicator_code"]), None)

            if ind_detail:
                st.error(f"⚠️ **触碰合规红线：【{ind_detail['category']}】{ind_detail['item']}**")
                st.write(f"**指标编号**：{ind_detail['code']}")
                st.write(f"**处罚标准**：扣除 {ind_detail['deduct']} 分")
                st.write(f"**合规指引**：{ind_detail['content']}")

                with st.form("voice_submit_form"):
                    st.write("请确认并上报：")
                    selected_space = st.selectbox("事发空间", options=list(space_options.keys()),
                                                  format_func=lambda x: space_options[x])
                    if st.form_submit_button("确认立案上报", type="primary"):
                        new_hazard = Hazard(
                            code=f"HZ-{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}",
                            category=analysis["category"],
                            title=analysis["title"],
                            description=mock_voice_text,
                            level=analysis["level"],
                            source="语音",
                            indicator_code=analysis["indicator_code"],
                            deducted=ind_detail["deduct"],
                            org_id=org_id,
                            reporter_id=user.id,
                            space_id=selected_space,
                            status="pending_rectify",
                            deadline=datetime.datetime.now() + datetime.timedelta(
                                days=HAZARD_LEVELS[analysis["level"]]["days"])
                        )
                        session.add(new_hazard)
                        _sync_violation(session, user, org_id, new_hazard)
                        session.commit()
                        st.success("✅ 语音隐患已成功上报并建档！")
                        st.session_state.pop("ai_analysis", None)
        elif "ai_analysis" in st.session_state and not st.session_state["ai_analysis"]["found"]:
            st.info("未能匹配到重大合规指标，建议切换至【手工录入】完善详细信息。")

    with tab3:
        with st.form("manual_report_form", clear_on_submit=True):
            st.subheader("手工建立隐患台账")
            col1, col2 = st.columns(2)
            with col1:
                title = st.text_input("隐患简述 (必填)", placeholder="如：二楼洗手间地面湿滑")
                category = st.selectbox("隐患类别", options=HAZARD_CATEGORIES)
                level = st.selectbox("风险等级", options=list(HAZARD_LEVELS.keys()),
                                     format_func=lambda x: f"{x} ({HAZARD_LEVELS[x]['desc']})")
            with col2:
                space_id = st.selectbox("发生位置", options=list(space_options.keys()),
                                        format_func=lambda x: space_options[x])

                # 提取指标库供选择
                ind_options = {ind["code"]: f"[{ind['code']}] {ind['item']} (扣{ind['deduct']}分)" for ind in
                               BUILTIN_INDICATORS}
                ind_options["NONE"] = "未触碰特定红线指标"
                indicator_code = st.selectbox("关联违规标准 (选填)", options=list(ind_options.keys()),
                                              format_func=lambda x: ind_options[x])

            desc = st.text_area("详细描述与整改建议", placeholder="请尽可能详细描述现场情况...")

            if st.form_submit_button("提交隐患工单", type="primary"):
                if not title:
                    st.error("请填写隐患简述！")
                else:
                    deducted_points = 0
                    if indicator_code != "NONE":
                        ind = next((i for i in BUILTIN_INDICATORS if i["code"] == indicator_code), None)
                        if ind: deducted_points = ind["deduct"]

                    h = Hazard(
                        code=f"HZ-{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}",
                        category=category,
                        title=title,
                        description=desc,
                        level=level,
                        source="文字",
                        indicator_code=indicator_code if indicator_code != "NONE" else None,
                        deducted=deducted_points,
                        org_id=org_id,
                        reporter_id=user.id,
                        space_id=space_id,
                        status="pending_rectify",
                        deadline=datetime.datetime.now() + datetime.timedelta(days=HAZARD_LEVELS[level]["days"])
                    )
                    session.add(h)
                    _sync_violation(session, user, org_id, h)
                    session.add(AuditLog(user_id=user.id, username=user.username, action="新增隐患", target=h.code))
                    session.commit()
                    st.success("📝 手工记录已成功提交入库！")