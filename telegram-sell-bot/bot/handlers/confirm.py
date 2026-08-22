"""
19. Admin Confirm / Reject System
20. Admin-Only Confirm Button
21. Order Status Management System
24. Customer Order Status Notification
28. Admin Action Log System
"""
import datetime as dt

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from bot import database as db


def build_admin_order_keyboard(order_id: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("✅ Confirm", callback_data=f"conf:{order_id}"),
                InlineKeyboardButton("❌ Reject", callback_data=f"rej:{order_id}"),
            ]
        ]
    )


async def confirm_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    admin = update.effective_user

    # 20. Admin-only confirm button
    if not await db.is_admin(admin.id):
        await query.answer("🚫 Admin ပဲ Confirm လုပ်ခွင့်ရှိပါတယ်။", show_alert=True)
        return

    order_id = query.data.split(":")[1]
    order = await db.get_order(order_id)
    if not order:
        await query.answer("⚠️ Order မတွေ့ပါ။", show_alert=True)
        return
    if order["status"] != "pending":
        await query.answer(f"ℹ️ Order status က {order['status']} ဖြစ်နေပြီးသားပါ။", show_alert=True)
        return

    await db.update_order(
        order_id,
        {
            "status": "confirmed",
            "confirmed_at": dt.datetime.utcnow().isoformat(),
            "confirmed_by": admin.id,
        },
    )
    await db.log_action(admin.id, admin.username or admin.first_name, "confirm_order", order_id)
    await query.answer("✅ Confirmed!")

    try:
        await query.edit_message_caption(
            caption=(query.message.caption or "") + f"\n\n✅ <b>CONFIRMED</b> by @{admin.username}",
            parse_mode="HTML",
        )
    except Exception:
        pass

    from bot.handlers.receipt import send_receipt
    await send_receipt(context, order_id)

    try:
        await context.bot.send_message(
            chat_id=order["customer_id"],
            text=(
                f"✅ <b>Order Confirmed!</b>\n🧾 Order ID: <code>{order_id}</code>\n"
                "🎉 Diamond/Item ကို ခဏအတွင်း ထည့်ပေးပါမည်။ ကျေးဇူးတင်ပါတယ်!"
            ),
            parse_mode="HTML",
        )
    except Exception:
        pass


async def reject_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    admin = update.effective_user

    if not await db.is_admin(admin.id):
        await query.answer("🚫 Admin ပဲ Reject လုပ်ခွင့်ရှိပါတယ်။", show_alert=True)
        return

    order_id = query.data.split(":")[1]
    order = await db.get_order(order_id)
    if not order:
        await query.answer("⚠️ Order မတွေ့ပါ။", show_alert=True)
        return
    if order["status"] != "pending":
        await query.answer(f"ℹ️ Order status က {order['status']} ဖြစ်နေပြီးသားပါ။", show_alert=True)
        return

    await db.update_order(order_id, {"status": "rejected", "reject_reason": "admin_rejected"})
    await db.log_action(admin.id, admin.username or admin.first_name, "reject_order", order_id)
    await query.answer("❌ Rejected")

    try:
        await query.edit_message_caption(
            caption=(query.message.caption or "") + f"\n\n❌ <b>REJECTED</b> by @{admin.username}",
            parse_mode="HTML",
        )
    except Exception:
        pass

    try:
        await context.bot.send_message(
            chat_id=order["customer_id"],
            text=(
                f"❌ <b>Order Rejected</b>\n🧾 Order ID: <code>{order_id}</code>\n"
                "Payment စစ်ဆေးမှု အောင်မြင်မှုမရှိပါ။ Admin ကို ဆက်သွယ်ပေးပါ 🙏"
            ),
            parse_mode="HTML",
        )
    except Exception:
        pass
