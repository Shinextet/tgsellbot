"""
22. Automatic Receipt Generation
23. Receipt Post / Post Update System
38. Completed Order / Transaction History System
"""
import datetime as dt

from telegram.ext import ContextTypes

from bot import config, database as db


def build_receipt_text(order: dict) -> str:
    created = order.get("created_at", "")
    return (
        "🧾 <b>PAYMENT RECEIPT</b>\n"
        "━━━━━━━━━━━━━━━\n"
        f"Order ID   : <code>{order['order_id']}</code>\n"
        f"Customer   : @{order.get('customer_username','-')}\n"
        f"Game ID    : <code>{order.get('game_id','-')}</code>\n"
        f"Server     : <code>{order.get('server_id','-')}</code>\n"
        f"Package    : {order.get('package_name','-')}\n"
        f"Amount     : {int(order.get('price',0))} MMK\n"
        f"Payment    : {order.get('payment_method','-')}\n"
        f"Date       : {created}\n"
        "━━━━━━━━━━━━━━━\n"
        "✅ Payment Confirmed — ကျေးဇူးတင်ပါတယ်! 🙏"
    )


async def send_receipt(context: ContextTypes.DEFAULT_TYPE, order_id: str):
    order = await db.get_order(order_id)
    if not order or not config.RECEIPT_CHAT_ID:
        return

    text = build_receipt_text(order)
    msg = await context.bot.send_message(
        chat_id=config.RECEIPT_CHAT_ID, text=text, parse_mode="HTML"
    )
    await db.update_order(order_id, {"receipt_msg_id": msg.message_id, "status": "completed"})
