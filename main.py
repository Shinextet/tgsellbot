"""
Telegram Sell Bot - main entrypoint.

Run locally:
    python -m bot.main

Deploy on Render:
    Start Command -> python -m bot.main
"""
import logging

from telegram import Update
from telegram.ext import (
    Application,
    ApplicationBuilder,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from bot import config
from bot.keep_alive import start_keep_alive
from bot.handlers import (
    start as h_start,
    group_control as h_group,
    admin as h_admin,
    order as h_order,
    payment as h_payment,
    confirm as h_confirm,
    search as h_search,
    report as h_report,
    settings as h_settings,
    jobs as h_jobs,
)

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)


async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    """34. Error / Failed Transaction Handling"""
    logger.error("Exception while handling an update:", exc_info=context.error)
    if config.ADMIN_GROUP_ID:
        try:
            await context.bot.send_message(
                chat_id=config.ADMIN_GROUP_ID,
                text=f"🛑 <b>Bot Error</b>\n<code>{context.error}</code>",
                parse_mode="HTML",
            )
        except Exception:
            pass


async def order_status_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await h_start.mystatus_cmd(update, context)


def build_application() -> Application:
    app = ApplicationBuilder().token(config.BOT_TOKEN).build()

    # ---- 1. Start / Help / DM status ----
    app.add_handler(CommandHandler("start", h_start.start_cmd))
    app.add_handler(CommandHandler("help", h_start.help_cmd))
    app.add_handler(CommandHandler("mystatus", h_start.mystatus_cmd))

    # ---- 2. Group open/close ----
    app.add_handler(CommandHandler("open", h_group.open_cmd))
    app.add_handler(CommandHandler("close", h_group.close_cmd))

    # ---- 3/4. Admin management ----
    app.add_handler(CommandHandler("addadmin", h_admin.addadmin_cmd))
    app.add_handler(CommandHandler("removeadmin", h_admin.removeadmin_cmd))
    app.add_handler(CommandHandler("admins", h_admin.admins_cmd))

    # ---- Order flow ----
    app.add_handler(CommandHandler("order", h_order.order_start))
    app.add_handler(CallbackQueryHandler(h_order.order_start, pattern=r"^order:start$"))
    app.add_handler(CallbackQueryHandler(order_status_button, pattern=r"^order:mystatus$"))
    app.add_handler(CallbackQueryHandler(h_order.package_selected, pattern=r"^pkg:\d+$"))
    app.add_handler(CallbackQueryHandler(h_order.copy_id_callback, pattern=r"^copyid:"))
    app.add_handler(CallbackQueryHandler(h_payment.payment_selected, pattern=r"^pay:"))

    # ---- Admin confirm / reject ----
    app.add_handler(CallbackQueryHandler(h_confirm.confirm_callback, pattern=r"^conf:"))
    app.add_handler(CallbackQueryHandler(h_confirm.reject_callback, pattern=r"^rej:"))

    # ---- Search / report / stats ----
    app.add_handler(CommandHandler("search", h_search.search_cmd))
    app.add_handler(CommandHandler("report", h_report.report_cmd))
    app.add_handler(CommandHandler("stats", h_report.stats_cmd))

    # ---- Settings / panel / backup ----
    app.add_handler(CommandHandler("panel", h_settings.panel_cmd))
    app.add_handler(CommandHandler("addpackage", h_settings.addpackage_cmd))
    app.add_handler(CommandHandler("removepackage", h_settings.removepackage_cmd))
    app.add_handler(CommandHandler("packages", h_settings.packages_cmd))
    app.add_handler(CommandHandler("setpayment", h_settings.setpayment_cmd))
    app.add_handler(CommandHandler("logs", h_settings.logs_cmd))
    app.add_handler(CommandHandler("backup", h_settings.backup_cmd))

    # ---- Free text: sell-price capture (group=0) then game-id capture (group=1) ----
    app.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, h_group.catch_sell_price_message),
        group=0,
    )
    app.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, h_order.receive_game_id),
        group=1,
    )

    # ---- Photos: payment screenshot ----
    app.add_handler(MessageHandler(filters.PHOTO, h_payment.receive_screenshot), group=2)

    # ---- Error handler ----
    app.add_error_handler(error_handler)

    # ---- Scheduled jobs ----
    job_queue = app.job_queue
    if job_queue:
        job_queue.run_repeating(h_jobs.pending_reminder_job, interval=300, first=60)
        job_queue.run_daily(h_report.daily_report_job, time=__import__("datetime").time(hour=17, minute=0))

    return app


def main():
    start_keep_alive()
    app = build_application()
    logger.info("Bot starting (polling)...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
