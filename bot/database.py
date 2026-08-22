"""
Thin async wrapper around the Supabase (Postgres) client.
supabase-py is synchronous, so every call is pushed to a thread via asyncio.to_thread
to avoid blocking the bot's event loop.
"""
import asyncio
import datetime as dt
import random
from typing import Optional

from supabase import create_client, Client

from bot import config

_client: Client = create_client(config.SUPABASE_URL, config.SUPABASE_KEY)


async def _run(fn, *args, **kwargs):
    return await asyncio.to_thread(fn, *args, **kwargs)


# ---------------------------------------------------------------- settings --
def _get_setting_sync(key: str) -> Optional[str]:
    res = _client.table("settings").select("value").eq("key", key).execute()
    return res.data[0]["value"] if res.data else None


def _set_setting_sync(key: str, value: str):
    _client.table("settings").upsert({"key": key, "value": value}).execute()


async def get_setting(key: str) -> Optional[str]:
    return await _run(_get_setting_sync, key)


async def set_setting(key: str, value: str):
    await _run(_set_setting_sync, key, value)


async def is_group_open() -> bool:
    val = await get_setting("group_open")
    return val == "true"


# ------------------------------------------------------------------ admins --
def _list_admins_sync():
    return _client.table("admins").select("*").execute().data


def _add_admin_sync(user_id: int, username: str, role: str, added_by: int):
    _client.table("admins").upsert(
        {"user_id": user_id, "username": username, "role": role, "added_by": added_by}
    ).execute()


def _remove_admin_sync(user_id: int):
    _client.table("admins").delete().eq("user_id", user_id).execute()


def _get_admin_sync(user_id: int):
    res = _client.table("admins").select("*").eq("user_id", user_id).execute()
    return res.data[0] if res.data else None


async def list_admins():
    return await _run(_list_admins_sync)


async def add_admin(user_id: int, username: str, role: str, added_by: int):
    await _run(_add_admin_sync, user_id, username, role, added_by)


async def remove_admin(user_id: int):
    await _run(_remove_admin_sync, user_id)


async def get_admin(user_id: int):
    return await _run(_get_admin_sync, user_id)


async def is_admin(user_id: int) -> bool:
    if user_id in config.OWNER_IDS:
        return True
    row = await get_admin(user_id)
    return row is not None


async def is_owner(user_id: int) -> bool:
    if user_id in config.OWNER_IDS:
        return True
    row = await get_admin(user_id)
    return bool(row and row.get("role") == "owner")


# --------------------------------------------------------------- packages --
def _list_packages_sync(active_only=True):
    q = _client.table("packages").select("*").order("sort_order")
    if active_only:
        q = q.eq("active", True)
    return q.execute().data


def _get_package_sync(pkg_id: int):
    res = _client.table("packages").select("*").eq("id", pkg_id).execute()
    return res.data[0] if res.data else None


async def list_packages(active_only=True):
    return await _run(_list_packages_sync, active_only)


async def get_package(pkg_id: int):
    return await _run(_get_package_sync, pkg_id)


# --------------------------------------------------------- payment methods --
def _upsert_payment_method_sync(method: str, phone: str):
    _client.table("payment_methods").upsert(
        {"method": method, "phone": phone, "active": True}
    ).execute()


def _list_payment_methods_sync(active_only=True):
    q = _client.table("payment_methods").select("*")
    if active_only:
        q = q.eq("active", True)
    return q.execute().data


async def upsert_payment_method(method: str, phone: str):
    await _run(_upsert_payment_method_sync, method, phone)


async def list_payment_methods(active_only=True):
    return await _run(_list_payment_methods_sync, active_only)


# ---------------------------------------------------------- sell price msg --
def _save_sell_price_message_sync(chat_id: int, message_id: int, content: str):
    _client.table("sell_price_messages").insert(
        {"chat_id": chat_id, "message_id": message_id, "content": content}
    ).execute()


def _latest_sell_price_message_sync(chat_id: int):
    res = (
        _client.table("sell_price_messages")
        .select("*")
        .eq("chat_id", chat_id)
        .order("created_at", desc=True)
        .limit(1)
        .execute()
    )
    return res.data[0] if res.data else None


async def save_sell_price_message(chat_id: int, message_id: int, content: str):
    await _run(_save_sell_price_message_sync, chat_id, message_id, content)


async def latest_sell_price_message(chat_id: int):
    return await _run(_latest_sell_price_message_sync, chat_id)


# -------------------------------------------------------------------orders --
def _gen_order_id_sync() -> str:
    today = dt.datetime.utcnow().strftime("%Y%m%d")
    for _ in range(20):
        candidate = f"ORD-{today}-{random.randint(1000, 9999)}"
        exists = _client.table("orders").select("order_id").eq("order_id", candidate).execute()
        if not exists.data:
            return candidate
    # extreme fallback
    return f"ORD-{today}-{random.randint(10000, 99999)}"


async def generate_order_id() -> str:
    return await _run(_gen_order_id_sync)


def _create_order_sync(order: dict):
    _client.table("orders").insert(order).execute()


def _update_order_sync(order_id: str, fields: dict):
    _client.table("orders").update(fields).eq("order_id", order_id).execute()


def _get_order_sync(order_id: str):
    res = _client.table("orders").select("*").eq("order_id", order_id).execute()
    return res.data[0] if res.data else None


def _find_recent_pending_sync(customer_id: int, game_id: str, minutes: int = 10):
    since = (dt.datetime.utcnow() - dt.timedelta(minutes=minutes)).isoformat()
    res = (
        _client.table("orders")
        .select("*")
        .eq("customer_id", customer_id)
        .eq("game_id", game_id)
        .eq("status", "pending")
        .gte("created_at", since)
        .execute()
    )
    return res.data


def _pending_orders_older_than_sync(minutes: int):
    cutoff = (dt.datetime.utcnow() - dt.timedelta(minutes=minutes)).isoformat()
    res = (
        _client.table("orders")
        .select("*")
        .eq("status", "pending")
        .lte("created_at", cutoff)
        .execute()
    )
    return res.data


def _sales_between_sync(start_iso: str, end_iso: str):
    res = (
        _client.table("orders")
        .select("*")
        .in_("status", ["confirmed", "completed"])
        .gte("confirmed_at", start_iso)
        .lte("confirmed_at", end_iso)
        .execute()
    )
    return res.data


def _all_orders_sync(limit: int = 5000):
    res = (
        _client.table("orders")
        .select("*")
        .order("created_at", desc=True)
        .limit(limit)
        .execute()
    )
    return res.data


async def create_order(order: dict):
    await _run(_create_order_sync, order)


async def update_order(order_id: str, fields: dict):
    await _run(_update_order_sync, order_id, fields)


async def get_order(order_id: str):
    return await _run(_get_order_sync, order_id)


async def find_recent_pending(customer_id: int, game_id: str, minutes: int = 10):
    return await _run(_find_recent_pending_sync, customer_id, game_id, minutes)


async def pending_orders_older_than(minutes: int):
    return await _run(_pending_orders_older_than_sync, minutes)


async def sales_between(start_iso: str, end_iso: str):
    return await _run(_sales_between_sync, start_iso, end_iso)


async def all_orders(limit: int = 5000):
    return await _run(_all_orders_sync, limit)


# --------------------------------------------------------------- action log --
def _log_action_sync(admin_id: int, admin_username: str, action: str, detail: str):
    _client.table("action_logs").insert(
        {"admin_id": admin_id, "admin_username": admin_username, "action": action, "detail": detail}
    ).execute()


async def log_action(admin_id: int, admin_username: str, action: str, detail: str = ""):
    await _run(_log_action_sync, admin_id, admin_username, action, detail)


def _recent_logs_sync(limit: int = 20):
    res = (
        _client.table("action_logs")
        .select("*")
        .order("created_at", desc=True)
        .limit(limit)
        .execute()
    )
    return res.data


async def recent_logs(limit: int = 20):
    return await _run(_recent_logs_sync, limit)


# ------------------------------------------------------------- rate limits --
def _get_rate_sync(user_id: int):
    res = _client.table("rate_limits").select("*").eq("user_id", user_id).execute()
    return res.data[0] if res.data else None


def _upsert_rate_sync(user_id: int, window_start: str, count: int):
    _client.table("rate_limits").upsert(
        {"user_id": user_id, "window_start": window_start, "count": count}
    ).execute()


async def get_rate(user_id: int):
    return await _run(_get_rate_sync, user_id)


async def upsert_rate(user_id: int, window_start: str, count: int):
    await _run(_upsert_rate_sync, user_id, window_start, count)
