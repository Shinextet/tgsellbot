"""
5. Game ID Receive System
6. Game ID Copy System
7. Server / Region Check System
8. Invalid ID Validation System
9. Order Creation System
10. Unique Order ID System
11. Package / Product Selection System
16. Duplicate Order / Duplicate Payment Protection (part 1 - game id dup check)
17. Pending Order System
31. Anti-Spam / Rate Limit System (applied here)
"""
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from bot import database as db
from bot.utils import validators
from bot.utils.ratelimit import is_rate_limited

# Conversation "stages" kept in context.user_data:
#   stage: 'await_game_id' | 'await_payment' | 'await_screenshot'
#   package_id, game_id, server_id, payment_method, payment_phone


async def order_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Entry point: /order command or 'Order တင်မည်' button."""
    query = update.callback_query
    if query:
        await query.answer()

    if not await db.is_group_open():
        text = "🔴 လက်ရှိ Group ပိတ်ထားပါတယ်။ Owner ဖွင့်တဲ့အထိ ခဏစောင့်ပေးပါ 🙏"
        if query:
            await query.edit_message_text(text)
        else:
            await update.effective_message.reply_text(text)
        return

    packages = await db.list_packages(active_only=True)
    if not packages:
        text = "📭 လောလောဆယ် ရောင်းရန် Package မရှိသေးပါ။"
        if query:
            await query.edit_message_text(text)
        else:
            await update.effective_message.reply_text(text)
        return

    buttons = [
        [InlineKeyboardButton(f"{p['emoji']} {p['name']} — {int(p['price'])} MMK",
                               callback_data=f"pkg:{p['id']}")]
        for p in packages
    ]
    markup = InlineKeyboardMarkup(buttons)
    text = "📦 <b>Package ရွေးချယ်ပါ</b>"
    if query:
        await query.edit_message_text(text, reply_markup=markup, parse_mode="HTML")
    else:
        await update.effective_message.reply_html(text, reply_markup=markup)


async def package_selected(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user_id = update.effective_user.id
    if await is_rate_limited(user_id):
        await query.answer("⏳ Action များနေပါတယ်၊ ခဏစောင့်ပါ။", show_alert=True)
        return

    pkg_id = int(query.data.split(":")[1])
    package = await db.get_package(pkg_id)
    if not package:
        await query.edit_message_text("⚠️ Package မတွေ့ပါ၊ ပြန်ရွေးပေးပါ။")
        return

    context.user_data["order"] = {
        "package_id": package["id"],
        "package_name": package["name"],
        "price": package["price"],
    }
    context.user_data["stage"] = "await_game_id"

    await query.edit_message_text(
        f"✅ Package ရွေးလိုက်ပါပြီ: <b>{package['name']} — {int(package['price'])} MMK</b>\n\n"
        "🎮 <b>Game ID + Server</b> ကို ဒီ format အတိုင်း ပို့ပေးပါ:\n"
        "<code>123456789 (12345)</code>",
        parse_mode="HTML",
    )


async def receive_game_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Registered as a text MessageHandler; only acts when stage == await_game_id."""
    if context.user_data.get("stage") != "await_game_id":
        return

    user_id = update.effective_user.id
    if await is_rate_limited(user_id):
        await update.effective_message.reply_text("⏳ Action များနေပါတယ်၊ ခဏစောင့်ပါ။")
        return

    text = update.effective_message.text or ""
    parsed = validators.parse_game_id(text)

    if not parsed:
        await update.effective_message.reply_html(
            "❌ <b>Game ID / Server format မှားနေပါတယ်။</b>\n"
            "ဥပမာ: <code>123456789 (12345)</code>\nထပ်ကြိုးစားပေးပါ 🙏"
        )
        return

    game_id, server_id = parsed

    # Duplicate protection: same customer, same game id, still pending recently
    dup = await db.find_recent_pending(user_id, game_id, minutes=10)
    if dup:
        await update.effective_message.reply_html(
            f"⚠️ <b>Duplicate Order!</b>\nဒီ Game ID (<code>{game_id}</code>) နဲ့ Order တစ်ခု "
            f"Pending ရှိနေပါသေးတယ် (<code>{dup[0]['order_id']}</code>)။ Admin confirm လုပ်တဲ့ "
            "အထိ စောင့်ပေးပါ။"
        )
        return

    order = context.user_data.setdefault("order", {})
    order["game_id"] = game_id
    order["server_id"] = server_id
    context.user_data["stage"] = "await_payment"

    # Show a tappable copy of the ID for the customer/admin convenience
    copy_kb = InlineKeyboardMarkup(
        [[InlineKeyboardButton("📋 Copy ID", callback_data=f"copyid:{game_id}:{server_id}")]]
    )

    # Optional live verification via a third-party checker (see validators.py).
    # Never blocks the order if the checker is unreachable - just adds a note.
    ok, info, note = await validators.verify_game_id_live(game_id, server_id)
    if ok is True:
        order["verified_nickname"] = info["nickname"]
        order["verified_country"] = info.get("country")
        country_txt = f" ({info['country']})" if info.get("country") else ""
        verify_line = f"✅ Verified — In-game name: <b>{info['nickname']}</b>{country_txt}\n"
    elif ok is False:
        verify_line = "⚠️ ဒီ Game ID ကို checker ကနေ ရှာမတွေ့ပါ — ID/Server ပြန်စစ်ပေးပါ (Admin manual verify လုပ်နိုင်ပါတယ်)။\n"
    else:
        verify_line = ""  # checker not configured / unreachable -> stay silent, don't block

    await update.effective_message.reply_html(
        f"✅ Game ID: <code>{game_id}</code>\n🌍 Server: <code>{server_id}</code>\n"
        f"{verify_line}\n"
        "👍 Payment Method ရွေးပါ 👇",
        reply_markup=copy_kb,
    )

    from bot.handlers.payment import show_payment_options
    await show_payment_options(update, context)


async def copy_id_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """6. Game ID Copy System - shows the id/server as a copyable code block via alert."""
    query = update.callback_query
    _, game_id, server_id = query.data.split(":")
    await query.answer(f"{game_id} ({server_id}) — copied ✅", show_alert=True)
