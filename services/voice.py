# -*- coding: utf-8 -*-
"""语音隐患上报：转写 + 智能结构化（位置/类型/紧急程度）

offline 演示模式：直接对文本做要素提取（正则 + 关键词）；
api 模式：接 Whisper / 讯飞 / 阿里云语音转写后走同一结构化逻辑。
"""
import re

import config

# 紧急程度关键词
_LEVEL_KEYWORDS = {
    "红色": ["着火", "冒烟", "火花", "裸露", "堵塞", "紧急", "危险", "快", "马上", "立即", "流血", "摔倒"],
    "橙色": ["松动", "损坏", "故障", "过期", "离线", "漏", "坏", "破"],
    "黄色": ["堆积", "堆放", "杂物", "不亮", "湿", "乱", "缺"],
    "蓝色": ["模糊", "不清", "旧", "慢"],
}

# 类别关键词
_CAT_KEYWORDS = {
    "消防": ["消防", "灭火器", "通道", "出口", "应急灯", "烟感"],
    "用电": ["电线", "插座", "电", "灯", "线路", "裸露"],
    "设施": ["扶手", "床栏", "呼叫器", "门", "窗", "轮椅", "床"],
    "环境": ["杂物", "地面", "水", "滑", "垃圾", "脏", "光线", "照明"],
    "护理": ["药", "锐器", "针", "约束"],
    "食品": ["食品", "食堂", "留样", "过期", "厨房", "饭菜"],
    "应急": ["演练", "疏散", "物资"],
}

_POS_RE = re.compile(r"(?:在|位于|于)?([\u4e00-\u9fa5A-Za-z0-9]{2,12}(?:室|房|楼|层|走廊|食堂|活动室|医务室|门口|区))")


def transcribe(audio_bytes: bytes) -> str:
    """音频 -> 文本。api 模式调用第三方 API；离线模式用本地 faster-whisper（tiny 模型）"""
    if config.AI_MODE == "api" and config.VOICE_API_URL:
        return _transcribe_api(audio_bytes)
    return _transcribe_offline(audio_bytes)


def _transcribe_offline(audio_bytes: bytes) -> str:
    """本地 faster-whisper 转写（离线，tiny 模型 ~39MB，首次下载）"""
    import os as _os
    _os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")  # 解决 OpenMP 冲突
    import tempfile
    from faster_whisper import WhisperModel

    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
        f.write(audio_bytes)
        tmp = f.name
    try:
        model = WhisperModel("tiny", device="cpu", compute_type="int8")
        segments, _ = model.transcribe(tmp, language="zh", beam_size=5)
        text = " ".join(s.text for s in segments)
        return text
    finally:
        _os.unlink(tmp)


def _transcribe_api(audio_bytes: bytes) -> str:
    import base64
    import json
    import urllib.request

    try:
        b64 = base64.b64encode(audio_bytes).decode()
        payload = json.dumps({"audio": b64, "lang": "zh"}).encode()
        req = urllib.request.Request(config.VOICE_API_URL, data=payload,
                                     headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=60) as resp:
            data = json.loads(resp.read().decode())
        return data.get("text", "")
    except Exception:
        return ""  # 转写失败返回空文本，界面引导手动输入


def structure(text: str) -> dict:
    """从转写文本提取 隐患位置 / 隐患类型 / 紧急程度 三大要素"""
    text = text or ""
    result = {"location": "", "category": "其他", "level": "黄色", "title": ""}
    m = _POS_RE.search(text)
    if m:
        result["location"] = m.group(1)
    for lvl, kws in _LEVEL_KEYWORDS.items():
        if any(k in text for k in kws):
            result["level"] = lvl
            break
    for cat, kws in _CAT_KEYWORDS.items():
        if any(k in text for k in kws):
            result["category"] = cat
            break
    # 标题：截取首句，最长 40 字
    first = re.split(r"[。！？!?，,]", text)[0].strip()
    result["title"] = first[:40] or text[:40]
    return result
