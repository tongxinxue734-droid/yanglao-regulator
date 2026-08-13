# -*- coding: utf-8 -*-
"""全局配置与常量定义"""
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
UPLOAD_DIR = os.path.join(DATA_DIR, "uploads")
DB_PATH = os.environ.get("SAFETY_DB_PATH", os.path.join(DATA_DIR, "safety.db"))
os.makedirs(UPLOAD_DIR, exist_ok=True)

DATABASE_URL = f"sqlite:///{DB_PATH}"

APP_NAME = "养老机构安全巡检与合规考核系统"
ORG_NAME = "示例养老服务中心"

# ---------------------------------------------------------------
# 隐患四级风险分级（红色24h / 橙色3天 / 黄色7天 / 蓝色15天）
# ---------------------------------------------------------------
HAZARD_LEVELS = {
    "红色": {"days": 1, "desc": "紧急，24 小时内必须闭环（如消防通道堵塞、电线裸露）"},
    "橙色": {"days": 3, "desc": "较重，3 天内整改（如扶手松动、床栏损坏）"},
    "黄色": {"days": 7, "desc": "一般，7 天内整改（如杂物堆积）"},
    "蓝色": {"days": 15, "desc": "轻微，15 天内整改（如标识模糊）"},
}

# 隐患九大核心识别类目（AI 视觉识别输出）
HAZARD_CATEGORIES = ["消防", "设施", "用电", "环境", "护理", "食品", "药品", "应急", "其他"]

# 隐患来源
HAZARD_SOURCES = ["拍照", "语音", "文字", "AI识别"]

# 状态流转：pending_rectify -> rectifying -> pending_review -> closed -> archived
# rejected(打回) 回到 rectifying
HAZARD_STATUS = {
    "pending_rectify": "待整改",
    "rectifying": "整改中",
    "pending_review": "待复查",
    "rejected": "打回重改",
    "closed": "已闭环",
    "archived": "已归档",
}
HAZARD_STATUS_REV = {v: k for k, v in HAZARD_STATUS.items()}

# ---------------------------------------------------------------
# 综合扣分处罚档次（来自《养老机构运营违规评价指标》）
# 累计扣分 >= 下界 即落入对应档次
# ---------------------------------------------------------------
PUNISHMENT_TIERS = [
    {"deduct": 1, "grade": "纸面瑕疵", "penalty": "口头警告 + 容缺受理"},
    {"deduct": 2, "grade": "轻微违规", "penalty": "200 元罚款 + 7 日整改"},
    {"deduct": 3, "grade": "一般违规", "penalty": "500 元罚款 + 7 日整改"},
    {"deduct": 6, "grade": "较重违规", "penalty": "1000 元罚款 + 限制新入住 30 日"},
    {"deduct": 9, "grade": "严重违规", "penalty": "3000 元罚款 + 限制新入住 60 日 + 重点抽检"},
    {"deduct": 12, "grade": "重大违规", "penalty": "5000 元罚款 + 局部或全面停业整顿 + 取消当年运营补贴 + 平台公示 30 日"},
]

# 评分问卷六大维度（月度巡检打分）
SCORE_DIMENSIONS = ["消防", "设施", "护理", "环境", "食品", "应急"]

# 月度/年度报告导出目录
REPORT_DIR = os.path.join(DATA_DIR, "reports")
os.makedirs(REPORT_DIR, exist_ok=True)

# 智能预警规则
ALERT_RULES = {
    "region_high_risk": {"label": "区域同类隐患高频", "threshold": 3, "unit": "次/月", "desc": "某区域月度同类隐患出现 3 次以上自动标记高风险"},
    "overdue_rate": {"label": "整改逾期率超标", "threshold": 0.30, "desc": "人员整改逾期率超 30% 自动触发上级关注"},
    "score_low": {"label": "月度综合得分偏低", "threshold": 80, "desc": "月度综合得分低于 80 分自动生成整改提醒"},
}

# 微信/邮件推送占位开关（生产环境可接入企业微信机器人 webhook）
ENABLE_WECHAT_PUSH = False
WECHAT_WEBHOOK_URL = os.environ.get("WECHAT_WEBHOOK_URL", "")

# 邮件推送（SMTP）
SMTP_HOST = os.environ.get("SMTP_HOST", "")
SMTP_PORT = int(os.environ.get("SMTP_PORT", "465"))
SMTP_USER = os.environ.get("SMTP_USER", "")
SMTP_PASS = os.environ.get("SMTP_PASS", "")
NOTIFY_EMAIL = os.environ.get("NOTIFY_EMAIL", "")

# AI 能力开关：offline(演示模拟) / api(智谱 GLM-4V 免费视觉识别)
AI_MODE = "offline"
# 智谱 GLM-4V（免费视觉模型，OpenAI 兼容接口）
ARK_API_KEY = os.environ.get("ZHIPU_API_KEY", os.environ.get("ARK_API_KEY", ""))
ARK_BASE_URL = os.environ.get("ZHIPU_API_URL", "https://open.bigmodel.cn/api/paas/v4/chat/completions")
ARK_VISION_MODEL = os.environ.get("ZHIPU_VISION_MODEL", "glm-4v-flash")
VOICE_API_URL = os.environ.get("VOICE_API_URL", "")
