# -*- coding: utf-8 -*-
"""AI 视觉隐患识别：offline 演示模式 / api 第三方视觉大模型（可插拔）

输出结构化字段：隐患类别、风险等级、规范依据、置信度、整改建议初稿
"""
import random

import config

# 养老场景 9 大核心识别类目预设库
VISION_KNOWLEDGE = {
    "消防": [
        ("消防通道堵塞", "红色", "《养老机构管理办法》第25条", "立即清理通道障碍物，确保消防通道畅通，设置禁堆标识。"),
        ("灭火器过期或缺失", "橙色", "《消防设施通用规范》GB55036", "检查灭火器压力与有效期，过期立即更换，缺失位置补配。"),
        ("应急灯故障", "橙色", "《建筑设计防火规范》GB50016", "检修应急照明线路，故障灯具立即更换，保证断电自动点亮。"),
        ("安全出口遮挡", "红色", "《消防法》第28条", "清除安全出口遮挡物，保持疏散门可正常开启。"),
    ],
    "设施": [
        ("扶手松动或缺失", "橙色", "《西安市养老服务促进条例》第18条", "加固松动扶手，缺失部位补装无障碍扶手。"),
        ("床栏损坏", "橙色", "《养老机构服务质量基本规范》", "更换损坏床栏，检查卡扣牢固度，防止老人坠床。"),
        ("呼叫器离线", "橙色", "《养老机构服务质量基本规范》", "检修床头呼叫系统，测试信号，离线设备立即修复。"),
        ("地面湿滑无警示", "黄色", "《养老机构服务质量基本规范》", "放置防滑警示牌，及时清理水渍，必要时铺设防滑垫。"),
        ("防滑垫缺失", "黄色", "《养老机构服务质量基本规范》", "卫生间/淋浴间铺设防滑垫并固定。"),
    ],
    "用电": [
        ("电线私拉乱接", "红色", "《用电安全导则》GB/T13869", "拆除私拉电线，规范布线，禁止使用多头插排串联。"),
        ("插座裸露破损", "红色", "《用电安全导则》GB/T13869", "更换破损插座面板，做好绝缘防护，加装保护盖。"),
        ("大功率违规电器", "橙色", "《养老机构消防安全管理规定》", "清理违规大功率电器，检查线路负载，建立电器台账。"),
        ("线路老化", "橙色", "《用电安全导则》GB/T13869", "检测线路绝缘老化程度，老化线路整段更换。"),
    ],
    "环境": [
        ("杂物堆积", "黄色", "《养老机构服务质量基本规范》", "清理堆积杂物，规范物品摆放，保持通道整洁。"),
        ("地面障碍物", "黄色", "《养老机构服务质量基本规范》", "移除地面障碍物，设置警示，防止老人绊倒。"),
        ("光线不足", "蓝色", "《养老机构服务质量基本规范》", "更换或增补照明灯具，保证公共区域照度达标。"),
        ("积水积冰", "黄色", "《养老机构服务质量基本规范》", "清理积水积冰，铺设防滑垫，设置警示标识。"),
    ],
    "护理": [
        ("药品乱放", "橙色", "《药品管理法》第25条", "药品分类存放、专人管理，核对效期，处方药上锁管理。"),
        ("锐器无收纳", "橙色", "《医疗废物管理条例》", "锐器立即收入利器盒，规范医疗废物处置。"),
        ("约束带违规使用", "红色", "《养老机构服务安全基本规范》GB38600", "立即解除违规约束，改用防护措施，做好评估记录。"),
    ],
    "食品": [
        ("食品存放不规范", "橙色", "《食品安全法》第33条", "规范食品贮存，落实留样制度，核查保质期。"),
        ("后厨卫生不达标", "黄色", "《食品安全法》第33条", "清洁后厨环境，落实消毒制度。"),
    ],
    "应急": [
        ("应急疏散通道堵塞", "红色", "《消防法》第28条", "立即清理疏散通道，确保应急出口畅通。"),
        ("应急物资缺失", "黄色", "《养老机构管理办法》第31条", "补齐应急物资，定期检查有效期。"),
    ],
    "药品": [
        ("药品过期", "橙色", "《药品管理法》第98条", "下架过期药品，建立效期预警台账。"),
    ],
}


def recognize(image_bytes: bytes) -> dict:
    """识别隐患。
    - api 模式：调用智谱 GLM-4V 视觉模型（OpenAI 兼容接口），未配置 Key 时自动回退演示；
    - offline 模式：返回预设库随机结构（置信度偏低提示人工复核）。"""
    if config.AI_MODE == "api":
        return _recognize_api(image_bytes)
    return _recognize_offline(image_bytes)


def _recognize_offline(image_bytes: bytes) -> dict:
    rnd = random.Random(image_bytes[:64])  # 同一图片结果稳定
    cat = rnd.choice(list(VISION_KNOWLEDGE.keys()))
    item = rnd.choice(VISION_KNOWLEDGE[cat])
    title, level, basis, advice = item
    return {
        "category": cat,
        "title": title,
        "level": level,
        "law_basis": basis,
        "confidence": round(rnd.uniform(0.62, 0.92), 2),
        "advice": advice,
        "mode": "offline-演示",
        "note": "演示模式模拟识别结果，请人工复核修正后提交",
    }


# 智谱 GLM-4V 识别提示词：场景描述 + 疑似提醒（不强行判定隐患）
# 定位：AI 如实描述画面内容，给出疑似风险点供人工判断——符合通用视觉模型真实能力
_VISION_SYSTEM_PROMPT = """你是养老机构安全巡检的视觉识别助手。请分析图片，只输出 JSON。你的任务是【如实描述场景】+【提示疑似风险】，不强行判定隐患。

JSON 格式：
{
  "scene_desc": "简要描述画面内容（30-60字）：这是什么场所、有什么物体、大致状态。例如：办公走廊，白色墙面浅色地砖，墙上有灭火器箱，地面有折叠椅。",
  "category": "疑似风险所属类别（从：消防/设施/用电/环境/护理/食品/应急/药品/其他 中选择；无明显疑似时填其他）",
  "title": "疑似风险描述（用"疑似"开头；无明显风险时填：未发现明显隐患）",
  "level": "风险等级（红色=紧急/橙色=较重/黄色=一般/蓝色=轻微；无风险填蓝色）",
  "law_basis": "相关法规依据（不确定填待核实）",
  "confidence": 0.0到1.0的置信度数字（仅当你确信用肉眼能确认明确危险时才高于0.7，否则0.3-0.5）,
  "advice": "建议（如：请现场确认地面是否湿滑；无需整改则填：现场正常）"
}

描述要点：
- 如实描述你看到的（场所/物体/状态），不要编造
- 疑似风险用"疑似"措辞（如：地面有反光疑似湿滑、物品较多疑似通道不便、灭火器箱未见灭火器疑似缺失）
- 明显正常的环境（正常走廊/办公室/房间）→ title 填"未发现明显隐患"，scene_desc 如实描述即可
- 你的角色是"辅助提醒"，最终判断由检查员现场确认"""


def _recognize_api(image_bytes: bytes) -> dict:
    """智谱 GLM-4V-Flash 视觉识别（免费，OpenAI 兼容接口）。未配置 Key / 调用失败自动回退演示。"""
    import base64
    import json

    import urllib.request

    if not config.ARK_API_KEY:
        result = _recognize_offline(image_bytes)
        result["mode"] = "api-未配置"
        result["note"] = "未配置 ZHIPU_API_KEY（智谱 GLM-4V，免费），已回退演示识别，请配置后启用真实识别"
        return result

    try:
        b64 = base64.b64encode(image_bytes).decode()
        payload = {
            "model": config.ARK_VISION_MODEL,
            "messages": [
                {"role": "system", "content": _VISION_SYSTEM_PROMPT},
                {"role": "user", "content": [
                    {"type": "text", "text": "请描述这张照片的场景，并提示可能的疑似风险（如有）。"},
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64}"}},
                ]},
            ],
            "temperature": 0.1,
            "max_tokens": 500,
        }
        req = urllib.request.Request(
            config.ARK_BASE_URL,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json",
                     "Authorization": f"Bearer {config.ARK_API_KEY}"},
        )
        with urllib.request.urlopen(req, timeout=60) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        content = data["choices"][0]["message"]["content"]
        # 解析模型返回的 JSON（可能被 markdown 包裹）
        content = content.strip()
        if content.startswith("```"):
            content = content.split("\n", 1)[-1].rsplit("```", 1)[0].strip()
        parsed = json.loads(content)
        # 兜底字段
        parsed.setdefault("scene_desc", "")
        parsed.setdefault("category", "其他")
        parsed.setdefault("title", "未发现明显隐患")
        parsed.setdefault("level", "蓝色")
        parsed.setdefault("law_basis", "待核实")
        parsed.setdefault("confidence", 0.3)
        parsed.setdefault("advice", "现场正常，无需整改。")
        parsed["mode"] = "api-智谱GLM4V"
        parsed["note"] = "智谱 GLM-4V 免费视觉模型识别结果，请人工复核确认后提交"
        return parsed
    except Exception as e:
        # API 不可用时回退演示识别，并标注原因，避免上报流程中断
        result = _recognize_offline(image_bytes)
        result["mode"] = "api-回退"
        result["note"] = f"智谱 GLM-4V 调用失败（{e}），已回退演示识别，请人工复核"
        return result
