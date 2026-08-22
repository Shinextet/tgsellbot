"""
Very small anti-spam / rate-limit guard.

Uses the `rate_limits` table so it also works correctly across bot restarts
and (if ever scaled) multiple processes.
"""
import datetime as dt

from bot import config, database as db


async def is_rate_limited(user_id: int) -> bool:
    """
    Returns True if the user has exceeded RATE_LIMIT_MAX_ACTIONS actions
    within RATE_LIMIT_WINDOW_SECONDS and should be blocked this time.
    """
    now = dt.datetime.utcnow()
    row = await db.get_rate(user_id)

    if not row:
        await db.upsert_rate(user_id, now.isoformat(), 1)
        return False

    window_start = dt.datetime.fromisoformat(row["window_start"])
    elapsed = (now - window_start).total_seconds()

    if elapsed > config.RATE_LIMIT_WINDOW_SECONDS:
        # new window
        await db.upsert_rate(user_id, now.isoformat(), 1)
        return False

    new_count = row["count"] + 1
    await db.upsert_rate(user_id, row["window_start"], new_count)
    return new_count > config.RATE_LIMIT_MAX_ACTIONS
