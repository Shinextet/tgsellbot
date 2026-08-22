"""
26. Order Search System
"""
from telegram import Update
from telegram.ext import ContextTypes

from bot import database as db

STATUS_LABEL = {
    "pending": "🟡 Pending",
    "confirmed": "✅ Confirmed",
    "rejected": "❌ Rejected",
    "completed": "🎉 Completed",
}


async def search_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if not await db.is_admin(user.id):
        await update.effective_message.reply_text("🚫 Admin only command ဖြစ်ပါတယ်။")
        return

    if not context.args:
        await update.effective_message.reply_text("Usage: /search <order_id>")
        return

    order_id = context.args[0].upper()
    order = await db.get_order(order_id)
    if not order:
        await update.effective_message.reply_text(f"⚠️ Order '{order_id}' မတွေ့ပါ။")
        return

    text = (
        f"🧾 <b>Order ID:</b> <code>{order['order_id']}</code>\n"
        f"👤 Customer: @{order.get('customer_username','-')} (<code>{order['customer_id']}</code>)\n"
        f"🎮 Game ID: <code>{order.get('game_id','-')}</code> (Server {order.get('server_id','-')})\n"
        f"📦 Package: {order.get('package_name','-')} — {int(order.get('price',0))} MMK\n"
        f"💳 Payment: {order.get('payment_method','-')}\n"
        f"📌 Status: {STATUS_LABEL.get(order['status'], order['status'])}\n"
        f"🕒 Created: {order.get('created_at','-')}\n"
    )
    if order.get("reject_reason"):
        text += f"❌ Reject reason: {order['reject_reason']}\n"

    await update.effective_message.reply_html(text)
