"""Token, claim-reference and hashing helpers. All randomness comes from `secrets`."""
from __future__ import annotations

import hashlib
import hmac
import re
import secrets

TOKEN_BYTES = 32  # 256 bits of entropy -> 43 url-safe characters
TOKEN_PATTERN = re.compile(r"^[A-Za-z0-9_-]{32,128}$")

# No 0/O/1/I so references can be read out loud at a counter.
CLAIM_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
CLAIM_PATTERN = re.compile(r"^[A-Z]{2,5}-[A-Z2-9]{5}-[A-Z2-9]{5}$")


def generate_token() -> str:
    """Unguessable URL-safe token for scratch cards and verification hand-offs."""
    return secrets.token_urlsafe(TOKEN_BYTES)


def is_well_formed_token(value: str) -> bool:
    return bool(TOKEN_PATTERN.match(value))


def generate_claim_reference(prefix: str = "SCR") -> str:
    def block() -> str:
        return "".join(secrets.choice(CLAIM_ALPHABET) for _ in range(5))

    return f"{prefix}-{block()}-{block()}"


def hash_identifier(value: str | None, secret: str) -> str | None:
    """Keyed hash so raw IP addresses never reach the database."""
    if not value:
        return None
    return hmac.new(secret.encode(), value.encode(), hashlib.sha256).hexdigest()[:32]


def constant_time_equals(a: str, b: str) -> bool:
    return hmac.compare_digest(a.encode(), b.encode())
