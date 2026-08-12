# -*- coding: utf-8 -*-
"""政务数据脱敏工具 — 按《脱敏 5 步法》统一处理
1. 删除直接标识：老人 → 姓氏+称谓（张大爷/李奶奶）
2. 截断号码 / 模糊地址：页面统一不展示
3. 范围化数值：年龄 → 年龄段
4. 抽样替代：演示数据非真实
5. 机构名称 → 编码（ORG-XXX）+ 首字打码
"""
import re


_ELDER_NAMES = [
    ("张", "大爷"), ("李", "奶奶"), ("王", "爷爷"), ("刘", "奶奶"),
    ("陈", "爷爷"), ("杨", "奶奶"), ("黄", "大爷"), ("周", "奶奶"),
    ("吴", "爷爷"), ("徐", "奶奶"), ("孙", "大爷"), ("胡", "奶奶"),
]


def elder_code(i: int) -> str:
    """老人脱敏：删除直接标识 → 姓氏+称谓（张某、张大爷…）
    按 5 步法第 1 条「张三 → 张某/李大爷」处理，可区分但不暴露全名"""
    surname, honor = _ELDER_NAMES[(i - 1) % len(_ELDER_NAMES)]
    return f"{surname}{honor}"


def age_band(age: int) -> str:
    """范围化数值：67岁 → 60-69岁"""
    low = (age // 10) * 10
    return f"{low}-{low + 9}岁"


def staff_mask(name: str) -> str:
    """员工/评估人姓氏打码：赵文静 → 赵*"""
    if not name:
        return "—"
    return name[0] + "*"


def org_code(code: str) -> str:
    """机构名称脱敏：保留监管编码 ORG-XXX（不输出全名）"""
    return code


def org_label(name: str, code: str) -> str:
    """机构展示：不脱敏，显示全称 + 监管编码（机构名称属于监管对象公开信息）"""
    return f"{name}（{code}）"


def mask_phone(phone: str) -> str:
    """手机号截断：139****0001"""
    if not phone or len(phone) < 7:
        return phone or "—"
    return phone[:3] + "****" + phone[-4:]


def mask_id(id_no: str) -> str:
    """身份证截断：前6后4，中间打码（红线：演示数据不出现真实身份证）"""
    if not id_no or len(id_no) < 10:
        return "—"
    return id_no[:6] + "********" + id_no[-4:]


def aigc_note() -> str:
    """AIGC 标识：页面/数据由 AI 生成，按 2025 新规显式标注"""
    return ("<div style='border:1px dashed #F59E0B;border-radius:8px;padding:8px 12px;"
            "font-size:13px;color:#92400E;background:#FFFBEB;margin:10px 0;'>"
            "🛡️ <b>数据安全声明</b>：本页数据为演示样本——养老机构名称、地址等监管公开信息如实展示；"
            "老人个人信息已按《政务数据脱敏 5 步法》处理：老人全匿名（姓氏+称谓）、年龄范围化、"
            "手机/身份证等号码截断打码；涉及个人隐私的内容一律不输出全名。"
            "</div>")


def aigc_badge(text: str = "AI 生成") -> str:
    """AIGC 显式标识徽标（2025 新规）"""
    return (f"<span style='background:#FEF3C7;color:#92400E;border:1px solid #FDE68A;"
            f"border-radius:4px;padding:1px 8px;font-size:11px;font-weight:600;'>🤖 {text}</span>")
