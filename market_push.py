import yfinance as yf
import os
import requests
from datetime import datetime
import pytz

# ========= Telegram 配置 =========
TG_BOT_TOKEN = os.getenv("TG_BOT_TOKEN")
TG_CHAT_ID = os.getenv("TG_CHAT_ID")

# GitHub 运行模式
IS_MANUAL = os.getenv("GITHUB_EVENT_NAME") == "workflow_dispatch"

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
    data = yf.Ticker(symbol).history(period="5d")
    closes = data["Close"].dropna()

    if len(closes) < 2:
        return None

    today, yesterday = closes.iloc[-1], closes.iloc[-2]
    return round((today / yesterday - 1) * 100, 2)


def ai_market_comment(changes: list[float]) -> str:
    avg = sum(changes) / len(changes)

    if avg > 0.8:
        return "🤖 AI解读：市场情绪偏多，风险偏好回升，科技与权重股表现积极。"
    elif avg < -0.8:
        return "🤖 AI解读：市场情绪偏空，资金趋于谨慎，短期波动可能加大。"
    else:
        return "🤖 AI解读：指数分化，市场处于震荡整理阶段，等待新的催化因素。"


def generate_message():
    date_cn = datetime.now(TZ_CN).strftime("%Y-%m-%d %H:%M")
    lines = [f"📊 美股行情推送 ({date_cn})"]

    changes = []

    for name, code in INDEXES.items():
        change = get_change(code)
        if change is None:
            continue

        changes.append(change)
        emoji = "📈" if change > 0 else "📉"
        sign = "+" if change > 0 else ""
        lines.append(f"{emoji} {name}: {sign}{change}%")

    if changes:
        lines.append("")
        lines.append(ai_market_comment(changes))

    lines.append("")
    lines.append("🕓 美股收盘：美东 16:00（自动识别夏 / 冬令时）")

    if IS_MANUAL:
        lines.append("⚙️ 本次为手动触发推送")

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
    print("🕒 CN:", datetime.now(TZ_CN))
    print("🕒 US:", datetime.now(TZ_US))
    print("🔁 手动执行:", IS_MANUAL)

    if not IS_MANUAL and not is_us_market_closed():
        print("⏳ 非手动执行，且美股未收盘，跳过")
        return

    msg = generate_message()
    print("📨 推送内容：\n", msg)

    send_telegram(msg)
    print("✅ 已推送到 Telegram")


if __name__ == "__main__":
    main()
