"""Email alert sender via SMTP.

Config file: data/smtp_config.json
{
    "enabled": false,
    "host": "smtp.gmail.com",
    "port": 587,
    "user": "your@email.com",
    "password": "app-password",
    "from_addr": "MarketEye <your@email.com>",
    "use_tls": true
}
"""

import json
import smtplib
import logging
from email.mime.text import MIMEText
from pathlib import Path

logger = logging.getLogger("marketeye.email")

CONFIG_PATH = Path(__file__).parent.parent / "data" / "smtp_config.json"


def load_config() -> dict | None:
    if not CONFIG_PATH.exists():
        return None
    try:
        with open(CONFIG_PATH) as f:
            cfg = json.load(f)
        if cfg.get("enabled") and cfg.get("host"):
            return cfg
    except Exception:
        pass
    return None


def save_config(host: str, port: int, user: str, password: str,
                from_addr: str, use_tls: bool = True):
    cfg = {
        "enabled": True,
        "host": host,
        "port": port,
        "user": user,
        "password": password,
        "from_addr": from_addr or user,
        "use_tls": use_tls,
    }
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(CONFIG_PATH, "w") as f:
        json.dump(cfg, f, indent=2)
    return cfg


def send_alert(to_email: str, subject: str, body: str) -> bool:
    cfg = load_config()
    if not cfg:
        logger.warning("SMTP not configured; skipping email")
        return False
    try:
        msg = MIMEText(body, "plain", "utf-8")
        msg["Subject"] = subject
        msg["From"] = cfg["from_addr"]
        msg["To"] = to_email

        if cfg.get("use_tls", True):
            with smtplib.SMTP(cfg["host"], cfg["port"], timeout=15) as s:
                s.starttls()
                s.login(cfg["user"], cfg["password"])
                s.send_message(msg)
        else:
            with smtplib.SMTP_SSL(cfg["host"], cfg["port"], timeout=15) as s:
                s.login(cfg["user"], cfg["password"])
                s.send_message(msg)

        logger.info(f"Email alert sent to {to_email}: {subject}")
        return True
    except Exception as e:
        logger.error(f"Email send failed: {e}")
        return False
