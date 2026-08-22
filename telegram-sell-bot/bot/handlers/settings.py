"""
32. Database Management System (packages/payment CRUD via commands)
33. Database Backup System
35. Bot Settings / Configuration System
36. Admin Panel / Control Panel
"""
import csv
import io

from telegram import Update, InputFile
from telegram.ext import ContextTypes

from bot import database as db

PANEL_TEXT = (
    "🛠 <b>Admin Panel</b>\n\n"
    "/open — Group ဖွင့်ရန်\n"
    "/close — Group ပိတ်ရန်\n"
    "/addadmin &lt;id&gt; [role] — Admin ထည့်ရန်\n"
    "/removeadmin &lt;id&gt; — Admin ဖြုတ်ရန်\n"
    "/admins — Admin list ကြည့်ရန်\n"
    "/addpackage &lt;name&gt;|&lt;price&gt; — Package အသစ်ထည့်ရန်\n"
    "/removepackage &lt;id&gt; — Package ဖျက်ရန်\n"
    "/packages — Package list\n"
    "/setpayment &lt;method&gt; &lt;phone&gt; — Payment number update\n"
    "/search &lt;order_id&gt; — Order ရှာရန်\n"
    "/report — ယနေ့ Sales report\n"
    "/stats — All-time statistics\n"
    "/backup — Orders CSV backup ရယူရန်\n"
    "/logs — နောက်ဆုံး admin actions"
)


async def panel_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if not await db.is_admin(user.id):
        await update.effective_message.reply_text("🚫 Admin only command ဖြစ်ပါတယ်။")
        return
    await update.effective_message.reply_html(PANEL_TEXT)


async def addpackage_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if not await db.is_admin(user.id):
        await update.effective_message.reply_text("🚫 Admin only command ဖြစ်ပါတယ်။")
        return

    raw = " ".join(context.args)
    if "|" not in raw:
        await update.effective_message.reply_text("Usage: /addpackage <name>|<price>")
        return

    name, price_str = raw.split("|", 1)
    try:
        price = float(price_str.strip())
    except ValueError:
        await update.effective_message.reply_text("⚠️ Price ကိုနံပါတ်ပဲ ရိုက်ပါ။")
        return

    from bot.database import _client  # direct insert, simplest for a new row
    import asyncio
    await asyncio.to_thread(
        lambda: _client.table("packages").insert(
            {"name": name.strip(), "price": price, "emoji": "💎", "active": True}
        ).execute()
    )
    await db.log_action(user.id, user.username, "add_package", raw)
    await update.effective_message.reply_text(f"✅ Package ထည့်ပြီးပါပြီ — {name.strip()} ({price} MMK)")


async def removepackage_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if not await db.is_admin(user.id):
        await update.effective_message.reply_text("🚫 Admin only command ဖြစ်ပါတယ်။")
        return

    if not context.args:
        await update.effective_message.reply_text("Usage: /removepackage <id>")
        return

    from bot.database import _client
    import asyncio
    pkg_id = context.args[0]
    await asyncio.to_thread(
        lambda: _client.table("packages").update({"active": False}).eq("id", pkg_id).execute()
    )
    await db.log_action(user.id, user.username, "remove_package", pkg_id)
    await update.effective_message.reply_text(f"✅ Package #{pkg_id} ကို ပိတ်လိုက်ပါပြီ။")


async def packages_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    packages = await db.list_packages(active_only=True)
    if not packages:
        await update.effective_message.reply_text("📭 Package မရှိသေးပါ။")
        return
    lines = ["📦 <b>Packages</b>"]
    for p in packages:
        lines.append(f"#{p['id']} • {p['emoji']} {p['name']} — {int(p['price'])} MMK")
    await update.effective_message.reply_html("\n".join(lines))


async def setpayment_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if not await db.is_admin(user.id):
        await update.effective_message.reply_text("🚫 Admin only command ဖြစ်ပါတယ်။")
        return

    if len(context.args) < 2:
        await update.effective_message.reply_text("Usage: /setpayment <method> <phone>")
        return

    method, phone = context.args[0], context.args[1]
    await db.upsert_payment_method(method, phone)
    await db.log_action(user.id, user.username, "set_payment", f"{method} {phone}")
    await update.effective_message.reply_text(f"✅ {method} → {phone} သိမ်းပြီးပါပြီ။")


async def logs_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if not await db.is_admin(user.id):
        await update.effective_message.reply_text("🚫 Admin only command ဖြစ်ပါတယ်။")
        return

    logs = await db.recent_logs(limit=20)
    if not logs:
        await update.effective_message.reply_text("📭 Log မရှိသေးပါ။")
        return

    lines = ["📝 <b>Recent Admin Actions</b>"]
    for l in logs:
        lines.append(f"• {l['created_at'][:19]} — {l.get('admin_username') or l.get('admin_id')} → {l['action']} ({l.get('detail','')})")
    await update.effective_message.reply_html("\n".join(lines))


async def backup_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if not await db.is_owner(user.id):
        await update.effective_message.reply_text("🚫 Owner ပဲ backup ယူခွင့်ရှိပါတယ်။")
        return

    orders = await db.all_orders(limit=100000)
    if not orders:
        await update.effective_message.reply_text("📭 Order data မရှိသေးပါ။")
        return

    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=list(orders[0].keys()))
    writer.writeheader()
    writer.writerows(orders)
    buf.seek(0)

    data = io.BytesIO(buf.getvalue().encode("utf-8"))
    data.name = "orders_backup.csv"

    await update.effective_message.reply_document(
        document=InputFile(data, filename="orders_backup.csv"),
        caption=f"🗃️ Backup — {len(orders)} orders",
    )
    await db.log_action(user.id, user.username, "backup", f"{len(orders)} orders")
