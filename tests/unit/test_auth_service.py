from datetime import UTC, datetime, timedelta

import pytest

from src.auth.service import (
    LOCKOUT_MINUTES,
    MAX_FAILED_ATTEMPTS,
    authenticate_user,
    create_user,
    derive_session_key,
    enable_panic_freeze,
    get_user_auth_config,
    is_user_frozen,
    set_trusted_contact,
)
from src.database.init_db import init_db


def test_authenticate_user_success(tmp_path) -> None:
    db_path = tmp_path / "auth.db"
    init_db(db_path)
    create_user("u1", "+919999999999", "1234", db_path=db_path)

    result = authenticate_user("u1", "1234", db_path=db_path)
    assert result.is_authenticated is True
    assert result.reason == "authenticated"


def test_lockout_after_repeated_failures(tmp_path) -> None:
    db_path = tmp_path / "auth.db"
    init_db(db_path)
    create_user("u2", "+919888888888", "4321", db_path=db_path)

    current_time = datetime(2026, 2, 23, 12, 0, tzinfo=UTC)
    for _ in range(MAX_FAILED_ATTEMPTS - 1):
        result = authenticate_user("u2", "0000", db_path=db_path, now=current_time)
        assert result.is_authenticated is False
        assert result.reason == "invalid_pin"

    lockout_result = authenticate_user("u2", "0000", db_path=db_path, now=current_time)
    assert lockout_result.is_authenticated is False
    assert lockout_result.reason == "lockout_started"
    assert lockout_result.lockout_until is not None

    blocked = authenticate_user("u2", "4321", db_path=db_path, now=current_time)
    assert blocked.is_authenticated is False
    assert blocked.reason == "locked_out"

    after_lockout = current_time + timedelta(minutes=LOCKOUT_MINUTES, seconds=1)
    recovered = authenticate_user("u2", "4321", db_path=db_path, now=after_lockout)
    assert recovered.is_authenticated is True
    assert recovered.reason == "authenticated"


def test_derive_session_key_requires_valid_auth(tmp_path) -> None:
    db_path = tmp_path / "auth.db"
    init_db(db_path)
    create_user("u3", "+919777777777", "5678", db_path=db_path)

    key_one = derive_session_key("u3", "5678", db_path=db_path)
    key_two = derive_session_key("u3", "5678", db_path=db_path)
    assert key_one == key_two
    assert len(key_one) == 32

    with pytest.raises(PermissionError):
        derive_session_key("u3", "0000", db_path=db_path)


def test_create_user_duplicate_requires_replace_flag(tmp_path) -> None:
    db_path = tmp_path / "auth.db"
    init_db(db_path)
    create_user("u4", "+919666666666", "1234", db_path=db_path)

    with pytest.raises(ValueError, match="user_exists:u4"):
        create_user("u4", "+919666666666", "4321", db_path=db_path)

    # replace should allow user credential reset
    create_user("u4", "+919666666666", "4321", db_path=db_path, replace_existing=True)
    assert authenticate_user("u4", "4321", db_path=db_path).is_authenticated is True


def test_trusted_contact_and_panic_freeze_settings(tmp_path) -> None:
    db_path = tmp_path / "auth.db"
    init_db(db_path)
    create_user("u5", "+919555000111", "1234", db_path=db_path)

    set_trusted_contact("u5", "1234", "+919888777666", db_path=db_path)
    cfg = get_user_auth_config("u5", db_path=db_path)
    assert cfg["trusted_contact"] == "+919888777666"

    _ = enable_panic_freeze("u5", "1234", minutes=30, db_path=db_path)
    assert is_user_frozen("u5", db_path=db_path) is True
