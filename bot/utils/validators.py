"""
Validation helpers for MLBB-style Game ID + Server ID input.

Accepted user input formats:
    123456789 (12345)
    123456789(12345)
    123456789 12345
    123456789,12345
"""
import re

GAME_ID_PATTERN = re.compile(
    r"^\s*(?P<game_id>\d{6,12})\s*[\(\s,]+\s*(?P<server_id>\d{3,6})\s*\)?\s*$"
)

PHONE_PATTERN = re.compile(r"(09\d{7,9})")


def parse_game_id(text: str):
    """
    Returns (game_id, server_id) tuple if valid, else None.
    """
    if not text:
        return None
    match = GAME_ID_PATTERN.match(text.strip())
    if not match:
        return None
    return match.group("game_id"), match.group("server_id")


def is_valid_game_id(text: str) -> bool:
    return parse_game_id(text) is not None


def extract_phone(text: str):
    m = PHONE_PATTERN.search(text or "")
    return m.group(1) if m else None


def looks_like_amount(text: str) -> bool:
    """Loose check used when asking customer to confirm transferred amount."""
    return bool(re.search(r"\d{2,}", text or ""))


# ---------------------------------------------------------------------------
# OPTIONAL: live region/username verification via a third-party checker
# (e.g. an unofficial site like cekidml.caliph.dev). This is NOT required for
# the bot to work - it only adds an extra "does this ID actually exist"
# check on top of the format regex above.
#
# IMPORTANT: unofficial checker sites can go down or change at any time, so
# this call has a short timeout and NEVER blocks order creation on failure -
# it just falls back to "unverified" and lets an admin confirm manually.
#
# Find the real endpoint yourself via Browser DevTools -> Network tab while
# using the checker site, then set CHECK_API_URL / adjust parse_response().
# ---------------------------------------------------------------------------
import httpx

# Confirmed via Browser DevTools -> Network -> Response tab on cekidml.caliph.dev:
#   GET https://cekidml.caliph.dev/validasi?id=<game_id>&serverid=<server_id>
#   Success -> {"status":"success","result":{"nickname":"@shine180724","country":"Myanmar"}}
#   Failure -> {"status":"error", ...}  (exact shape may vary, handled defensively below)
CHECK_API_URL = "https://cekidml.caliph.dev/validasi"
CHECK_TIMEOUT_SECONDS = 5


async def verify_game_id_live(game_id: str, server_id: str):
    """
    Calls the unofficial cekidml.caliph.dev checker to confirm a Game ID +
    Server ID is real, and grabs the in-game nickname/country if found.

    Returns (ok: bool, info: dict | None, note: str)
        ok=True,  info={"nickname": "@shine180724", "country": "Myanmar"} -> verified
        ok=False, info=None  -> checker responded but ID not found / status != success
        ok=None,  info=None  -> checker unreachable / unexpected response
                                 (never blocks order creation)
    """
    if not CHECK_API_URL:
        return None, None, "verification not configured"

    try:
        async with httpx.AsyncClient(timeout=CHECK_TIMEOUT_SECONDS) as client:
            resp = await client.get(
                CHECK_API_URL, params={"id": game_id, "serverid": server_id}
            )
            resp.raise_for_status()
            data = resp.json()
    except Exception as e:
        # Site down / rate-limited / network issue -> don't block the order
        return None, None, f"checker unreachable: {e}"

    if data.get("status") == "success":
        result = data.get("result") or {}
        nickname = result.get("nickname")
        country = result.get("country")
        if nickname:
            return True, {"nickname": nickname, "country": country}, "verified"

    return False, None, "id not found"
