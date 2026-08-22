"""
Detects which payment methods are mentioned inside a free-form text message
(typically the owner's "sell price" announcement) and pulls out the phone
number attached to each one, using regex.

Keywords handled (case-insensitive, Burmese + English):
    -ph            -> "Phone Bill" top-up
    wave           -> Wave Pay / Wave Money
    kpay           -> KBZ Pay
    aya            -> AYA Pay
    ငွေလွှဲ         -> Bank / manual money transfer
"""
import re
from typing import Dict, List, Tuple

_METHOD_PATTERNS: Dict[str, re.Pattern] = {
    "KPay":         re.compile(r"k\s*-?\s*pay|kbz\s*-?\s*pay", re.IGNORECASE),
    "Wave":         re.compile(r"wave\s*-?\s*(pay|money)?", re.IGNORECASE),
    "AYA":          re.compile(r"aya\s*-?\s*(pay|bank)?", re.IGNORECASE),
    "Phone":        re.compile(r"-\s*ph\b|phone\s*bill|ဖုန်း\s*ဘေလ်", re.IGNORECASE),
    "BankTransfer": re.compile(r"ငွေလွှဲ|bank\s*transfer", re.IGNORECASE),
}

_PHONE_NEAR = re.compile(r"(09\d{7,9})")


def extract_payment_methods(text: str) -> List[Tuple[str, str]]:
    """
    Scans `text` line by line. For every line that mentions a known payment
    method keyword, tries to find a phone number on that same line (falls
    back to scanning the whole text if not found on the line).

    Returns list of (method_name, phone_or_empty) tuples, de-duplicated,
    keeping the order methods first appear.
    """
    if not text:
        return []

    results: "dict[str, str]" = {}
    lines = text.splitlines() or [text]
    whole_text_phones = _PHONE_NEAR.findall(text)

    for line in lines:
        for method, pattern in _METHOD_PATTERNS.items():
            if pattern.search(line):
                phone_match = _PHONE_NEAR.search(line)
                phone = phone_match.group(1) if phone_match else (
                    whole_text_phones[0] if whole_text_phones else ""
                )
                # keep first occurrence, but upgrade empty phone if found later
                if method not in results or (not results[method] and phone):
                    results[method] = phone

    return list(results.items())


def format_payment_block(pairs: List[Tuple[str, str]]) -> str:
    """Pretty-print detected payment methods for confirmation messages."""
    if not pairs:
        return "⚠️ Payment method မတွေ့ပါ (ဥပမာ - Wave Pay, KPay, AYA, ငွေလွှဲ)"
    lines = ["💳 <b>Payment Methods တွေ့ရှိသည်</b>"]
    for method, phone in pairs:
        phone_txt = phone if phone else "（phone number မတွေ့ပါ）"
        lines.append(f"• {method} — {phone_txt}")
    return "\n".join(lines)
