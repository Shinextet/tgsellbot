"""
29. Daily Sales Report System
30. Order / Sales Statistics System
"""
import datetime as dt

from telegram import Update
from telegram.ext import ContextTypes

from bot import config, database as db


def _today_range_iso():
    now = dt.datetime.utcnow()
    start = dt.datetime(now.year, now.month, now.day)
    end = start + dt.timedelta(days=1)
    return start.isoformat(), end.isoformat()


async def build_daily_report_text() -> str:
    start_iso, end_iso = _today_range_iso()
    sales = await db.sales_between(start_iso, end_iso)

    total_orders = len(sales)
    total_amount = sum(float(o.get("price", 0)) for o in sales)

    by_package: dict[str, int] = {}
    for o in sales:
        name = o.get("package_name", "Unknown")
        by_package[name] = by_package.get(name, 0) + 1

    lines = [
        "📊 <b>Daily Sales Report</b>",
        f"🗓 {dt.datetime.utcnow().strftime('%Y-%m-%d')} (UTC)",
        "━━━━━━━━━━━━━━━",
        f"🧾 Orders: {total_orders}",
        f"💰 Total: {int(total_amount)} MMK",
    ]
    if by_package:
        lines.append("\n📦 <b>By Package</b>")
        for name, cnt in sorted(by_package.items(), key=lambda x: -x[1]):
            lines.append(f"• {name} × {cnt}")

    return "\n".join(lines)


async def report_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if not await db.is_admin(user.id):
        await update.effective_message.reply_text("🚫 Admin only command ဖြစ်ပါတယ်။")
        return
    await update.effective_message.reply_html(await build_daily_report_text())


async def stats_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if not await db.is_admin(user.id):
        await update.effective_message.reply_text("🚫 Admin only command ဖြစ်ပါတယ်။")
        return

    orders = await db.all_orders(limit=5000)
    total = len(orders)
    by_status: dict[str, int] = {}
    total_revenue = 0.0
    for o in orders:
        by_status[o["status"]] = by_status.get(o["status"], 0) + 1
        if o["status"] in ("confirmed", "completed"):
            total_revenue += float(o.get("price", 0))

    lines = [
        "📈 <b>All-Time Statistics</b>",
        f"🧾 Total Orders: {total}",
        f"💰 Total Revenue: {int(total_revenue)} MMK",
        "",
    ]
    for status, cnt in by_status.items():
        lines.append(f"• {status}: {cnt}")

    await update.effective_message.reply_html("\n".join(lines))


async def daily_report_job(context: ContextTypes.DEFAULT_TYPE):
    """Scheduled via JobQueue - posts the daily report to the admin group."""
    if not config.ADMIN_GROUP_ID:
        return
    text = await build_daily_report_text()
    await context.bot.send_message(chat_id=config.ADMIN_GROUP_ID, text=text, parse_mode="HTML")
