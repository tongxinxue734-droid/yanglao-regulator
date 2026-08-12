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
        st.info("💡 请上传隐患照片或现场拍照，系统将自动调用视觉大模型框选违规点并匹配扣分指标。")
        col_cam, col_res = st.columns([1, 1])

        with col_cam:
            img_source = st.radio("获取图片方式", ["📂 本地相册", "📷 现场拍摄"], horizontal=True,
                                  label_visibility="collapsed")

            photo = None
            if img_source == "📂 本地相册":
                photo = st.file_uploader("选择隐患照片（点击或拖拽）", type=['jpg', 'jpeg', 'png'])
            else:
                photo = st.camera_input("拍摄现场照片")

        with col_res:
            if photo is not None:
                st.success("✅ 图片已获取！正在进行视觉分析...")
                with st.spinner("AI 识别中..."):
                    import time
                    time.sleep(1.5)  # 模拟网络延迟

                    # 模拟视觉识别返回结果
                    st.markdown("#### 🔍 AI 诊断报告")
                    st.markdown(f"**最高风险匹配**：{level_badge('橙色')}", unsafe_allow_html=True)
                    st.markdown("**识别类目**：设施安全")
                    st.markdown("**关联违规指标**：B3 (占用、封锁消防通道、安全出口)")
                    st.markdown("**预估扣分**：6 分")
                    st.markdown("**处置建议**：7 日内完成整改，逾期将面临 1000 元罚款。")

                    if st.button("🚀 一键生成工单并指派", type="primary"):
                        # 保存水印照片（姓名+机构+时间，感知哈希去重）
                        photos = []
                        if photo is not None:
                            from services.watermark import save_photo
                            org_name = org_label(org_opts[org_sel].name, org_opts[org_sel].code) if orgs else "辖区"
                            p = save_photo(photo.getvalue(), name=user.name,
                                           room=org_name, location="现场检查", subdir="hazards")
                            if p:
                                photos.append(p)
                            else:
                                st.info("该照片与历史记录重复，已自动去重（问题仍立案）")
                        # 构建隐患记录
                        new_hazard = Hazard(
                            code=f"HZ-{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}",
                            category="设施安全",
                            title="[AI视觉识别] 消防通道存在物品堆积",
                            description="AI 摄像头识别到走廊/消防通道有轮椅及杂物堆积，存在安全隐患。",
                            level="橙色",
                            source="AI识别",
                            indicator_code="B3",
                            deducted=6,
                            org_id=org_id,
                            reporter_id=user.id,
                            photos=photos,
                            status="pending_rectify",
                            deadline=datetime.datetime.now() + datetime.timedelta(days=HAZARD_LEVELS["橙色"]["days"])
                        )
                        session.add(new_hazard)
                        _sync_violation(session, user, org_id, new_hazard)
                        session.commit()
                        st.balloons()
                        st.success(f"工单 {new_hazard.code} 已成功派发至相关责任人！"
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