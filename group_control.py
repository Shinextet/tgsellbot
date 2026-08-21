"""
2. Group Open / Close System
   - /open  (owner only): opens the group for orders, then waits for the
     owner's very next text message in the group = the "sell price" list.
     That message gets pinned; the previous pinned sell-price message
     (if any) is unpinned automatically.
   - /close (owner/admin): closes the group, stops new orders.

   Also runs the payment-method regex extractor on the sell-price message
   so /order can show the right payment buttons automatically.
"""
import logging

from telegram import Update
from telegram.error import TelegramError
from telegram.ext import ContextTypes

from bot import config, database as db
from bot.utils import payment_regex

logger = logging.getLogger(__name__)

# chat_id -> True while we're waiting for the owner's sell-price message
_awaiting_price: dict[int, int] = {}  # chat_id -> owner_user_id


async def open_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    chat = update.effective_chat

    if not await db.is_owner(user.id):
        await update.effective_message.reply_text("🚫 Owner ပဲ /open ဖွင့်ခွင့်ရှိပါတယ်။")
        return

    await db.set_setting("group_open", "true")
    _awaiting_price[chat.id] = user.id

    await update.effective_message.reply_html(
        "🟢 <b>Group ကို ဖွင့်လိုက်ပါပြီ!</b>\n\n"
        "👉 Owner ရေ — ဒီနောက် ပို့မယ့် <b>sell price</b> message ကို bot က "
        "အလိုအလျောက် pin လုပ်ပေးမှာဖြစ်ပါတယ် (ဟောင်းတစ်ခုရှိရင် unpin လုပ်ပေးပါမယ်)။\n"
        "ချက်ချင်း sell price list ကို ဒီ group ထဲမှာ ပို့ပေးပါ။"
    )


async def close_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    chat = update.effective_chat

    if not await db.is_admin(user.id):
        await update.effective_message.reply_text("🚫 Admin ပဲ /close ပိတ်ခွင့်ရှိပါတယ်။")
        return

    await db.set_setting("group_open", "false")
    _awaiting_price.pop(chat.id, None)
    await update.effective_message.reply_html(
        "🔴 <b>Group ကို ပိတ်လိုက်ပါပြီ။</b> Order အသစ် လက်ခံမည် မဟုတ်တော့ပါ။"
    )


async def catch_sell_price_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Registered as a MessageHandler (group chats, text only, high priority)
    to catch the owner's sell-price message right after /open.
    """
    chat = update.effective_chat
    user = update.effective_user
    message = update.effective_message

    owner_id = _awaiting_price.get(chat.id)
    if owner_id is None or user.id != owner_id or not message.text:
        return  # not what we're waiting for -> let other handlers run

    # 1) unpin + note the old sell-price message
    old = await db.latest_sell_price_message(chat.id)
    if old:
        try:
            await context.bot.unpin_chat_message(chat_id=chat.id, message_id=old["message_id"])
        except TelegramError as e:
            logger.warning("unpin failed: %s", e)

    # 2) pin the new one
    try:
        await context.bot.pin_chat_message(
            chat_id=chat.id, message_id=message.message_id, disable_notification=False
        )
    except TelegramError as e:
        logger.warning("pin failed: %s", e)
        await message.reply_text(
            "⚠️ Pin မလုပ်နိုင်ပါ — bot ကို group admin (Pin Messages permission) လုပ်ပေးထားပါ။"
        )

    await db.save_sell_price_message(chat.id, message.message_id, message.text)

    # 3) regex-extract payment methods & phone numbers, store them
    pairs = payment_regex.extract_payment_methods(message.text)
    for method, phone in pairs:
        if phone:
            await db.upsert_payment_method(method, phone)

    await db.log_action(user.id, user.username or user.first_name, "sell_price_posted",
                         message.text[:200])

    _awaiting_price.pop(chat.id, None)

    await message.reply_html(
        "📌 <b>Sell price ကို Pin လုပ်ပြီးပါပြီ!</b>\n\n" + payment_regex.format_payment_block(pairs)
    )
