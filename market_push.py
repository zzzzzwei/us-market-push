import yfinance as yf
import os
import requests
from datetime import datetime
import pytz

# ========= Telegram =========
TG_BOT_TOKEN = os.getenv("TG_BOT_TOKEN")
TG_CHAT_ID = os.getenv("TG_CHAT_ID")
IS_MANUAL = os.getenv("GITHUB_EVENT_NAME") == "workflow_dispatch"

# ========= 时区 =========
TZ_US = pytz.timezone("US/Eastern")
TZ_CN = pytz.timezone("Asia/Shanghai")

# ========= 指数 =========
INDEXES = {
    "纳指": "^IXIC",
    "标普500": "^GSPC",
    "道琼斯": "^DJI"
}

# ========= 风控参数 =========
LOOKBACK_HIGH_DAYS = 20
DRAWDOWN_THRESHOLD = -3.0
CONTINUOUS_DOWN_DAYS = 4

# ========= 宏观指标 =========
MACRO_INDEX = {
    "VIX": "^VIX",
    "10Y美债": "^TNX",
    "美元指数": "DX-Y.NYB"
}


def is_us_market_closed():
    now = datetime.now(TZ_US)
    if now.weekday() >= 5:
        return False
    close_time = now.replace(hour=16, minute=0, second=0, microsecond=0)
    return now >= close_time


def get_history(symbol, days=30):
    return yf.Ticker(symbol).history(period=f"{days}d")["Close"].dropna()


def get_today_change(closes):
    if len(closes) < 2:
        return None
    return round((closes.iloc[-1] / closes.iloc[-2] - 1) * 100, 2)


def get_drawdown_from_high(closes, lookback=20):
    recent = closes.iloc[-lookback:]
    high = recent.max()
    today = recent.iloc[-1]
    return round((today / high - 1) * 100, 2)


def count_continuous_down_days(closes):
    count = 0
    for i in range(len(closes) - 1, 0, -1):
        if closes.iloc[i] < closes.iloc[i - 1]:
            count += 1
        else:
            break
    return count


def macro_risk_check():
    risks = []

    vix = get_history(MACRO_INDEX["VIX"], 5)
    if vix.iloc[-1] > 20:
        risks.append("😰 VIX 偏高")

    tnx = get_history(MACRO_INDEX["10Y美债"], 5)
    if tnx.iloc[-1] > tnx.iloc[-2]:
        risks.append("📈 美债收益率上行")

    dxy = get_history(MACRO_INDEX["美元指数"], 5)
    if dxy.iloc[-1] > dxy.iloc[-2]:
        risks.append("💵 美元走强")

    return risks if len(risks) >= 2 else []


def generate_message():
    now_cn = datetime.now(TZ_CN).strftime("%Y-%m-%d %H:%M")
    lines = [f"📊 美股风险监控 ({now_cn})"]

    risk_lines = []

    for name, code in INDEXES.items():
        closes = get_history(code)
        today_change = get_today_change(closes)

        emoji = "📈" if today_change > 0 else "📉"
        sign = "+" if today_change > 0 else ""
        lines.append(f"{emoji} {name}: {sign}{today_change}%")

        # === 回撤风险 ===
        drawdown = get_drawdown_from_high(closes, LOOKBACK_HIGH_DAYS)
        if drawdown <= DRAWDOWN_THRESHOLD and today_change < 0:
            risk_lines.append(
                f"⚠️ {name} 较 {LOOKBACK_HIGH_DAYS} 日高点回撤 {abs(drawdown)}%，且今日继续下跌"
            )

        # === 连续下跌 ===
        down_days = count_continuous_down_days(closes)
        if down_days >= CONTINUOUS_DOWN_DAYS:
            risk_lines.append(
                f"📉 {name} 已连续下跌 {down_days} 天"
            )

    # === 宏观风险 ===
    macro_risks = macro_risk_check()
    if macro_risks:
        risk_lines.append("🌍 宏观风险共振：")
        risk_lines.extend(macro_risks)

    if risk_lines:
        lines.append("")
        lines.append("🚨 风险提醒：")
        lines.extend(risk_lines)

    if IS_MANUAL:
        lines.append("")
        lines.append("⚙️ 本次为手动触发")

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
    print("🔁 手动执行:", IS_MANUAL)

    if not IS_MANUAL and not is_us_market_closed():
        print("⏳ 未收盘，跳过")
        return

    msg = generate_message()
    print(msg)
    send_telegram(msg)
    print("✅ 已推送")


if __name__ == "__main__":
    main()
