# -*- coding: utf-8 -*-
"""AI 智能助理 — 合规指标问答（RAG 规则检索版）
输入问题 → 检索 39 条指标库 → 秒回扣分标准与依据（可扩展 DeepSeek）
"""
import re

import pandas as pd
import streamlit as st
from sqlalchemy.orm import Session

from auth import require_role
from models import Indicator
from services import llm as llm_svc
from services.mask import aigc_badge
from views.theme import app_header, metric_card, section_title


def _match_indicators(session: Session, query: str, top_k: int = 3):
    """关键词规则检索：问题文本 ∩ 指标标题/关键词 → 匹配得分
    支持同义词归一（冰柜→冷藏冷冻/设施设备）与 n-gram 子串匹配"""
    q = query.strip()
    # 同义词归一：日常口语 → 指标库用词（扩大命中面）
    SYNONYMS = {
        "冰柜": "冷藏冷冻 冰柜 冰箱 冷冻",
        "冰箱": "冷藏冷冻 冰柜 冰箱 冷冻",
        "冷柜": "冷藏冷冻 冰柜 冰箱 冷冻",
        "留样": "留样 食品留样",
        "消毒柜": "消毒柜 消毒",
        "培训证": "培训 职业技能",
        "没培训": "培训 职业技能",
        "灭火器": "灭火器 消防",
        "消防通道": "消防通道 疏散通道",
        "押金": "押金 预收费",
        "骗补": "补贴 骗取",
        "食堂": "食品 餐饮 食堂",
        "伙食": "食品 餐饮 伙食",
        "坏了": "设施设备 维修",
    }
    expanded = q
    for k, v in SYNONYMS.items():
        if k in q:
            expanded += " " + v
    inds = session.query(Indicator).all()
    tokens = set()
    for n in range(2, 5):
        for i in range(len(expanded) - n + 1):
            tokens.add(expanded[i:i + n])
    scored = []
    for ind in inds:
        hay = f"{ind.code} {ind.item} {ind.content or ''}"
        s = sum(1 for t in tokens if t in hay)
        if s:
            scored.append((s, ind))
    scored.sort(key=lambda x: -x[0])
    return [ind for _, ind in scored[:top_k]]


def render(session: Session):
    require_role(1)
    app_header("🤖 AI 智能助理", "基于《养老机构服务安全基本规范》指标库 · 秒回扣分标准 · 支持语音转写提问")

    c1, c2, c3 = st.columns(3)
    ind_count = session.query(Indicator).filter(Indicator.active == True).count()
    with c1:
        metric_card("指标库", ind_count, f"{ind_count} 条违规指标")
    with c2:
        metric_card("六类覆盖", "A-F", "安全/卫生/管理/人员")
    with c3:
        metric_card("问答引擎", "规则检索", "可升级 DeepSeek")

    section_title("💬", "合规问答", "例如：「厨房冰柜坏了扣几分？」「消防通道堵塞」「护理人员未培训」")

    col_q, col_b = st.columns([3, 1])
    with col_q:
        question = st.text_input("输入您的问题", placeholder="例如：食品留样不合规扣几分？",
                                 label_visibility="collapsed")
    with col_b:
        ask = st.button("🔍 查询标准", type="primary", use_container_width=True)

    if ask and question:
        matches = _match_indicators(session, question)
        if not matches:
            st.warning("未匹配到明确指标，请换种说法（例如包含「消防」「食品」「护理」等关键词）")
        else:
            # 引擎 1：DeepSeek 大模型（RAG 上下文）——失败自动降级
            answer = llm_svc.ask(question, llm_svc.build_context(matches))
            if answer:
                st.markdown(
                    f'<div style="border:1px solid #E2E8F0;border-left:6px solid #7C3AED;'
                    f'border-radius:10px;padding:14px 18px;margin-bottom:12px;background:#FFFFFF;">'
                    f'<div style="font-size:13px;font-weight:700;color:#4C1D95;margin-bottom:8px;">'
                    f'🤖 DeepSeek 解答 {aigc_badge()}</div>'
                    f'<div style="font-size:14px;color:#334155;line-height:1.8;">{answer}</div>'
                    f'</div>', unsafe_allow_html=True)
            else:
                st.markdown(
                    f'<div style="border:1px dashed #94A3B8;border-radius:8px;padding:8px 12px;'
                    f'font-size:12px;color:#475569;background:#F8FAFC;margin-bottom:10px;">'
                    f'🔌 DeepSeek 未连接（缺 API Key 或网络超时），已降级为<b>本地规则引擎</b>'
                    f'（仅展示指标扣分）</div>', unsafe_allow_html=True)
            # 引擎 2：命中指标卡片（无论哪种引擎都展示，便于核对依据）
            st.caption(f"命中指标（{len(matches)} 条，供核对）：")
            for ind in matches:
                st.markdown(f"""
                <div style="border:1px solid #E2E8F0;border-left:6px solid #2563EB;border-radius:10px;
                    padding:14px 18px;margin-bottom:10px;background:#FFFFFF;">
                    <div style="font-size:14px;font-weight:700;color:#1E3A8A;">{ind.code} {ind.item}</div>
                    <div style="font-size:12px;color:#475569;margin-top:6px;">
                        <b>扣分：</b><span style="color:#DC2626;font-weight:700;">{ind.deduct} 分</span>
                        ｜ <b>类别：</b>{ind.category} ｜ <b>依据：</b>{ind.law_basis or '—'}
                    </div>
                </div>
                """, unsafe_allow_html=True)
    elif ask:
        st.info("请输入问题后再查询")

    # 语音提问（演示：输入转写文本）
    with st.expander("🎤 语音提问（演示）"):
        voice = st.text_area("语音转写结果", placeholder="说出您的问题，系统自动转写，例如：我看到灭火器过期了，该扣几分？",
                             height=80)
        if st.button("识别并查询", use_container_width=True) and voice.strip():
            matches = _match_indicators(session, voice)
            if matches:
                top = matches[0]
                st.success(f"🗣️ 已识别语音：「{voice.strip()[:30]}…」→ 命中 {top.code} {top.item}（扣 {top.deduct} 分）")
            else:
                st.warning("未匹配到指标，请补充关键词")

    # 快捷问答示例
    st.markdown("<hr style='border-top:1px dashed #CBD5E1;margin:20px 0;'>", unsafe_allow_html=True)
    st.caption("💡 试试这些问题：")
    quick = ["厨房冰柜坏了扣几分", "消防通道堵塞", "护理员没有培训证", "食品留样不规范", "未做能力评估", "骗取补贴"]
    btns = st.columns(6)
    for i, q in enumerate(quick):
        if btns[i % 6].button(q, key=f"q{i}"):
            matches = _match_indicators(session, q)
            for ind in matches[:2]:
                # 注意：含 HTML 的 markdown 必须加 unsafe_allow_html=True，否则 <b> 会被转义显示为裸源码
                st.markdown(f"**{ind.code} {ind.item}** → 扣 <b style='color:#DC2626'>{ind.deduct} 分</b> · {ind.law_basis or ''}",
                            unsafe_allow_html=True)
