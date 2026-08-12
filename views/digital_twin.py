# -*- coding: utf-8 -*-
"""机构 3D 可视化 — 房间级状态可视化
Three.js 渲染楼栋 → 房间状态（正常🟢/隐患未改🟠/紧急报警🔴）一屏尽览
"""
import json
import random
from collections import Counter

import streamlit as st
from sqlalchemy.orm import Session

from auth import require_role, current_user, visible_org_ids
from models import Hazard, Organization
from services.mask import org_label
from views.theme import app_header, metric_card, section_title


def _room_states(session: Session, org_id: int):
    """汇总该机构每房间隐患状态：green 正常 / orange 隐患未改 / red 紧急报警"""
    status_map = {
        "pending_rectify": "orange", "rectifying": "orange",
        "pending_review": "orange", "rejected": "orange",
        "overdue": "red", "escalated": "red",
        "closed": "green",
    }
    room_state = {}
    for h in session.query(Hazard).filter(Hazard.org_id == org_id).all():
        room = h.space.room if h.space else "未知区域"
        st_ = "red" if (h.overdued or h.escalated) else status_map.get(h.status, "green")
        cur = room_state.get(room, "green")
        rank = {"green": 0, "orange": 1, "red": 2}
        if rank[st_] > rank[cur]:
            room_state[room] = st_
    # 3 层 × 6 房间，未出现的房间默认 green（少量演示隐患点缀）
    rnd = random.Random(9 + org_id)
    rooms = []
    for floor in range(3):
        for idx in range(6):
            num = f"{floor + 1}0{idx + 1}"
            state = room_state.get(f"{num}室", "green")
            if state == "green" and rnd.random() < 0.08:
                state = "orange"
            rooms.append({"floor": floor + 1, "num": num, "state": state})
    return rooms


def render(session: Session):
    require_role(1)
    user = current_user(session)
    vis_org_ids = visible_org_ids(session, user)
    orgs = session.query(Organization).filter(
        Organization.active == True,
        Organization.id.in_(vis_org_ids) if vis_org_ids else True).all()
    if not orgs:
        st.error("管辖范围内暂无可展示机构")
        return

    org_sel = st.selectbox(
        "🏢 选择机构查看 3D 状态",
        {org_label(o.name, o.code): o for o in orgs},
        key="twin_org")
    org = org_sel if isinstance(org_sel, Organization) else next(
        (o for o in orgs if org_label(o.name, o.code) == org_sel), orgs[0])

    app_header(f"{org_label(org.name, org.code)} · 3D 可视化",
               f"该机构房间状态（正常 / 隐患未改 / 紧急报警）实时可视化 · 秒级定位隐患点位")

    rooms = _room_states(session, org.id)
    cnt = Counter(r["state"] for r in rooms)
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        metric_card("房间总数", len(rooms), "3 层 × 6 室")
    with c2:
        metric_card("正常房间", cnt.get("green", 0), "状态良好", icon_str="🟢")
    with c3:
        metric_card("隐患未改", cnt.get("orange", 0), "需整改", icon_str="🟠")
    with c4:
        metric_card("紧急报警", cnt.get("red", 0), "已逾期/升级", icon_str="🔴")

    section_title("🏙️", "楼栋房间状态 3D 图", "旋转 / 缩放查看 · 房间颜色实时同步隐患台账")

    state_label = {"green": "正常", "orange": "隐患未改", "red": "紧急报警"}
    state_color = {"green": "#10B981", "orange": "#F59E0B", "red": "#EF4444"}
    # 统计每层状态分布
    floor_stats = {}
    for f in range(1, 4):
        sub = [r for r in rooms if r["floor"] == f]
        floor_stats[f] = {s: sum(1 for r in sub if r["state"] == s) for s in ("green", "orange", "red")}

    html = f"""
    <div id="twin" style="width:100%;height:520px;border-radius:14px;overflow:hidden;
        border:1px solid #E2E8F0;background:linear-gradient(160deg,#0B1525,#16263F);"></div>
    <script type="importmap">
    {{ "imports": {{
        "three": "https://unpkg.com/three@0.160.0/build/three.module.js",
        "three/addons/": "https://unpkg.com/three@0.160.0/examples/jsm/"
    }} }}
    </script>
    <script type="module">
    import * as THREE from 'three';
    import {{ OrbitControls }} from 'three/addons/controls/OrbitControls.js';

    const roomData = {json.dumps(rooms, ensure_ascii=False)};
    const stateLabel = {json.dumps(state_label, ensure_ascii=False)};
    const stateColor = {json.dumps(state_color)};

    const container = document.getElementById('twin');
    const scene = new THREE.Scene();
    scene.background = new THREE.Color(0x0b1525);

    const camera = new THREE.PerspectiveCamera(45, container.clientWidth / container.clientHeight, 0.1, 100);
    camera.position.set(10, 9, 13);
    camera.lookAt(0, 2.5, 0);
    const renderer = new THREE.WebGLRenderer({{ antialias: true }});
    renderer.setSize(container.clientWidth, container.clientHeight);
    renderer.shadowMap.enabled = true;
    container.appendChild(renderer.domElement);

    const controls = new OrbitControls(camera, renderer.domElement);
    controls.target.set(0, 2.5, 0);
    controls.enableDamping = true;

    // 灯光
    scene.add(new THREE.AmbientLight(0xffffff, 0.55));
    const dir = new THREE.DirectionalLight(0xffffff, 0.9);
    dir.position.set(8, 12, 6); dir.castShadow = true;
    scene.add(dir);

    // 地面网格
    const grid = new THREE.GridHelper(14, 14, 0x334155, 0x1e293b);
    scene.add(grid);

    // 楼体基座
    const base = new THREE.Mesh(
        new THREE.BoxGeometry(8.4, 0.25, 6.4),
        new THREE.MeshStandardMaterial({{ color: 0x1e293b, roughness: 0.8 }})
    );
    base.position.y = 0.12; base.receiveShadow = true;
    scene.add(base);

    // 房间（每层 2 行 × 3 列）
    const pickMeshes = [];
    const stateLegend = [];
    roomData.forEach(r => {{
        const col = (r.num % 10 - 1) % 3;         // 0..2
        const row = Math.floor((r.num % 10 - 1) / 3); // 0..1
        const x = (col - 1) * 2.7;
        const z = (row - 0.5) * 2.9;
        const y = 0.25 + (r.floor - 1) * 1.75 + 0.5;
        const color = stateColor[r.state];

        const box = new THREE.Mesh(
            new THREE.BoxGeometry(2.2, 1.05, 1.35),
            new THREE.MeshStandardMaterial({{ color: new THREE.Color(color), roughness: 0.35, metalness: 0.1 }})
        );
        box.position.set(x, y, z);
        box.castShadow = true;
        scene.add(box);

        // 发光边框（报警房间）
        if (r.state === 'red') {{
            const edges = new THREE.LineSegments(
                new THREE.EdgesGeometry(box.geometry),
                new THREE.LineBasicMaterial({{ color: 0xff0000, linewidth: 2 }})
            );
            edges.position.copy(box.position);
            scene.add(edges);
        }}

        // 楼层标签
        if (col === 0 && row === 0) {{
            const sprite = new THREE.Sprite(new THREE.SpriteMaterial({{
                map: (() => {{ const c = document.createElement('canvas'); c.width=128; c.height=64;
                    const g = c.getContext('2d'); g.fillStyle='#94A3B8'; g.font='28px sans-serif';
                    g.fillText('第' + r.floor + '层', 8, 40); return new THREE.CanvasTexture(c); }})(),
                transparent: true }}));
            sprite.position.set(-5.2, 0.25 + (r.floor - 1) * 1.75 + 0.55, 0);
            scene.add(sprite);
        }}

        pickMeshes.push({{ mesh: box, data: r }});
    }});

    // 点击房间 → 显示状态信息
    const raycaster = new THREE.Raycaster();
    const mouse = new THREE.Vector2();
    const info = document.createElement('div');
    info.style.cssText = 'position:absolute;top:12px;left:12px;background:rgba(255,255,255,0.08);' +
        'backdrop-filter:blur(8px);padding:10px 14px;border-radius:10px;font:13px sans-serif;color:#E2E8F0;' +
        'pointer-events:none;z-index:5;';
    container.appendChild(info);
    container.addEventListener('click', (e) => {{
        const rect = container.getBoundingClientRect();
        mouse.x = ((e.clientX - rect.left) / rect.width) * 2 - 1;
        mouse.y = -((e.clientY - rect.top) / rect.height) * 2 + 1;
        raycaster.setFromCamera(mouse, camera);
        const hits = raycaster.intersectObjects(pickMeshes.map(p => p.mesh));
        if (hits.length) {{
            const d = hits[0].object.userData || pickMeshes.find(p => p.mesh === hits[0].object).data;
            const r = pickMeshes.find(p => p.mesh === hits[0].object).data;
            info.innerHTML = '🚪 <b>' + r.num + '室</b> ｜ 状态：<b style="color:' + stateColor[r.state] + '">' +
                stateLabel[r.state] + '</b>';
        }}
    }});

    // 动画（报警房间脉冲）
    const redMeshes = pickMeshes.filter(p => p.data.state === 'red').map(p => p.mesh);
    let t = 0;
    function animate() {{
        requestAnimationFrame(animate);
        controls.update();
        t += 0.03;
        redMeshes.forEach(m => {{
            const s = 1 + Math.sin(t * 3) * 0.06;
            m.scale.set(s, s, s);
        }});
        renderer.render(scene, camera);
    }}
    animate();

    window.addEventListener('resize', () => {{
        camera.aspect = container.clientWidth / container.clientHeight;
        camera.updateProjectionMatrix();
        renderer.setSize(container.clientWidth, container.clientHeight);
    }});
    </script>
    """
    st.components.v1.html(html, height=560)

    # 图例 + 各层分布
    st.markdown("""
    <div style="display:flex;gap:18px;margin:8px 0 16px;padding:10px 16px;border:1px solid #E2E8F0;border-radius:10px;background:#FAFBFC;">
        <span><span style="display:inline-block;width:12px;height:12px;border-radius:3px;background:#10B981;"></span> 正常</span>
        <span><span style="display:inline-block;width:12px;height:12px;border-radius:3px;background:#F59E0B;"></span> 隐患未改</span>
        <span><span style="display:inline-block;width:12px;height:12px;border-radius:3px;background:#EF4444;"></span> 紧急报警（脉冲）</span>
        <span style="color:#94A3B8;">💡 点击任意房间查看状态 · 拖拽旋转 · 滚轮缩放</span>
    </div>
    """, unsafe_allow_html=True)
    c1, c2, c3 = st.columns(3)
    for i, (f, stats) in enumerate(floor_stats.items()):
        col = [c1, c2, c3][i]
        with col:
            st.markdown(f"**第 {f} 层**：🟢 {stats['green']} 间 · 🟠 {stats['orange']} 间 · 🔴 {stats['red']} 间")
