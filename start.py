"""
1. Bot Start / Welcome Flow
25. Private Chat / DM System
"""
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from bot import database as db

WELCOME_TEXT = (
    "👋 <b>MLBB ID Top-Up Bot</b> မှ ကြိုဆိုပါတယ်။\n\n"
    "🎮 Diamond / Pass အမြန်ဆုံး ဝယ်ယူလိုပါက အောက်က <b>Order တင်မည်</b> ခလုတ်ကို "
    "နှိပ်ပြီး လုပ်ဆောင်ပေးပါ။\n\n"
    "❓ အကူအညီလိုပါက /help ကို ရိုက်ထည့်ပါ။"
)

HELP_TEXT = (
    "🛠 <b>အသုံးပြုနည်း</b>\n\n"
    "/order — Package ရွေးပြီး Order အသစ်တင်ရန်\n"
    "/mystatus — မိမိရဲ့ နောက်ဆုံး Order status စစ်ရန်\n"
    "/search &lt;order_id&gt; — Order တစ်ခုချင်းစီရှာရန် (admin)\n\n"
    "🎮 <b>Game ID ပို့ရန် format:</b>\n"
    "<code>123456789 (12345)</code>  — ID (Server)\n\n"
    "💳 Payment လုပ်ပြီးရင် screenshot ကို ဒီ chat ထဲပဲ ပို့ပေးပါ။"
)


async def start_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("🛒 Order တင်မည်", callback_data="order:start")],
            [InlineKeyboardButton("📦 Order Status", callback_data="order:mystatus")],
        ]
    )
    await update.effective_message.reply_html(WELCOME_TEXT, reply_markup=keyboard)


async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.effective_message.reply_html(HELP_TEXT)


async def mystatus_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    orders = await db.all_orders(limit=200)
    mine = [o for o in orders if o["customer_id"] == user_id]
    if not mine:
        await update.effective_message.reply_text("📭 Order မရှိသေးပါ။")
        return
    latest = mine[0]
    status_emoji = {
        "pending": "🟡 Pending",
        "confirmed": "✅ Confirmed",
        "rejected": "❌ Rejected",
        "completed": "🎉 Completed",
    }.get(latest["status"], latest["status"])
    text = (
        f"🧾 <b>Order ID:</b> <code>{latest['order_id']}</code>\n"
        f"📦 Package: {latest.get('package_name','-')}\n"
        f"💰 Price: {latest.get('price','-')} MMK\n"
        f"📌 Status: {status_emoji}"
    )
    await update.effective_message.reply_html(text)
