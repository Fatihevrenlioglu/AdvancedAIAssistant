"""Tests for security helpers."""
from __future__ import annotations

import time

import pytest

from src.auth.auth_manager import AuthManager
from src.security.input_validator import InputValidator


def test_input_validator_sanitize_string() -> None:
    """sanitize_string should strip HTML and enforce max length."""
    assert InputValidator.sanitize_string("<b>Hello</b>\n", max_length=5) == "Hello"
    assert InputValidator.sanitize_string("<script>x</script>abc", max_length=2) == "xa"


def test_input_validator_validate_email() -> None:
    """validate_email should distinguish valid and invalid emails."""
    assert InputValidator.validate_email("user@example.com") is True
    assert InputValidator.validate_email("invalid-email") is False


def test_input_validator_validate_sql_input() -> None:
    """validate_sql_input should reject obvious injection patterns."""
    assert InputValidator.validate_sql_input("normal value") is True
    assert InputValidator.validate_sql_input("1 OR 1=1; DROP TABLE users;") is False


def test_auth_manager_create_and_verify_token_round_trip() -> None:
    """AuthManager should round-trip JWT payloads."""
    auth = AuthManager("secret", expiry_minutes=5)
    token = auth.create_token("user-1", roles=["admin"])
    payload = auth.verify_token(token)
    assert payload["sub"] == "user-1"
    assert payload["roles"] == ["admin"]


def test_auth_manager_verify_token_raises_for_invalid_and_expired_tokens() -> None:
    """AuthManager should reject invalid and expired tokens."""
    auth = AuthManager("secret", expiry_minutes=0)
    token = auth.create_token("user-1")
    time.sleep(1)
    with pytest.raises(ValueError):
        auth.verify_token(token)
    with pytest.raises(ValueError):
        auth.verify_token("not-a-token")


def test_auth_manager_hash_and_verify_password() -> None:
    """AuthManager should hash and verify passwords."""
    auth = AuthManager("secret")
    hashed = auth.hash_password("strong-password")
    assert hashed != "strong-password"
    assert auth.verify_password("strong-password", hashed) is True
    assert auth.verify_password("wrong-password", hashed) is False
