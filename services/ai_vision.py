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
    """识别隐患。offline 模式返回预设库随机结构（置信度偏低提示人工复核）；
    api 模式调用第三方视觉大模型（配置 VISION_API_URL 后启用）。"""
    if config.AI_MODE == "api" and config.VISION_API_URL:
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


def _recognize_api(image_bytes: bytes) -> dict:
    """第三方视觉大模型接入点（如豆包视觉/百度智能云隐患识别）。
    生产环境：上传图片 -> 解析 JSON -> 映射到 VISION_KNOWLEDGE 标准类目。"""
    import base64
    import json

    import urllib.request

    try:
        b64 = base64.b64encode(image_bytes).decode()
        payload = json.dumps({"image": b64, "scene": "nursing_home_hazard"}).encode()
        req = urllib.request.Request(config.VISION_API_URL, data=payload,
                                     headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode())
        data.setdefault("mode", "api")
        return data
    except Exception as e:
        # API 不可用时回退演示识别，并标注原因，避免上报流程中断
        result = _recognize_offline(image_bytes)
        result["mode"] = "api-回退"
        result["note"] = f"视觉 API 调用失败（{e}），已回退演示识别，请人工复核"
        return result
