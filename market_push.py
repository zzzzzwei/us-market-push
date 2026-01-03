import yfinance as yf
import os
import requests
from datetime import datetime
import pytz

# ========= Telegram 配置 =========
TG_BOT_TOKEN = os.getenv("TG_BOT_TOKEN")
TG_CHAT_ID = os.getenv("TG_CHAT_ID")

# ========= 指数配置 =========
INDEXES = {
    "纳指": "^IXIC",
    "标普500": "^GSPC",
    "道琼斯": "^DJI"
}

# ========= 时区 =========
TZ_US = pytz.timezone("US/Eastern")
TZ_CN = pytz.timezone("Asia/Shanghai")

def is_us_market_closed():
    """是否已过美股收盘时间（16:00 美东，自动夏/冬令时）"""
    now_us = datetime.now(TZ_US)

    if now_us.weekday() >= 5:
        return False

    close_time = now_us.replace(hour=16, minute=0, second=0, microsecond=0)
    return now_us >= close_time


def get_change(symbol):
    data = yf.Ticker(symbol).history(period="2d")
    if len(data) < 2:
        return None
    today = data["Close"].iloc[-1]
    yesterday = data["Close"].iloc[-2]
    return round((today / yesterday - 1) * 100, 2)


def generate_message():
    date_cn = datetime.now(TZ_CN).strftime("%Y-%m-%d")
    lines = [f"📊 美股收盘 ({date_cn})"]

    for name, code in INDEXES.items():
        change = get_change(code)
        if change is None:
            continue
        emoji = "📈" if change > 0 else "📉"
        sign = "+" if change > 0 else ""
        lines.append(f"{emoji} {name}: {sign}{change}%")

    lines.append("🕓 收盘时间：美东 16:00（自动识别夏/冬令时）")
    return "\n".join(lines)


def send_telegram(text):
    url = f"https://api.telegram.org/bot{TG_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TG_CHAT_ID,
        "text": text,
        "disable_web_page_preview": True
    }
    r = requests.post(url, data=payload, timeout=10)
    r.raise_for_status()


def main():
    if not is_us_market_closed():
        print("⏳ 美股尚未收盘，跳过")
        return

    msg = generate_message()
    send_telegram(msg)
    print("✅ 已推送到 Telegram")


if __name__ == "__main__":
    main()
