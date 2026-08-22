"""
27. Pending Order Timeout / Reminder System
"""
import logging

from telegram.ext import ContextTypes

from bot import config, database as db

logger = logging.getLogger(__name__)

_reminded: set[str] = set()  # order_ids we've already nudged, to avoid spamming


async def pending_reminder_job(context: ContextTypes.DEFAULT_TYPE):
    if not config.ADMIN_GROUP_ID:
        return

    stale = await db.pending_orders_older_than(config.ORDER_TIMEOUT_MINUTES)
    for order in stale:
        oid = order["order_id"]
        if oid in _reminded:
            continue
        _reminded.add(oid)
        try:
            await context.bot.send_message(
                chat_id=config.ADMIN_GROUP_ID,
                text=(
                    f"⏰ <b>Pending Reminder</b>\n🧾 Order <code>{oid}</code> က "
                    f"{config.ORDER_TIMEOUT_MINUTES} မိနစ်ကျော် Pending ဖြစ်နေပါပြီ — "
                    "Confirm/Reject လုပ်ပေးပါ 🙏"
                ),
                parse_mode="HTML",
            )
        except Exception as e:
            logger.warning("reminder send failed: %s", e)
