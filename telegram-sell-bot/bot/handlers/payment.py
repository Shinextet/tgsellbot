"""
12. Payment Method Selection System
13. Payment Phone Number Display System
14. Payment Screenshot Receive System
15. Payment Amount Validation System
16. Duplicate Order / Duplicate Payment Protection (screenshot re-use check)
18. Admin New Order Notification
"""
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from bot import config, database as db
from bot.utils.ratelimit import is_rate_limited

_used_file_ids: set[str] = set()  # simple in-memory duplicate-screenshot guard


async def show_payment_options(update: Update, context: ContextTypes.DEFAULT_TYPE):
    methods = await db.list_payment_methods(active_only=True)
    if not methods:
        await update.effective_message.reply_text(
            "⚠️ Payment method setup လုပ်ရသေးဘူး — Admin ကို ဆက်သွယ်ပါ။"
        )
        return

    buttons = [
        [InlineKeyboardButton(f"💳 {m['method']}", callback_data=f"pay:{m['method']}")]
        for m in methods
    ]
    await update.effective_message.reply_html(
        "💳 <b>Payment Method ရွေးပါ</b>", reply_markup=InlineKeyboardMarkup(buttons)
    )


async def payment_selected(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user_id = update.effective_user.id
    if await is_rate_limited(user_id):
        await query.answer("⏳ Action များနေပါတယ်၊ ခဏစောင့်ပါ။", show_alert=True)
        return

    method = query.data.split(":")[1]
    methods = {m["method"]: m for m in await db.list_payment_methods(active_only=True)}
    chosen = methods.get(method)
    if not chosen:
        await query.edit_message_text("⚠️ Payment method မတွေ့ပါ။")
        return

    order = context.user_data.setdefault("order", {})
    order["payment_method"] = method
    order["payment_phone"] = chosen.get("phone", "")
    context.user_data["stage"] = "await_screenshot"

    await query.edit_message_text(
        f"💳 <b>{method}</b>\n📱 Phone: <code>{chosen.get('phone','-')}</code>\n"
        f"💰 Amount: <b>{int(order.get('price', 0))} MMK</b>\n\n"
        "ငွေလွှဲပြီးရင် Screenshot ကို ဒီ chat ထဲ ပို့ပေးပါ 📸",
        parse_mode="HTML",
    )


async def receive_screenshot(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.user_data.get("stage") != "await_screenshot":
        return

    user = update.effective_user
    if await is_rate_limited(user.id):
        await update.effective_message.reply_text("⏳ Action များနေပါတယ်၊ ခဏစောင့်ပါ။")
        return

    photo = update.effective_message.photo
    if not photo:
        await update.effective_message.reply_text("📸 Screenshot ကို ပုံနဲ့ပဲ ပို့ပေးပါ။")
        return

    file_id = photo[-1].file_id

    # 16. Duplicate payment protection: same screenshot re-submitted
    if file_id in _used_file_ids:
        await update.effective_message.reply_text(
            "⚠️ ဒီ Screenshot ကို တစ်ခြား Order အတွက် သုံးပြီးသားဖြစ်ပါတယ်။ "
            "မှားယွင်းနေရင် Admin ကို ဆက်သွယ်ပေးပါ။"
        )
        return

    order = context.user_data.get("order", {})
    if not order.get("game_id") or not order.get("payment_method"):
        await update.effective_message.reply_text("⚠️ Order data မပြည့်စုံပါ — /order ကနေ ပြန်စပါ။")
        return

    order_id = await db.generate_order_id()
    order_record = {
        "order_id": order_id,
        "customer_id": user.id,
        "customer_username": user.username or user.first_name,
        "game_id": order["game_id"],
        "server_id": order["server_id"],
        "package_id": order["package_id"],
        "package_name": order["package_name"],
        "price": order["price"],
        "payment_method": order["payment_method"],
        "payment_phone": order["payment_phone"],
        "screenshot_file_id": file_id,
        "verified_nickname": order.get("verified_nickname"),
        "verified_country": order.get("verified_country"),
        "status": "pending",
        "chat_id": update.effective_chat.id,
    }
    await db.create_order(order_record)
    _used_file_ids.add(file_id)

    context.user_data.clear()

    await update.effective_message.reply_html(
        f"✅ <b>Order တင်ပြီးပါပြီ!</b>\n🧾 Order ID: <code>{order_id}</code>\n\n"
        "🟡 Admin confirm လုပ်ပေးမည့်အထိ ခဏစောင့်ပေးပါ 🙏"
    )

    await _notify_admins(update, context, order_id, order_record, file_id)


async def _notify_admins(update, context, order_id, order_record, file_id):
    from bot.handlers.confirm import build_admin_order_keyboard  # local import avoids cycle

    if not config.ADMIN_GROUP_ID:
        return

    caption = (
        "🆕 <b>New Order</b>\n"
        f"🧾 Order ID: <code>{order_id}</code>\n"
        f"👤 Customer: @{order_record['customer_username']} (<code>{order_record['customer_id']}</code>)\n"
        f"🎮 Game ID: <code>{order_record['game_id']}</code> (Server {order_record['server_id']})\n"
    )
    if order_record.get("verified_nickname"):
        country_txt = f" — {order_record['verified_country']}" if order_record.get("verified_country") else ""
        caption += f"✅ Verified: {order_record['verified_nickname']}{country_txt}\n"
    caption += (
        f"📦 Package: {order_record['package_name']} — {int(order_record['price'])} MMK\n"
        f"💳 Payment: {order_record['payment_method']}"
    )

    msg = await context.bot.send_photo(
        chat_id=config.ADMIN_GROUP_ID,
        photo=file_id,
        caption=caption,
        parse_mode="HTML",
        reply_markup=build_admin_order_keyboard(order_id),
    )
    await db.update_order(order_id, {"admin_msg_id": msg.message_id})
