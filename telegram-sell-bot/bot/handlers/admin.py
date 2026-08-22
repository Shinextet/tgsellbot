"""
3. Admin Command System
4. Admin Permission & Role System
37. Security & Access Control System
"""
from telegram import Update
from telegram.ext import ContextTypes

from bot import database as db


async def addadmin_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if not await db.is_owner(user.id):
        await update.effective_message.reply_text("🚫 Owner ပဲ admin ထည့်ခွင့်ရှိပါတယ်။")
        return

    if not context.args:
        await update.effective_message.reply_text(
            "Usage: /addadmin <user_id> [role]\nrole: admin (default) or owner"
        )
        return

    try:
        target_id = int(context.args[0])
    except ValueError:
        await update.effective_message.reply_text("⚠️ user_id ကိုနံပါတ်ပဲ ရိုက်ပါ။")
        return

    role = context.args[1] if len(context.args) > 1 else "admin"
    if role not in ("admin", "owner"):
        role = "admin"

    await db.add_admin(target_id, username="", role=role, added_by=user.id)
    await db.log_action(user.id, user.username, "add_admin", f"target={target_id} role={role}")
    await update.effective_message.reply_text(f"✅ Admin ထည့်ပြီးပါပြီ — {target_id} ({role})")


async def removeadmin_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if not await db.is_owner(user.id):
        await update.effective_message.reply_text("🚫 Owner ပဲ admin ဖြုတ်ခွင့်ရှိပါတယ်။")
        return

    if not context.args:
        await update.effective_message.reply_text("Usage: /removeadmin <user_id>")
        return

    try:
        target_id = int(context.args[0])
    except ValueError:
        await update.effective_message.reply_text("⚠️ user_id ကိုနံပါတ်ပဲ ရိုက်ပါ။")
        return

    await db.remove_admin(target_id)
    await db.log_action(user.id, user.username, "remove_admin", f"target={target_id}")
    await update.effective_message.reply_text(f"✅ Admin ဖြုတ်ပြီးပါပြီ — {target_id}")


async def admins_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if not await db.is_admin(user.id):
        await update.effective_message.reply_text("🚫 Admin only command ဖြစ်ပါတယ်။")
        return

    admins = await db.list_admins()
    if not admins:
        text = "📭 Admin list ထဲ ဘယ်သူမှ မရှိသေးပါ (owner env config ကတော့ အမြဲ full access ရှိတယ်)။"
    else:
        lines = ["👥 <b>Admin List</b>"]
        for a in admins:
            lines.append(f"• <code>{a['user_id']}</code> — {a['role']}")
        text = "\n".join(lines)
    await update.effective_message.reply_html(text)
