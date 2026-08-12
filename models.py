# -*- coding: utf-8 -*-
"""SQLAlchemy ORM 数据模型"""
from datetime import datetime
from sqlalchemy import (Column, Integer, String, Text, Float, Boolean, DateTime,
                        ForeignKey, JSON)
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


class Organization(Base):
    """养老机构档案（监管对象，多机构评分体系）"""
    __tablename__ = "organizations"
    id = Column(Integer, primary_key=True)
    name = Column(String(128), nullable=False, unique=True)   # 机构名称（监管公开信息，不脱敏）
    code = Column(String(32), unique=True, nullable=False)     # 机构编号，如 ORG-001
    address = Column(String(256), default="")                  # 地址（区级）
    org_type = Column(String(16), default="民办")              # 公办 / 民办
    level = Column(String(8), default="二星级")                # 星级（一~五星级）
    capacity = Column(Integer, default=0)                      # 核定床位数
    legal_person = Column(String(64), default="")              # 法定代表人（打码）
    manager_name = Column(String(64), default="")              # 负责人
    phone = Column(String(32), default="")
    license_status = Column(String(16), default="在营")        # 在营 / 停业整改 / 注销
    base_score = Column(Integer, default=100)                  # 基准分（满分）
    created_at = Column(DateTime, default=datetime.now)
    active = Column(Boolean, default=True)

    @property
    def full_name(self):
        return f"{self.name}（{self.code}）"


class Elderly(Base):
    """在院老人档案（演示数据 · 个人信息已脱敏存储）
    脱敏规则：姓名只存「姓氏+称谓」（张大爷/李奶奶）；手机/身份证存模拟号、展示层打码；
    家属姓名打码；年龄存数值、展示层范围化；房间仅到房号。
    数据为抽样替代的演示样本，非真实人员信息。
    """
    __tablename__ = "elders"
    id = Column(Integer, primary_key=True)
    org_id = Column(Integer, ForeignKey("organizations.id"), nullable=False)  # 所属机构
    code = Column(String(16), nullable=False)              # 院内编号，如 ORG-001-0001
    name = Column(String(16), nullable=False)              # 脱敏姓名：张大爷/李奶奶
    gender = Column(String(4), default="男")               # 男 / 女
    age = Column(Integer, default=0)                       # 年龄（展示时范围化）
    health_level = Column(String(16), default="自理")      # 自理/轻度失能/中度失能/重度失能
    room = Column(String(32), default="")                  # 房间号
    phone = Column(String(32), default="")                 # 模拟手机号（展示打码）
    id_card = Column(String(32), default="")               # 模拟身份证号（展示打码）
    guardian = Column(String(32), default="")              # 紧急联系人（打码：张*）
    admitted_at = Column(String(16), default="")           # 入住日期 YYYY-MM-DD
    assessed_at = Column(String(16), default="")           # 最近能力评估日期
    assessment_valid = Column(Boolean, default=True)       # 评估是否在有效期内（6 个月）
    status = Column(String(8), default="在院")             # 在院 / 出院
    created_at = Column(DateTime, default=datetime.now)

    org = relationship("Organization", foreign_keys=[org_id])


class User(Base):
    """用户账号（三级权限）"""
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    username = Column(String(64), unique=True, nullable=False)
    password_hash = Column(String(128), nullable=False)
    name = Column(String(64), nullable=False)
    role_level = Column(Integer, nullable=False)          # 1 超级管理员 / 2 部门管理员 / 3 一线执行
    dept_name = Column(String(64), default="")            # 部门/管辖范围，如 护理部 / 一层楼
    parent_id = Column(Integer, ForeignKey("users.id"), nullable=True)  # 上级 ID
    phone = Column(String(32), default="")
    org_ids = Column(JSON, default=list)   # 管辖机构 id 列表（政府监管人员按片区管辖）
    active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.now)


class Space(Base):
    """空间档案：楼栋-楼层-房间/公共区域"""
    __tablename__ = "spaces"
    id = Column(Integer, primary_key=True)
    building = Column(String(64), nullable=False)
    floor = Column(String(32), nullable=False)
    room = Column(String(64), nullable=False)             # 房间号或公共区域名
    space_type = Column(String(16), default="房间")       # 房间 / 公共区域
    manager_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    check_standard = Column(Text, default="")
    created_at = Column(DateTime, default=datetime.now)

    @property
    def full_name(self):
        return f"{self.building}-{self.floor}-{self.room}"


class Indicator(Base):
    """隐患/违规标准库：内置《养老机构运营违规评价指标》39 条 + 自定义扩展"""
    __tablename__ = "indicators"
    id = Column(Integer, primary_key=True)
    code = Column(String(16), unique=True, nullable=False)  # A1..F8
    category = Column(String(32), nullable=False)           # 主体资格/设施安全/...
    item = Column(String(64), nullable=False)               # 事项
    content = Column(Text, nullable=False)                  # 内容/情形描述
    law_basis = Column(Text, default="")                    # 依据
    remark = Column(String(64), default="")                 # 备注（如 ★停业整改）
    deduct = Column(Integer, nullable=False)                # 扣分 1/2/3/6/9/12
    builtin = Column(Boolean, default=True)                 # 是否内置（内置不可删）
    active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.now)


class Hazard(Base):
    """隐患主表（巡检-整改-复查闭环核心）"""
    __tablename__ = "hazards"
    id = Column(Integer, primary_key=True)
    org_id = Column(Integer, ForeignKey("organizations.id"), nullable=True)  # 所属机构
    code = Column(String(32), unique=True, nullable=False)   # HB-2026-0001
    category = Column(String(32), default="其他")            # 消防/设施/用电/环境/护理...
    hazard_type = Column(String(64), default="")
    title = Column(String(128), nullable=False)
    description = Column(Text, default="")
    level = Column(String(8), default="黄色")                # 红/橙/黄/蓝
    source = Column(String(16), default="文字")              # 拍照/语音/文字/AI识别
    indicator_code = Column(String(16), nullable=True)       # 关联标准库指标（违规考核扣分）
    deducted = Column(Integer, default=0)                    # 关联指标扣分
    reporter_id = Column(Integer, ForeignKey("users.id"))
    space_id = Column(Integer, ForeignKey("spaces.id"), nullable=True)
    status = Column(String(24), default="pending_rectify")   # 见 config.HAZARD_STATUS
    assignee_id = Column(Integer, ForeignKey("users.id"), nullable=True)  # 整改责任人
    deadline = Column(DateTime, nullable=True)               # 整改期限
    photos = Column(JSON, default=list)                      # 照片路径列表（含水印）
    ai_result = Column(JSON, default=dict)                   # AI 识别结构化结果
    voice_text = Column(Text, default="")                    # 语音转写原文
    overdued = Column(Boolean, default=False)
    escalated = Column(Boolean, default=False)               # 是否已升级预警
    created_at = Column(DateTime, default=datetime.now)
    closed_at = Column(DateTime, nullable=True)

    reporter = relationship("User", foreign_keys=[reporter_id])
    assignee = relationship("User", foreign_keys=[assignee_id])
    space = relationship("Space")
    org = relationship("Organization", foreign_keys=[org_id])


class Rectification(Base):
    """整改记录"""
    __tablename__ = "rectifications"
    id = Column(Integer, primary_key=True)
    hazard_id = Column(Integer, ForeignKey("hazards.id"))
    assignee_id = Column(Integer, ForeignKey("users.id"))
    plan = Column(Text, default="")                          # 整改方案
    feedback = Column(Text, default="")                      # 整改说明
    photos = Column(JSON, default=list)                      # 整改后照片
    submitted_at = Column(DateTime, default=datetime.now)


class Review(Base):
    """复查记录"""
    __tablename__ = "reviews"
    id = Column(Integer, primary_key=True)
    hazard_id = Column(Integer, ForeignKey("hazards.id"))
    reviewer_id = Column(Integer, ForeignKey("users.id"))
    result = Column(String(8), nullable=False)               # 通过 / 不通过
    comment = Column(Text, default="")
    reviewed_at = Column(DateTime, default=datetime.now)


class InspectionTask(Base):
    """巡检计划（每日/每周/每月）"""
    __tablename__ = "inspection_tasks"
    id = Column(Integer, primary_key=True)
    title = Column(String(128), nullable=False)
    freq = Column(String(8), default="每周")                 # 每日/每周/每月
    assignee_id = Column(Integer, ForeignKey("users.id"))
    space_ids = Column(JSON, default=list)                   # 巡检范围（空间 id 列表）
    start_date = Column(String(16), default="")
    end_date = Column(String(16), default="")
    active = Column(Boolean, default=True)
    created_by = Column(Integer, ForeignKey("users.id"))
    created_at = Column(DateTime, default=datetime.now)


class TaskInstance(Base):
    """巡检任务实例（按计划生成的具体待办）"""
    __tablename__ = "task_instances"
    id = Column(Integer, primary_key=True)
    task_id = Column(Integer, ForeignKey("inspection_tasks.id"))
    assignee_id = Column(Integer, ForeignKey("users.id"))
    title = Column(String(128), default="")
    due_date = Column(String(16), default="")                # YYYY-MM-DD
    status = Column(String(16), default="待执行")            # 待执行/已完成/已逾期
    completed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.now)


class ComplianceScore(Base):
    """合规考核评分：按标准库指标逐项检查（月度），人工打分留痕"""
    __tablename__ = "compliance_scores"
    id = Column(Integer, primary_key=True)
    org_id = Column(Integer, ForeignKey("organizations.id"), nullable=True)  # 检查对象机构
    indicator_code = Column(String(16), nullable=False)
    period = Column(String(7), nullable=False)               # YYYY-MM
    space_id = Column(Integer, ForeignKey("spaces.id"), nullable=True)
    checked_by = Column(Integer, ForeignKey("users.id"))
    found = Column(Boolean, default=False)                   # 是否发现违规
    deducted = Column(Integer, default=0)                    # 实际扣分（0 或指标分值）
    comment = Column(Text, default="")
    photos = Column(JSON, default=list)
    created_at = Column(DateTime, default=datetime.now)


class ViolationRecord(Base):
    """违规记录（由人工检查或隐患闭环触发，累计扣分/处罚档次依据）"""
    __tablename__ = "violation_records"
    id = Column(Integer, primary_key=True)
    org_id = Column(Integer, ForeignKey("organizations.id"), nullable=True)  # 违规机构
    indicator_code = Column(String(16), nullable=False)
    period = Column(String(7), nullable=False)
    space_id = Column(Integer, ForeignKey("spaces.id"), nullable=True)
    hazard_id = Column(Integer, ForeignKey("hazards.id"), nullable=True)  # 来源隐患
    found_by = Column(Integer, ForeignKey("users.id"))
    deducted = Column(Integer, nullable=False)
    status = Column(String(16), default="整改中")            # 整改中/已整改/已豁免
    source = Column(String(16), default="人工检查")          # 人工检查/隐患闭环
    rectified_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.now)


class AuditLog(Base):
    """操作日志审计（全量留痕）"""
    __tablename__ = "audit_logs"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    username = Column(String(64), default="")
    action = Column(String(64), nullable=False)              # 登录/上报/派单/整改/复查/归档...
    target = Column(String(128), default="")
    detail = Column(Text, default="")
    created_at = Column(DateTime, default=datetime.now)


class ResidentLeave(Base):
    """老人离院记录（门禁/IoT 数据源，已脱敏：仅存匿名编号）
    骗补预警基础数据：连续离院天数 vs 补贴申报状态"""
    __tablename__ = "resident_leaves"
    id = Column(Integer, primary_key=True)
    org_id = Column(Integer, ForeignKey("organizations.id"), nullable=False)
    elder_code = Column(String(16), nullable=False)          # 匿名编号：长者01
    leave_days = Column(Integer, nullable=False)             # 连续离院天数
    is_subsidized = Column(Integer, default=0)               # 机构是否申报补贴 0/1
    source = Column(String(16), default="门禁")              # 数据来源：门禁/雷达/家属确认
    detected_at = Column(DateTime, default=datetime.now)


class Notification(Base):
    """消息中心：待办任务/整改提醒/逾期预警统一归集"""
    __tablename__ = "notifications"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    ntype = Column(String(16), default="系统")               # 待办/整改提醒/逾期预警/系统
    content = Column(Text, default="")
    link = Column(String(32), default="")
    is_read = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.now)


class Report(Base):
    """报告存档（月度/年度）"""
    __tablename__ = "reports"
    id = Column(Integer, primary_key=True)
    title = Column(String(128), nullable=False)
    rtype = Column(String(8), default="月度")                # 月度/年度
    period = Column(String(16), default="")                  # YYYY-MM 或 YYYY
    file_path = Column(String(256), default="")
    summary = Column(Text, default="")
    created_by = Column(Integer, ForeignKey("users.id"))
    created_at = Column(DateTime, default=datetime.now)


class Complaint(Base):
    """投诉举报受理（政府监管渠道：12345 转办 / 来信 / 来电 / 网络）
    登记 → 受理 → 派单核查 → 处理反馈 → 归档，全程留痕审计"""
    __tablename__ = "complaints"
    id = Column(Integer, primary_key=True)
    code = Column(String(32), unique=True, nullable=False)   # TS-2026-0001
    org_id = Column(Integer, ForeignKey("organizations.id"), nullable=True)  # 被投诉机构
    source = Column(String(16), default="来电")              # 12345转办/来信/来电/网络
    category = Column(String(16), default="其他")            # 服务质量/收费问题/安全隐患/虐待老人/其他
    title = Column(String(128), nullable=False)
    content = Column(Text, default="")
    complainant = Column(String(32), default="匿名")          # 投诉人（脱敏：姓氏+称谓）
    phone = Column(String(32), default="")                    # 联系电话（打码）
    level = Column(String(8), default="黄色")                 # 红/橙/黄/蓝（紧急程度）
    status = Column(String(16), default="待受理")             # 待受理/核查中/已办结/已归档/不予受理
    assignee_id = Column(Integer, ForeignKey("users.id"), nullable=True)  # 承办人
    result = Column(Text, default="")                         # 处理结果（办结/不予受理说明）
    hazard_id = Column(Integer, ForeignKey("hazards.id"), nullable=True)  # 转隐患立案关联
    created_by = Column(Integer, ForeignKey("users.id"), nullable=True)   # 登记人
    closed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.now)

    org = relationship("Organization", foreign_keys=[org_id])
    assignee = relationship("User", foreign_keys=[assignee_id])


class License(Base):
    """机构证照备案（民政监管：营业执照 / 备案凭证 / 消防验收 / 食品经营许可）
    到期前 30 天自动标黄「临期」，已过期标红「过期」→ 到期预警"""
    __tablename__ = "licenses"
    id = Column(Integer, primary_key=True)
    org_id = Column(Integer, ForeignKey("organizations.id"), nullable=False)
    lic_type = Column(String(32), nullable=False)             # 证照类型
    lic_no = Column(String(64), default="")                   # 证照号（展示打码）
    issued_at = Column(String(16), default="")                # 发证日期 YYYY-MM-DD
    expire_at = Column(String(16), default="")                # 有效期至 YYYY-MM-DD
    status = Column(String(8), default="有效")                # 有效/临期/过期（展示层计算）
    remark = Column(String(128), default="")
    created_at = Column(DateTime, default=datetime.now)

    org = relationship("Organization", foreign_keys=[org_id])


class AssessmentRecord(Base):
    """老人能力评估备案（政府监管 · 评估结果留痕，护理补贴发放依据）
    依据 MZ/T 039《老年人能力评估规范》四维评估：
    生活自理(0-40) + 认知(0-16) + 情绪行为(0-8) + 视听觉(0-8) = 总分(0-72)
    失能等级映射：自理(>60) / 轻度失能(41-60) / 中度失能(21-40) / 重度失能(<=20)
    评估记录永久留痕（评估机构/评估员/得分明细），老人匿名（elder_id 关联脱敏档案）"""
    __tablename__ = "assessment_records"
    id = Column(Integer, primary_key=True)
    org_id = Column(Integer, ForeignKey("organizations.id"), nullable=False)
    elder_id = Column(Integer, ForeignKey("elders.id"), nullable=False)   # 关联脱敏老人档案
    adl_score = Column(Integer, default=0)                   # 生活自理得分 0-40
    cognition_score = Column(Integer, default=0)             # 认知能力得分 0-16
    emotion_score = Column(Integer, default=0)               # 情绪行为得分 0-8
    sensory_score = Column(Integer, default=0)               # 视听觉得分 0-8
    total_score = Column(Integer, default=0)                 # 总分 0-72
    level = Column(String(16), default="自理")               # 自理/轻度失能/中度失能/重度失能
    assessor = Column(String(32), default="")                # 评估员（打码展示）
    assessor_org = Column(String(64), default="")            # 评估机构
    valid_until = Column(String(16), default="")             # 有效期至（评估+6 个月）
    created_by = Column(Integer, ForeignKey("users.id"), nullable=True)  # 录入监管人员
    created_at = Column(DateTime, default=datetime.now)

    elder = relationship("Elderly", foreign_keys=[elder_id])
    org = relationship("Organization", foreign_keys=[org_id])
