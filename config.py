"""
Central configuration - loads everything from environment variables (.env locally,
Render 'Environment' tab in production).
"""
import os
from dotenv import load_dotenv

load_dotenv()


def _int_list(raw: str):
    return [int(x.strip()) for x in raw.split(",") if x.strip()]


BOT_TOKEN = os.getenv("BOT_TOKEN", "")

OWNER_IDS = _int_list(os.getenv("OWNER_IDS", ""))
GROUP_ID = int(os.getenv("GROUP_ID", "0") or 0)
ADMIN_GROUP_ID = int(os.getenv("ADMIN_GROUP_ID", "0") or 0)
RECEIPT_CHAT_ID = int(os.getenv("RECEIPT_CHAT_ID", str(GROUP_ID)) or 0)

SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "")

PORT = int(os.getenv("PORT", "8080"))

ORDER_TIMEOUT_MINUTES = int(os.getenv("ORDER_TIMEOUT_MINUTES", "15"))

RATE_LIMIT_MAX_ACTIONS = int(os.getenv("RATE_LIMIT_MAX_ACTIONS", "6"))
RATE_LIMIT_WINDOW_SECONDS = int(os.getenv("RATE_LIMIT_WINDOW_SECONDS", "10"))

if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN missing - set it in .env / Render environment variables")
if not SUPABASE_URL or not SUPABASE_KEY:
    raise RuntimeError("SUPABASE_URL / SUPABASE_KEY missing - set them in .env / Render")
