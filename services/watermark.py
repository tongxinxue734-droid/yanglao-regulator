# -*- coding: utf-8 -*-
"""照片水印（防代拍/重复上报）与感知哈希去重"""
import hashlib
import io
import os
import time
from datetime import datetime

from PIL import Image, ImageDraw, ImageFont

import config


def _font(size: int = 22):
    for path in (r"C:\Windows\Fonts\msyh.ttc",  # 微软雅黑
                 r"C:\Windows\Fonts\simhei.ttf",
                 r"C:\Windows\Fonts\simsun.ttc"):
        if os.path.exists(path):
            try:
                return ImageFont.truetype(path, size)
            except Exception:
                continue
    return ImageFont.load_default()


def add_watermark(image_bytes: bytes, *, name: str, room: str,
                  location: str = "") -> bytes:
    """叠加水印：巡检人姓名 + 时间 + 定位 + 房间号"""
    img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    draw = ImageDraw.Draw(img)
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    lines = [
        f"巡检人：{name}",
        f"时间：{ts}",
        f"房间：{room}",
    ]
    if location:
        lines.append(f"定位：{location}")
    font = _font(max(20, img.width // 30))
    margin = 12
    y = margin
    for line in lines:
        bbox = draw.textbbox((0, 0), line, font=font)
        tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
        x = img.width - tw - margin
        draw.rectangle([x - 6, y - 4, x + tw + 6, y + th + 4], fill=(0, 0, 0))
        draw.text((x, y), line, fill=(255, 255, 0), font=font)
        y += th + 8
    out = io.BytesIO()
    img.save(out, format="JPEG", quality=88)
    return out.getvalue()


def save_photo(image_bytes: bytes, *, name: str, room: str,
               location: str = "", subdir: str = "hazards") -> str:
    """保存带水印照片，返回相对路径。返回 None 表示重复照片或图片无效。"""
    try:
        h = _dhash(image_bytes)
    except Exception:
        return None  # 非图片文件，跳过
    dedup_dir = os.path.join(config.DATA_DIR, "dedup")
    os.makedirs(dedup_dir, exist_ok=True)
    mark_file = os.path.join(dedup_dir, f"{h}.txt")
    if os.path.exists(mark_file):
        return None  # 重复照片，自动去重
    watermarked = add_watermark(image_bytes, name=name, room=room, location=location)
    fname = f"{datetime.now().strftime('%Y%m%d%H%M%S')}_{h[:10]}.jpg"
    rel_dir = os.path.join("uploads", subdir)
    abs_dir = os.path.join(config.DATA_DIR, rel_dir)
    os.makedirs(abs_dir, exist_ok=True)
    abs_path = os.path.join(abs_dir, fname)
    try:
        with open(abs_path, "wb") as f:
            f.write(watermarked)
    except Exception:
        return None  # 写盘失败不留下去重标记，允许重试
    open(mark_file, "w").close()  # 保存成功后才打去重标记
    return os.path.join(rel_dir, fname).replace("\\", "/")


def _dhash(image_bytes: bytes, hash_size: int = 8) -> str:
    """感知哈希：结构相似的照片得到相同哈希，用于重复上报去重"""
    img = Image.open(io.BytesIO(image_bytes)).convert("L").resize(
        (hash_size + 1, hash_size), Image.LANCZOS)
    diff = []
    px = img.load()
    for y in range(hash_size):
        for x in range(hash_size):
            diff.append(1 if px[x, y] > px[x + 1, y] else 0)
    bits = "".join(str(b) for b in diff)
    return format(int(bits, 2), "0%dx" % (hash_size * hash_size))
