# -*- coding: utf-8 -*-
"""DeepSeek 大模型问答 — RAG 增强
检索 39 条指标库做上下文 → DeepSeek 组织回答（政务规范语气）
- key 从 Reasonix 全局 .env 读取（%APPDATA%/reasonix/.env）
- 无 key / 超时 / 报错 → 自动降级为规则检索版（assistant._match_indicators）
- 输出按 2025 新规显式标注「AI 生成」
"""
import json
import os
import re
import urllib.request

API_URL = "https://api.deepseek.com/chat/completions"
MODEL = "deepseek-chat"  # V3 指令模型；深度分析可换 deepseek-reasoner


def _load_api_key() -> str:
    """从 Reasonix 全局 .env 读取 DEEPSEEK_API_KEY（不落盘到项目）"""
    key = os.environ.get("DEEPSEEK_API_KEY", "")
    if key:
        return key
    env_file = os.path.join(os.environ.get("APPDATA", ""), "reasonix", ".env")
    try:
        with open(env_file, encoding="utf-8") as f:
            for line in f:
                m = re.match(r"\s*DEEPSEEK_API_KEY\s*=\s*[\"']?([^\"'\r\n]+)", line)
                if m:
                    return m.group(1).strip()
    except OSError:
        pass
    return ""


def ask(query: str, context: str) -> str | None:
    """调用 DeepSeek；失败返回 None（由调用方降级）"""
    key = _load_api_key()
    if not key:
        return None
    sys_prompt = (
        "你是养老机构监管部门的合规解答助手。请严格依据给定指标库回答，"
        "语气严谨、条理清晰；先给结论（扣分档位），再列依据；"
        "回答控制在 200 字内；不得编造指标库之外的内容。"
    )
    payload = {
        "model": MODEL,
        "messages": [
            {"role": "system", "content": sys_prompt},
            {"role": "user", "content": f"指标库：\n{context}\n\n问题：{query}"},
        ],
        "temperature": 0.3,
        "max_tokens": 600,
    }
    req = urllib.request.Request(
        API_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {key}"},
    )
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        return data["choices"][0]["message"]["content"].strip()
    except Exception:
        return None


def build_context(indicators) -> str:
    """把命中的指标拼成指标库上下文（含 code/名称/扣分/依据/类别）"""
    lines = []
    for ind in indicators:
        lines.append(
            f"- {ind.code} {ind.item}：扣 {ind.deduct} 分，类别「{ind.category}」，"
            f"依据：{ind.law_basis or '—'}"
        )
    return "\n".join(lines)
