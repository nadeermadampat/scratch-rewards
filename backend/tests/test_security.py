from app.core.security import (
    CLAIM_PATTERN,
    constant_time_equals,
    generate_claim_reference,
    generate_token,
    hash_identifier,
    is_well_formed_token,
)


def test_tokens_are_long_url_safe_and_unique():
    tokens = {generate_token() for _ in range(5000)}
    assert len(tokens) == 5000
    for token in list(tokens)[:50]:
        assert len(token) >= 43  # 32 random bytes, base64url
        assert is_well_formed_token(token)


def test_malformed_tokens_are_rejected():
    for bad in ("", "short", "a" * 31, "has space" * 5, "../../etc/passwd" * 3, "x" * 200):
        assert not is_well_formed_token(bad)


def test_claim_reference_format_and_uniqueness():
    refs = {generate_claim_reference() for _ in range(2000)}
    assert len(refs) == 2000
    assert all(CLAIM_PATTERN.match(ref) for ref in refs)
    # Ambiguous characters are never used.
    assert not any(ch in ref.split("-", 1)[1] for ref in refs for ch in "01OI")


def test_ip_hash_is_keyed_and_not_reversible_by_inspection():
    assert hash_identifier("203.0.113.9", "k1") == hash_identifier("203.0.113.9", "k1")
    assert hash_identifier("203.0.113.9", "k1") != hash_identifier("203.0.113.9", "k2")
    assert "203.0.113.9" not in hash_identifier("203.0.113.9", "k1")
    assert hash_identifier(None, "k1") is None


def test_constant_time_equals():
    assert constant_time_equals("abc", "abc")
    assert not constant_time_equals("abc", "abd")
