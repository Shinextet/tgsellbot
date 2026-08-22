"""
Tiny Flask web server whose only job is to answer HTTP GET / with 200 OK,
so that UptimeRobot (or any pinger) can hit it every few minutes and stop
Render's free-tier service from sleeping.

Runs in a background thread inside the same process as the Telegram bot.
"""
import logging
import threading

from flask import Flask

from bot import config

logger = logging.getLogger(__name__)

app = Flask(__name__)


@app.route("/")
def home():
    return "Telegram Sell Bot is alive ✅", 200


@app.route("/health")
def health():
    return {"status": "ok"}, 200


def _run():
    # use=False + threaded server, good enough for a lightweight ping endpoint
    app.run(host="0.0.0.0", port=config.PORT)


def start_keep_alive():
    t = threading.Thread(target=_run, daemon=True)
    t.start()
    logger.info("Keep-alive web server started on port %s", config.PORT)
