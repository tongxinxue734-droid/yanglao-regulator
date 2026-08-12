# -*- coding: utf-8 -*-
"""种子数据：账号、空间档案、指标库、演示闭环数据"""
import random
from datetime import datetime, timedelta

import bcrypt
from sqlalchemy.orm import Session

import config
from models import (User, Organization, Space, Indicator, Hazard, Rectification, Review,
                    InspectionTask, TaskInstance, ComplianceScore,
                    ViolationRecord, Notification, AuditLog, ResidentLeave, Elderly, Complaint, License,
                    AssessmentRecord)
from indicators import BUILTIN_INDICATORS

# 虚拟（脱敏）养老机构 —— 演示多机构评分体系（8 个，覆盖西安市各区县）
# 依据政务数据脱敏规范：地址仅到区/路段（不包含门牌号），电话截断，法人打码
VIRTUAL_ORGS = [
    # --- 西安本地机构 ---
    dict(name="云栖养老服务中心", code="ORG-001", address="西安市雁塔区云栖路",
         org_type="民办", level="三星级", capacity=320, legal_person="林*", manager_name="周*明",
         phone="139****0001", license_status="在营"),
    dict(name="康悦颐养中心", code="ORG-002", address="西安市莲湖区康悦大道",
         org_type="民办", level="四星级", capacity=450, legal_person="陈*", manager_name="吴*芳",
         phone="139****0002", license_status="在营"),
    dict(name="西安市福康居养老院", code="ORG-003", address="西安市碑林区福康巷",
         org_type="公办", level="二星级", capacity=180, legal_person="赵*", manager_name="孙*国",
         phone="139****0003", license_status="在营"),
    dict(name="乐龄家园养老服务中心", code="ORG-004", address="西安市未央区乐龄路",
         org_type="民办", level="五星级", capacity=600, legal_person="许*", manager_name="李*清",
         phone="139****0004", license_status="在营"),
    # --- 西安其他区县 ---
    dict(name="长安福寿养老服务中心", code="ORG-005", address="西安市长安区福寿路",
         org_type="公办", level="三星级", capacity=240, legal_person="马*", manager_name="钱*芳",
         phone="139****0005", license_status="在营"),
    dict(name="灞桥颐和养老院", code="ORG-006", address="西安市灞桥区颐和路",
         org_type="民办", level="二星级", capacity=120, legal_person="张*", manager_name="刘*华",
         phone="139****0006", license_status="在营"),
    dict(name="新城松鹤养老服务中心", code="ORG-007", address="西安市新城区松鹤巷",
         org_type="民办", level="四星级", capacity=390, legal_person="黄*", manager_name="周*兰",
         phone="139****0007", license_status="在营"),
    dict(name="临潼骊山老年公寓", code="ORG-008", address="西安市临潼区骊山大道",
         org_type="公办", level="二星级", capacity=150, legal_person="杨*", manager_name="王*美",
         phone="139****0008", license_status="在营"),
]


def hash_pw(pw: str) -> str:
    return bcrypt.hashpw(pw.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def seed_all(session: Session, with_demo: bool = True):
    """初始化基础数据。with_demo=False 时仅建账号与指标库。"""
    # ---- 指标库（39 条内置，幂等） ----
    if session.query(Indicator).count() == 0:
        for ind in BUILTIN_INDICATORS:
            session.add(Indicator(
                code=ind["code"], category=ind["category"], item=ind["item"],
                content=ind["content"], law_basis=ind.get("law_basis", ""),
                remark=ind.get("remark", ""), deduct=ind["deduct"], builtin=True,
            ))
        session.flush()

    # ---- 虚拟机构（幂等，政府人员账号引用） ----
    if session.query(Organization).count() == 0:
        for org in VIRTUAL_ORGS:
            session.add(Organization(**org))
        session.flush()
    orgs = session.query(Organization).order_by(Organization.id).all()

    # ---- 账号（幂等）：政府监管人员体系 ----
    if session.query(User).count() == 0:
        admin = User(username="admin", password_hash=hash_pw("admin123"), name="王建国",
                     role_level=1, dept_name="市民政局养老服务科", phone="138****0001",
                     org_ids=[o.id for o in orgs])
        m1 = User(username="li", password_hash=hash_pw("123456"), name="李慧敏",
                  role_level=2, dept_name="雁塔区民政局", parent_id=1, phone="138****0002",
                  org_ids=[orgs[0].id, orgs[2].id, orgs[4].id, orgs[6].id])  # 雁塔/碑林/长安/新城
        m2 = User(username="wang", password_hash=hash_pw("123456"), name="王志强",
                  role_level=2, dept_name="莲湖区民政局", parent_id=1, phone="138****0003",
                  org_ids=[orgs[1].id, orgs[3].id, orgs[5].id, orgs[7].id])  # 莲湖/未央/灞桥/临潼
        session.add_all([admin, m1, m2])
        session.flush()
        session.add_all([
            User(username="zhao", password_hash=hash_pw("123456"), name="赵文静",
                 role_level=3, dept_name="雁塔区民政检查队", parent_id=m1.id, phone="138****0004",
                 org_ids=m1.org_ids),
            User(username="qian", password_hash=hash_pw("123456"), name="钱志远",
                 role_level=3, dept_name="雁塔区民政检查队", parent_id=m1.id, phone="138****0005",
                 org_ids=m1.org_ids),
            User(username="sun", password_hash=hash_pw("123456"), name="孙丽华",
                 role_level=3, dept_name="莲湖区民政检查队", parent_id=m2.id, phone="138****0006",
                 org_ids=m2.org_ids),
        ])
        session.flush()

    if not with_demo:
        session.commit()
        return

    # ---- 空间档案 ----
    if session.query(Space).count() == 0:
        users = {u.username: u for u in session.query(User).all()}
        spaces = [
            Space(building="一号楼", floor="1层", room="101室", space_type="房间", manager_id=users["qian"].id, check_standard="每日巡检：用电/消防/地面"),
            Space(building="一号楼", floor="1层", room="102室", space_type="房间", manager_id=users["qian"].id, check_standard="每日巡检：用电/消防/地面"),
            Space(building="一号楼", floor="1层", room="103室", space_type="房间", manager_id=users["qian"].id, check_standard="每日巡检：用电/消防/地面"),
            Space(building="一号楼", floor="1层", room="活动室", space_type="公共区域", manager_id=users["sun"].id, check_standard="每日巡检：环境/设施"),
            Space(building="一号楼", floor="1层", room="走廊", space_type="公共区域", manager_id=users["sun"].id, check_standard="每日巡检：消防通道/照明"),
            Space(building="一号楼", floor="2层", room="201室", space_type="房间", manager_id=users["sun"].id, check_standard="每日巡检：用电/消防/地面"),
            Space(building="一号楼", floor="2层", room="202室", space_type="房间", manager_id=users["sun"].id, check_standard="每日巡检：用电/消防/地面"),
            Space(building="二号楼", floor="1层", room="食堂", space_type="公共区域", manager_id=users["zhao"].id, check_standard="食品/燃气/消防"),
            Space(building="二号楼", floor="1层", room="医务室", space_type="公共区域", manager_id=users["zhao"].id, check_standard="药品/医疗/用电"),
        ]
        session.add_all(spaces)
        session.flush()

    # ---- 在院老人档案（演示数据 · 已脱敏存储，共 521 条分布在 8 个机构） ----
    # 脱敏规则：姓名只存「姓氏+称谓」；手机/身份证存模拟号、展示层打码；
    # 家属打码；年龄存数值、展示层范围化；数据为抽样替代，非真实人员
    if session.query(Elderly).count() == 0:
        now = datetime.now()
        rnd = random.Random(20260812)
        surnames = ["张", "李", "王", "刘", "陈", "杨", "黄", "周", "吴", "徐", "孙", "胡",
                    "朱", "高", "林", "何", "郭", "马", "罗", "梁", "宋", "郑", "谢", "韩",
                    "唐", "冯", "于", "董", "程", "曹", "袁", "邓", "许", "傅", "沈", "曾", "彭"]
        honor_m = ["爷爷", "大爷"]
        honor_f = ["奶奶", "大娘"]
        # 能力等级分布：自理 22% / 轻度失能 30% / 中度失能 28% / 重度失能 20%
        levels = (["自理"] * 22 + ["轻度失能"] * 30 + ["中度失能"] * 28 + ["重度失能"] * 20)
        # 每机构在院老人数（按核定床位数比例分配，合计 521 条 ≥ 500）
        per_org = [68, 95, 38, 128, 51, 26, 83, 32]
        elders = []
        for org, n in zip(orgs, per_org):
            for k in range(1, n + 1):
                gender = rnd.choice(["男", "女"])
                surname = rnd.choice(surnames)
                honor = rnd.choice(honor_m) if gender == "男" else rnd.choice(honor_f)
                age = rnd.randint(72, 96)
                health = rnd.choice(levels)
                days_since = rnd.randint(0, 400)          # 距最近评估天数
                admitted = (now - timedelta(days=rnd.randint(30, 2500))).strftime("%Y-%m-%d")
                assessed = (now - timedelta(days=days_since)).strftime("%Y-%m-%d")
                building = rnd.choice(["一号楼", "二号楼"])
                floor = rnd.randint(1, 6)
                room = f"{building}{floor}层{rnd.randint(1, 30):02d}室"
                phone = "13" + rnd.choice("987") + "".join(str(rnd.randint(0, 9)) for _ in range(8))
                birth = str(now.year - age)                # 模拟出生年
                id_card = ("6101" + birth
                           + "".join(str(rnd.randint(0, 9)) for _ in range(8))
                           + f"{rnd.randint(0, 99):02d}")
                elders.append(Elderly(
                    org_id=org.id, code=f"{org.code}-{k:04d}",
                    name=f"{surname}{honor}", gender=gender, age=age,
                    health_level=health, room=room, phone=phone, id_card=id_card,
                    guardian=f"{surname}*", admitted_at=admitted, assessed_at=assessed,
                    assessment_valid=days_since <= 180, status="在院",
                ))
        session.add_all(elders)
        session.flush()

    # ---- 演示闭环数据（近 90 天） ----
    if session.query(Hazard).count() == 0:
        users = {u.username: u for u in session.query(User).all()}
        spaces = session.query(Space).all()
        if not spaces or not {"zhao", "qian", "sun"}.issubset(users):
            session.commit()
            return  # 缺少演示账号或空间档案时跳过演示数据
        ind_map = {i.code: i for i in session.query(Indicator).all()}

        demo = [
            # (天数前, 类别, 类型, 标题, 等级, 来源, 指标码, 上报人, 空间idx, 状态, 责任人, 闭环天数)
            # ---- 原 12 条 ----
            (2, "消防", "消防通道堵塞", "走廊堆放杂物堵塞消防通道", "红色", "拍照", "B3", "qian", 4, "closed", "qian", 1),
            (8, "设施", "扶手松动", "活动室门口无障碍扶手松动", "橙色", "AI识别", "B6", "qian", 3, "closed", "sun", 3),
            (15, "用电", "插座裸露", "102室床头插座面板破损裸露", "红色", "拍照", None, "zhao", 1, "closed", "zhao", 2),
            (20, "环境", "杂物堆积", "201室门口杂物堆积影响通行", "黄色", "文字", None, "sun", 5, "closed", "sun", 4),
            (30, "设施", "床栏损坏", "103室床栏卡扣损坏", "橙色", "拍照", None, "zhao", 2, "closed", "zhao", 5),
            (25, "护理", "药品乱放", "医务室药品未按处方分类存放", "橙色", "语音", "D4", "zhao", 8, "rectifying", "zhao", None),
            (40, "消防", "灭火器过期", "二号楼食堂灭火器压力不足", "橙色", "AI识别", "B2", "qian", 7, "closed", "qian", 6),
            (45, "环境", "积水积冰", "一层走廊地面湿滑无警示牌", "黄色", "拍照", None, "sun", 4, "closed", "sun", 2),
            (12, "用电", "电线私拉乱接", "活动室空调插座私拉插线板", "黄色", "拍照", None, "qian", 3, "pending_review", "sun", 3),
            (50, "消防", "应急灯故障", "走廊应急照明灯故障不亮", "橙色", "文字", None, "qian", 4, "closed", "sun", 4),
            (60, "环境", "光线不足", "201室照明灯亮度不足", "蓝色", "文字", None, "sun", 5, "closed", "sun", 3),
            (5, "食品", "食品存放不规范", "食堂留样冰箱温度记录缺失", "橙色", "语音", "D8", "zhao", 7, "rectifying", "zhao", None),
            # ---- 新增 24 条：更多机构 / 指标 / 状态 ----
            (9, "消防", "灭火器缺失", "101室灭火器被挪作他用", "红色", "AI识别", "B1", "qian", 0, "closed", "qian", 2),
            (18, "设施", "呼叫器离线", "202室床头呼叫器电池耗尽快配", "橙色", "拍照", None, "sun", 6, "closed", "sun", 4),
            (22, "护理", "约束带违规使用", "103室老人未按评估使用约束带", "红色", "语音", "C5", "zhao", 2, "rectifying", "zhao", None),
            (28, "用电", "大功率违规电器", "活动室发现违规电热毯", "橙色", "拍照", "B4", "qian", 3, "closed", "qian", 5),
            (35, "环境", "地面障碍物", "一层走廊轮椅停放阻塞通道", "黄色", "文字", None, "sun", 4, "closed", "sun", 2),
            (42, "消防", "安全出口遮挡", "二号楼安全出口被杂物遮挡", "红色", "拍照", "B3", "qian", 7, "closed", "qian", 3),
            (55, "设施", "防滑垫缺失", "医务室卫生间未铺设防滑垫", "黄色", "文字", None, "zhao", 8, "closed", "zhao", 2),
            (65, "食品", "后厨卫生不达标", "食堂操作间未按时消毒", "黄色", "AI识别", "D8", "qian", 7, "closed", "sun", 4),
            (70, "用药", "药品过期", "医务室急救药品已过有效期", "橙色", "拍照", "D4", "zhao", 8, "pending_review", "zhao", 3),
            (3, "消防", "应急灯故障", "101室走廊应急照明灯损坏", "橙色", "文字", None, "sun", 0, "closed", "sun", 1),
            (13, "用电", "线路老化", "202室空调插座线路绝缘老化", "橙色", "AI识别", None, "qian", 6, "rectifying", "qian", None),
            (19, "环境", "杂物堆积", "活动室角落杂物长期未清理", "蓝色", "文字", None, "sun", 3, "closed", "sun", 4),
            (27, "设施", "床栏松动", "202室床栏螺丝松动摇晃", "橙色", "拍照", None, "zhao", 6, "closed", "zhao", 3),
            (33, "食品", "食品留样不规范", "食堂未按要求留样48小时", "橙色", "语音", "D8", "qian", 7, "pending_review", "sun", 3),
            (38, "护理", "锐器无收纳", "医务室使用后针头未入利器盒", "红色", "拍照", "C5", "zhao", 8, "closed", "zhao", 1),
            (48, "消防", "消防栓遮挡", "走廊消防栓被立柜遮挡", "橙色", "文字", None, "sun", 4, "closed", "sun", 3),
            (52, "设施", "门窗损坏", "101室窗户把手断裂无法关闭", "黄色", "拍照", None, "qian", 0, "closed", "qian", 2),
            (58, "环境", "光线不足", "医务室灯光照度不达标", "蓝色", "文字", None, "zhao", 8, "closed", "zhao", 3),
            (7, "消防", "灭火器过期", "202室灭火器压力表红区", "橙色", "AI识别", "B2", "qian", 6, "closed", "qian", 2),
            (14, "用电", "插座裸露", "活动室墙插面板损坏电线外露", "红色", "拍照", None, "sun", 3, "closed", "sun", 1),
            (21, "食品", "食堂卫生", "后厨垃圾桶未加盖", "黄色", "语音", "D8", "qian", 7, "closed", "zhao", 3),
            (26, "设施", "防滑垫缺失", "101室卫生间防滑垫老化破损", "黄色", "文字", None, "sun", 0, "closed", "sun", 2),
            (31, "护理", "药品管理", "老人自备药未统一管理", "橙色", "拍照", "D4", "zhao", 2, "rectifying", "zhao", None),
        ]
        now = datetime.now()
        orgs = session.query(Organization).order_by(Organization.id).all()
        for i, (days_ago, cat, htype, title, lvl, src, ind_code, reporter, sp_idx, status, assignee, close_days) in enumerate(demo):
            created = now - timedelta(days=days_ago)
            ded = ind_map[ind_code].deduct if ind_code and ind_code in ind_map else 0
            deadline = created + timedelta(days=config.HAZARD_LEVELS.get(lvl, {"days": 7})["days"])
            org = orgs[i % len(orgs)]  # 隐患轮流归属虚拟机构
            h = Hazard(
                code=f"HB-2026-{i+1:04d}", category=cat, hazard_type=htype, title=title,
                description=title, level=lvl, source=src,
                indicator_code=ind_code, deducted=ded, org_id=org.id,
                reporter_id=users[reporter].id, space_id=spaces[sp_idx].id,
                status=status, assignee_id=users[assignee].id, deadline=deadline,
                created_at=created,
                closed_at=(created + timedelta(days=close_days)) if status in ("closed",) else None,
            )
            session.add(h)
            session.flush()
            if status in ("closed", "pending_review"):
                session.add(Rectification(hazard_id=h.id, assignee_id=users[assignee].id,
                                          plan="排查并整改", feedback="已完成整改，现场复查合格",
                                          submitted_at=created + timedelta(days=close_days - 1)))
            if status == "closed":
                session.add(Review(hazard_id=h.id, reviewer_id=users["qian"].id,
                                   result="通过", comment="复查合格，闭环归档",
                                   reviewed_at=created + timedelta(days=close_days)))
                if ind_code:
                    period = created.strftime("%Y-%m")
                    session.add(ViolationRecord(indicator_code=ind_code, period=period, org_id=org.id,
                                                space_id=h.space_id, hazard_id=h.id,
                                                found_by=h.reporter_id, deducted=ded,
                                                status="已整改", source="隐患闭环",
                                                rectified_at=h.closed_at, created_at=created))
        session.flush()

        # ---- 人工合规检查记录（近 6 个月，按机构检查打分） ----
        if session.query(ComplianceScore).count() == 0:
            rnd = random.Random(42)
            periods = [(now - timedelta(days=30 * k)).strftime("%Y-%m") for k in range(1, 7)]
            inds = session.query(Indicator).all()
            for org_i, org in enumerate(orgs):
                # 每个机构命中率不同（模拟不同机构合规水平）
                hit = [0.04, 0.08, 0.15, 0.02, 0.06, 0.18, 0.03, 0.10][org_i % 8]
                for period in periods:
                    for ind in inds:
                        found = rnd.random() < hit
                        session.add(ComplianceScore(
                            indicator_code=ind.code, period=period, org_id=org.id,
                            checked_by=users["admin"].id,
                            found=found, deducted=ind.deduct if found else 0,
                            comment=f"{org.code} 月度合规检查" if found else "",
                        ))
            session.flush()

        # ---- 巡检计划与实例 ----
        if session.query(InspectionTask).count() == 0:
            t = InspectionTask(title="一号楼每日安全巡检", freq="每日",
                               assignee_id=users["qian"].id,
                               space_ids=[s.id for s in spaces[:6]],
                               start_date=(now - timedelta(days=30)).strftime("%Y-%m-%d"),
                               end_date=(now + timedelta(days=60)).strftime("%Y-%m-%d"),
                               created_by=users["admin"].id)
            session.add(t)
            session.flush()
            for k in range(5):
                due = now - timedelta(days=k)
                session.add(TaskInstance(task_id=t.id, assignee_id=users["qian"].id,
                                         title=t.title, due_date=due.strftime("%Y-%m-%d"),
                                         status="已完成" if k > 0 else "待执行",
                                         completed_at=(now - timedelta(days=k)) if k > 0 else None))

        # ---- 老人离院记录（门禁/IoT 数据源 · 已脱敏，骗补预警基础数据） ----
        if session.query(ResidentLeave).count() == 0:
            rnd = random.Random(777)
            for org in orgs:
                for k in range(rnd.randint(3, 6)):
                    leave_days = rnd.choice([2, 5, 9, 12, 15, 16, 18, 21, 28])
                    subsidized = rnd.random() < 0.55
                    session.add(ResidentLeave(
                        org_id=org.id,
                        elder_code=f"长者{rnd.randint(1, 99):02d}",
                        leave_days=leave_days,
                        is_subsidized=1 if subsidized else 0,
                        source=rnd.choice(["门禁", "雷达", "家属确认"]),
                        detected_at=now - timedelta(days=rnd.randint(0, 3))))

        # ---- 投诉举报受理（政府监管 · 12345 转办等渠道） ----
        if session.query(Complaint).count() == 0:
            comps = [
                # (机构idx, 来源, 类别, 标题, 内容, 等级, 投诉人, 电话, 状态, 承办人, 结果, 天前)
                (0, "12345转办", "收费问题", "家属反映押金退还拖延",
                 "市民反映：老人入院缴纳的 2000 元押金，办理退院手续后 3 个月仍未退还，多次催促无果。",
                 "橙色", "赵*", "186****2211", "已办结", "qian",
                 "已约谈机构负责人，责令 7 日内退还押金并致电投诉人致歉，押金已于当日原路退回。", 12),
                (1, "网络", "服务质量", "伙食质量差引家属不满",
                 "网民反映：机构食堂菜品种类单一、荤素搭配不合理，老人普遍反映吃不饱。",
                 "黄色", "钱*", "137****3344", "核查中", "qian",
                 "", 3),
                (2, "来电", "安全隐患", "楼道堆放杂物阻塞消防通道",
                 "家属探视时发现三楼走廊堆放大量杂物，堵塞消防通道，存在安全隐患。",
                 "红色", "孙*", "158****5566", "核查中", "sun",
                 "", 1),
                (3, "来信", "虐待老人", "疑似护理员态度粗暴",
                 "匿名来信反映：某护理员在照护过程中言语粗暴、动作粗鲁，老人情绪明显低落。",
                 "红色", "李*", "139****7788", "待受理", None,
                 "", 0),
                (4, "来电", "服务质量", "老人反映洗澡服务安排不合理",
                 "现场来电：机构每周仅安排一次集中洗澡，失能老人排队时间过长，冬季易感冒。",
                 "黄色", "周*", "188****9900", "已归档", "sun",
                 "已反馈机构调整洗澡安排为每周两次并增派护理人员协助，老人家属确认满意，已归档。", 45),
                (5, "12345转办", "收费问题", "涉嫌重复收取护理费",
                 "投诉人：同一护理项目被同时计入基础护理费和增值服务费，怀疑重复收费。",
                 "橙色", "吴*", "133****1122", "已办结", "qian",
                 "已核查收费明细，确认系系统录入重复，责令机构双倍退还多收费用并整改收费系统。", 20),
            ]
            users = {u.username: u for u in session.query(User).all()}
            now = datetime.now()
            for i, (oi, src, cat, title, content, lvl, cname, cphone, status, assignee, result, days_ago) in enumerate(comps):
                created = now - timedelta(days=days_ago)
                closed = (created + timedelta(days=3)) if status in ("已办结", "已归档", "不予受理") else None
                session.add(Complaint(
                    code=f"TS-2026-{i + 1:04d}", org_id=orgs[oi].id, source=src, category=cat,
                    title=title, content=content, level=lvl,
                    complainant=cname, phone=cphone, status=status,
                    assignee_id=users[assignee].id if assignee else None,
                    result=result, created_by=users["admin"].id,
                    created_at=created, closed_at=closed))
            session.flush()

        # ---- 机构证照备案（营业执照/备案凭证/消防验收/食品许可） ----
        if session.query(License).count() == 0:
            lic_data = [
                # (机构idx, 类型, 证照号, 发证日期, 有效期至, 备注)
                (0, "营业执照", "91610113MA6******", "2023-03-15", "2099-12-31", "长期有效"),
                (0, "养老机构备案凭证", "XA-MZ-BA-2023-001", "2023-04-01", "2026-10-01", "备案制"),
                (0, "消防验收合格证明", "XA-XF-YS-2023-011", "2023-03-20", "2026-09-20", ""),
                (0, "食品经营许可证", "JY36101131******", "2023-04-10", "2026-08-15", "临近到期"),
                (1, "营业执照", "91610104MA6******", "2022-08-08", "2099-12-31", "长期有效"),
                (1, "养老机构备案凭证", "XA-MZ-BA-2022-017", "2022-09-01", "2025-09-01", "已过期！"),
                (1, "消防验收合格证明", "XA-XF-YS-2022-023", "2022-08-20", "2027-08-20", ""),
                (2, "营业执照", "91610103MA6******", "2021-05-12", "2099-12-31", "长期有效"),
                (2, "养老机构备案凭证", "XA-MZ-BA-2021-009", "2021-06-01", "2026-06-01", ""),
                (2, "食品经营许可证", "JY36101032******", "2021-06-20", "2026-06-20", ""),
                (3, "营业执照", "91610112MA6******", "2024-01-01", "2099-12-31", "长期有效"),
                (3, "养老机构备案凭证", "XA-MZ-BA-2024-002", "2024-01-15", "2027-01-15", ""),
                (4, "营业执照", "91610116MA6******", "2020-10-10", "2099-12-31", "长期有效"),
                (4, "消防验收合格证明", "XA-XF-YS-2020-008", "2020-10-25", "2025-10-25", "已过期！"),
                (5, "养老机构备案凭证", "XA-MZ-BA-2022-031", "2022-11-01", "2025-11-01", "已过期！"),
                (6, "营业执照", "91610102MA6******", "2023-07-07", "2099-12-31", "长期有效"),
                (6, "食品经营许可证", "JY36101030******", "2023-07-25", "2026-07-25", ""),
                (7, "养老机构备案凭证", "XA-MZ-BA-2023-022", "2023-05-01", "2026-05-01", ""),
                (7, "消防验收合格证明", "XA-XF-YS-2023-005", "2023-05-10", "2026-11-10", ""),
            ]
            for (oi, ltype, lno, issued, expire, remark) in lic_data:
                session.add(License(
                    org_id=orgs[oi].id, lic_type=ltype, lic_no=lno,
                    issued_at=issued, expire_at=expire, remark=remark))
            session.flush()

        # ---- 老人能力评估备案（MZ/T 039 四维量表 · 留痕供补贴/护患比依据） ----
        if session.query(AssessmentRecord).count() == 0:
            from services.assessment import calc_level, calc_valid_until
            elders_all = session.query(Elderly).order_by(Elderly.id).all()
            rnd = random.Random(20260813)
            assessors = ["刘评估", "陈评估", "张评估"]
            assessor_orgs = ["西安市养老服务评估中心", "雁塔区老年能力评估站", "莲湖区养老服务评估站"]
            # 抽样 60 位老人生成评估备案（覆盖四档等级），其余老人维持档案默认等级
            sampled = rnd.sample(elders_all, min(60, len(elders_all)))
            now = datetime.now()
            for i, e in enumerate(sampled):
                # 按老人档案 health_level 反推量表得分区间（保证演示数据自洽）
                lvl_brackets = {
                    "自理": (61, 72), "轻度失能": (41, 60),
                    "中度失能": (21, 40), "重度失能": (5, 20),
                }
                lo, hi = lvl_brackets.get(e.health_level, (41, 60))
                total = rnd.randint(lo, hi)
                # 拆分为四维得分（保证加和=total 且不超过各维满分）
                adl = min(40, rnd.randint(max(0, total - 32), min(40, total)))
                rest = total - adl
                cog = min(16, rnd.randint(max(0, rest - 16), min(16, rest)))
                rest2 = rest - cog
                emo = min(8, rnd.randint(max(0, rest2 - 8), min(8, rest2)))
                sen = rest2 - emo
                assess_date = now - timedelta(days=rnd.randint(5, 190))
                valid_until = calc_valid_until(assess_date.strftime("%Y-%m-%d"))
                session.add(AssessmentRecord(
                    org_id=e.org_id, elder_id=e.id,
                    adl_score=adl, cognition_score=cog, emotion_score=emo, sensory_score=sen,
                    total_score=total, level=calc_level(total),
                    assessor=rnd.choice(assessors), assessor_org=rnd.choice(assessor_orgs),
                    valid_until=valid_until, created_by=users["admin"].id,
                    created_at=assess_date))
            session.flush()

        # ---- 系统消息 ----
        session.add(Notification(user_id=users["qian"].id, ntype="逾期预警",
                                 content="存在 1 项隐患即将/已经逾期，请尽快处理。", link="隐患台账"))
        session.add(Notification(user_id=users["admin"].id, ntype="系统",
                                 content="欢迎使用养老机构安全巡检与合规考核系统。"))
        session.add(AuditLog(user_id=users["admin"].id, username="admin",
                             action="系统初始化", target="seed", detail="初始化演示数据"))

    session.commit()

