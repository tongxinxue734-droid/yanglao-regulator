# -*- coding: utf-8 -*-
"""Three.js 3D 组件：楼栋风险可视化 + 粒子背景（通过 st.components 嵌入）
CDN: unpkg three@0.160.0 + OrbitControls
"""
import json

import streamlit as st

THREE_CDN = "https://unpkg.com/three@0.160.0/build/three.module.js"
ORBIT_CDN = "https://unpkg.com/three@0.160.0/examples/jsm/controls/OrbitControls.js"


def _risk_color(level: str) -> str:
    return {"红色": "#EF4444", "橙色": "#F59E0B", "黄色": "#EAB308", "蓝色": "#38BDF8"}.get(level, "#8FA3C0")


def _count_color(n: int) -> list:
    """隐患数 -> [r,g,b] 色（绿->黄->红）"""
    if n <= 0:
        return [0.16, 0.27, 0.45]
    if n <= 3:
        return [0.13, 0.65, 0.38]
    if n <= 6:
        return [0.96, 0.62, 0.04]
    return [0.93, 0.20, 0.20]


def building_3d(buildings: list, height: int = 430):
    """3D 楼栋风险可视化。
    buildings: [{"name": "一号楼", "floors": [{"floor": "1层", "hazards": 3,
                  "top_level": "橙色"}, ...]}, ...]
    楼层方块颜色按隐患数映射（绿->黄->红），可拖拽旋转/缩放，hover 高亮。
    """
    data = json.dumps(buildings, ensure_ascii=False)
    html = f"""<!DOCTYPE html><html><head><meta charset="utf-8">
<style>
body {{ margin:0; overflow:hidden; background:transparent; font-family:'Fira Sans','Microsoft YaHei',sans-serif; }}
#info {{
  position:absolute; top:8px; left:12px; z-index:10;
  color:#8FA3C0; font-size:11px; pointer-events:none;
}}
.legend {{ position:absolute; bottom:10px; left:12px; z-index:10;
  display:flex; gap:14px; font-size:10px; color:#8FA3C0; }}
.legend i {{ display:inline-block; width:10px; height:10px; border-radius:3px; margin-right:4px; }}
</style></head><body>
<div id="info">🖱 拖拽旋转 · 滚轮缩放 · 悬停楼层查看</div>
<div class="legend">
  <span><i style="background:#22C55E"></i>低风险</span>
  <span><i style="background:#F59E0B"></i>中风险</span>
  <span><i style="background:#EF4444"></i>高风险</span>
</div>
<script type="importmap">
{{ "imports": {{ "three": "{THREE_CDN}", "three/addons/": "https://unpkg.com/three@0.160.0/examples/jsm/" }} }}
</script>
<script type="module">
import * as THREE from 'three';
import {{ OrbitControls }} from 'three/addons/controls/OrbitControls.js';

const DATA = {data};
const container = document.body;
const W = container.clientWidth, H = container.clientHeight;

const scene = new THREE.Scene();
scene.background = null;
scene.fog = new THREE.Fog(0x0B1120, 60, 140);

const camera = new THREE.PerspectiveCamera(45, W/H, 0.1, 500);
camera.position.set(22, 18, 30);

const renderer = new THREE.WebGLRenderer({{ antialias:true, alpha:true }});
renderer.setSize(W, H);
renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
renderer.shadowMap.enabled = true;
container.appendChild(renderer.domElement);

const controls = new OrbitControls(camera, renderer.domElement);
controls.enableDamping = true; controls.dampingFactor = 0.08;
controls.autoRotate = true; controls.autoRotateSpeed = 1.2;
controls.maxPolarAngle = Math.PI / 2.1;

// 灯光
scene.add(new THREE.AmbientLight(0xffffff, 0.55));
const dir = new THREE.DirectionalLight(0xffffff, 1.1);
dir.position.set(18, 30, 12); dir.castShadow = true;
scene.add(dir);
const rim = new THREE.PointLight(0x5B8DEF, 0.9, 80);
rim.position.set(-16, 12, -12); scene.add(rim);
const rim2 = new THREE.PointLight(0xA78BFA, 0.6, 80);
rim2.position.set(20, 8, -14); scene.add(rim2);

// 地面
const grid = new THREE.GridHelper(70, 28, 0x334155, 0x1E293B);
grid.position.y = -0.05; scene.add(grid);
const ground = new THREE.Mesh(
  new THREE.PlaneGeometry(80, 80),
  new THREE.MeshStandardMaterial({{ color:0x0F1B33, transparent:true, opacity:0.4 }}));
ground.rotation.x = -Math.PI/2; ground.position.y = -0.1; scene.add(ground);

// 楼栋
const raycaster = new THREE.Raycaster();
const mouse = new THREE.Vector2();
const meshes = [];

const floorH = 1.25, gapY = 0.18, floorW = 3.6, floorD = 3.6;
const span = DATA.length > 1 ? 9 : 0;
const x0 = -(DATA.length - 1) * span / 2;

DATA.forEach((b, bi) => {{
  const bx = x0 + bi * span;
  const floors = b.floors || [];
  const totalY = floors.length * (floorH + gapY);
  // 基座
  const base = new THREE.Mesh(
    new THREE.BoxGeometry(floorW + 1.1, 0.5, floorD + 1.1),
    new THREE.MeshStandardMaterial({{ color:0x1E293B, roughness:0.6, metalness:0.3 }}));
  base.position.set(bx, 0.2, 0);
  scene.add(base);
  // 楼层
  floors.forEach((f, fi) => {{
    const c = _count(f.hazards || 0);
    const mat = new THREE.MeshStandardMaterial({{ color:new THREE.Color(c[0],c[1],c[2]),
      roughness:0.35, metalness:0.25, emissive:new THREE.Color(c[0],c[1],c[2]), emissiveIntensity:0.12 }});
    const box = new THREE.Mesh(new THREE.BoxGeometry(floorW, floorH, floorD), mat);
    box.position.set(bx, 0.6 + fi * (floorH + gapY), 0);
    box.castShadow = true;
    box.userData = {{ building: b.name, floor: f.floor, hazards: f.hazards, top: f.top_level || '—', orig: c }};
    scene.add(box); meshes.push(box);
  }});
  // 楼栋标签（Sprite）
  const cv = document.createElement('canvas');
  cv.width = 256; cv.height = 48;
  const ctx = cv.getContext('2d');
  ctx.font = 'bold 26px "Fira Sans","Microsoft YaHei"';
  ctx.fillStyle = '#E6EDF7'; ctx.textAlign = 'center';
  ctx.fillText(b.name, 128, 32);
  const tex = new THREE.CanvasTexture(cv);
  const sp = new THREE.Sprite(new THREE.SpriteMaterial({{ map:tex, transparent:true, depthTest:false }}));
  sp.scale.set(6, 1.15, 1);
  sp.position.set(bx, totalY + 1.6, 0);
  scene.add(sp);
}});

function _count(n) {{
  if (n <= 0) return [0.16, 0.27, 0.45];
  if (n <= 3) return [0.13, 0.65, 0.38];
  if (n <= 6) return [0.96, 0.62, 0.04];
  return [0.93, 0.20, 0.20];
}}

// hover 高亮
renderer.domElement.addEventListener('pointermove', (e) => {{
  const r = renderer.domElement.getBoundingClientRect();
  mouse.x = ((e.clientX - r.left) / r.width) * 2 - 1;
  mouse.y = -((e.clientY - r.top) / r.height) * 2 + 1;
}});
let hovered = null;
const tip = document.createElement('div');
tip.style.cssText = 'position:absolute;z-index:20;padding:5px 10px;border-radius:8px;font-size:11px;' +
  'background:rgba(11,17,32,0.92);border:1px solid rgba(91,141,239,0.5);color:#E6EDF7;display:none;pointer-events:none;';
container.appendChild(tip);

function animate() {{
  requestAnimationFrame(animate);
  controls.update();
  raycaster.setFromCamera(mouse, camera);
  const hits = raycaster.intersectObjects(meshes);
  if (hovered) {{
    hovered.material.emissiveIntensity = 0.12;
    hovered = null; tip.style.display = 'none';
  }}
  if (hits.length) {{
    const o = hits[0].object;
    o.material.emissiveIntensity = 0.45;
    hovered = o;
    const d = o.userData;
    tip.style.display = 'block';
    const r = renderer.domElement.getBoundingClientRect();
    tip.style.left = (r.left + 14) + 'px';
    tip.style.top = (r.top + 40) + 'px';
    tip.textContent = `${{d.building}} · ${{d.floor}} · 隐患 ${{d.hazards}} 项 · ${{d.top}}级`;
  }}
  renderer.render(scene, camera);
}}
animate();

window.addEventListener('resize', () => {{
  const w = container.clientWidth, h = container.clientHeight;
  camera.aspect = w/h; camera.updateProjectionMatrix();
  renderer.setSize(w, h);
}});
</script></body></html>"""
    st.components.v1.html(html, height=height)


def particle_bg(seed: int = 7, count: int = 90):
    """全屏 Three.js 粒子背景（用于登录页/大屏顶部装饰）"""
    html = f"""<!DOCTYPE html><html><head><meta charset="utf-8">
<style>
body {{ margin:0; overflow:hidden; background:transparent; }}
canvas {{ display:block; }}
</style></head><body>
<script type="importmap">
{{ "imports": {{ "three": "{THREE_CDN}" }} }}
</script>
<script type="module">
import * as THREE from 'three';
const W = innerWidth, H = innerHeight;
const scene = new THREE.Scene();
const camera = new THREE.PerspectiveCamera(75, W/H, 0.1, 300);
camera.position.z = 42;
const renderer = new THREE.WebGLRenderer({{ antialias:true, alpha:true }});
renderer.setSize(W, H);
renderer.setPixelRatio(Math.min(devicePixelRatio, 2));
document.body.appendChild(renderer.domElement);
const n = {count};
const pos = new Float32Array(n*3);
const colors = new Float32Array(n*3);
const palette = [new THREE.Color(0x5B8DEF), new THREE.Color(0xA78BFA), new THREE.Color(0x38BDF8), new THREE.Color(0x22C55E)];
const seed = {seed};
for (let i=0;i<n;i++) {{
  const a = (i / n) * Math.PI * 2 + seed * 0.7;
  const r = 16 + ((i * seed * 7) % 12);
  pos[i*3] = Math.cos(a) * r + (Math.sin(i*seed) * 6);
  pos[i*3+1] = Math.sin(a) * r * 0.62;
  pos[i*3+2] = ((i * seed * 13) % 20) - 10;
  const c = palette[i % palette.length];
  colors[i*3] = c.r; colors[i*3+1] = c.g; colors[i*3+2] = c.b;
}}
const geo = new THREE.BufferGeometry();
geo.setAttribute('position', new THREE.BufferAttribute(pos, 3));
geo.setAttribute('color', new THREE.BufferAttribute(colors, 3));
const mat = new THREE.PointsMaterial({{ size:0.35, vertexColors:true, transparent:true, opacity:0.75, depthWrite:false }});
const pts = new THREE.Points(geo, mat);
scene.add(pts);
const rot = new THREE.Group();
rot.add(pts); scene.add(rot);
(function loop() {{
  requestAnimationFrame(loop);
  rot.rotation.y += 0.0014;
  pts.rotation.z += 0.0004;
  renderer.render(scene, camera);
}})();
window.addEventListener('resize', () => {{
  camera.aspect = innerWidth/innerHeight; camera.updateProjectionMatrix();
  renderer.setSize(innerWidth, innerHeight);
}});
</script></body></html>"""
    st.components.v1.html(html, height=340, scrolling=False)
