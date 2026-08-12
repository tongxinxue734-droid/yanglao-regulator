# -*- coding: utf-8 -*-
"""预警推送服务：站内通知 + 企业微信机器人 + 邮件（SMTP）
配置见 config.py（WECHAT_WEBHOOK_URL / SMTP_* / NOTIFY_EMAIL）
"""
import config


def send_wecom(content: str) -> bool:
    """企业微信机器人 webhook 推送"""
    if not config.ENABLE_WECHAT_PUSH or not config.WECHAT_WEBHOOK_URL:
        return False
    try:
        import requests
        r = requests.post(config.WECHAT_WEBHOOK_URL,
                          json={"msgtype": "text", "text": {"content": content}},
                          timeout=5)
        return r.status_code == 200
    except Exception:
        return False


def send_mail(subject: str, body: str) -> bool:
    """SMTP 邮件推送"""
    if not config.SMTP_HOST or not config.NOTIFY_EMAIL:
        return False
    try:
        import smtplib
        from email.mime.text import MIMEText
        msg = MIMEText(body, "plain", "utf-8")
        msg["Subject"] = subject
        msg["From"] = config.SMTP_USER
        msg["To"] = config.NOTIFY_EMAIL
        if config.SMTP_PORT == 465:
            server = smtplib.SMTP_SSL(config.SMTP_HOST, config.SMTP_PORT, timeout=8)
        else:
            server = smtplib.SMTP(config.SMTP_HOST, config.SMTP_PORT, timeout=8)
        if config.SMTP_USER:
            server.login(config.SMTP_USER, config.SMTP_PASS)
        server.sendmail(config.SMTP_USER, [config.NOTIFY_EMAIL], msg.as_string())
        server.quit()
        return True
    except Exception:
        return False


def push(ntype: str, content: str) -> tuple:
    """统一推送入口：返回 (企业微信, 邮件) 是否成功"""
    ok_w = send_wecom(f"【养老监管 · {ntype}】{content}")
    ok_m = send_mail(f"【养老监管预警】{ntype}", content)
    return ok_w, ok_m
