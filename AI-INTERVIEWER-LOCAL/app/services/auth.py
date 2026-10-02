from __future__ import annotations

import base64
import hashlib
import hmac
import secrets
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from app.database import database


COOKIE_NAME = "ai_interview_session"
SESSION_HOURS = 8
SCRYPT_N = 2**14
SCRYPT_R = 8
SCRYPT_P = 1


class AuthError(ValueError):
    pass


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _token_hash(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def hash_password(password: str) -> str:
    if len(password) < 6:
        raise AuthError("Mật khẩu phải có ít nhất 6 ký tự")
    salt = secrets.token_bytes(16)
    digest = hashlib.scrypt(
        password.encode("utf-8"),
        salt=salt,
        n=SCRYPT_N,
        r=SCRYPT_R,
        p=SCRYPT_P,
        dklen=32,
    )
    return "$".join(
        (
            "scrypt",
            str(SCRYPT_N),
            str(SCRYPT_R),
            str(SCRYPT_P),
            base64.urlsafe_b64encode(salt).decode("ascii"),
            base64.urlsafe_b64encode(digest).decode("ascii"),
        )
    )


def verify_password(password: str, encoded: str) -> bool:
    try:
        algorithm, n, r, p, salt_text, digest_text = encoded.split("$", 5)
        if algorithm != "scrypt":
            return False
        expected = base64.urlsafe_b64decode(digest_text.encode("ascii"))
        actual = hashlib.scrypt(
            password.encode("utf-8"),
            salt=base64.urlsafe_b64decode(salt_text.encode("ascii")),
            n=int(n),
            r=int(r),
            p=int(p),
            dklen=len(expected),
        )
        return hmac.compare_digest(actual, expected)
    except (ValueError, TypeError):
        return False


def public_user(row: Any) -> dict[str, Any]:
    return {
        "user_id": int(row["user_id"]),
        "username": row["username"],
        "full_name": row["full_name"],
        "role": row["role"],
        "email": row["email"] or "",
        "student_id": row["student_id"] or "",
        "active": bool(row["active"]),
    }


def authenticate(database_path: Path, username: str, password: str) -> dict[str, Any]:
    with database(database_path) as connection:
        row = connection.execute(
            "SELECT * FROM users WHERE username = ? COLLATE NOCASE",
            (username.strip(),),
        ).fetchone()
    if not row or not row["active"] or not verify_password(password, row["password_hash"]):
        raise AuthError("Tên đăng nhập hoặc mật khẩu không đúng")
    return public_user(row)


def create_session(database_path: Path, user_id: int) -> tuple[str, int]:
    token = secrets.token_urlsafe(32)
    created_at = _now()
    expires_at = created_at + timedelta(hours=SESSION_HOURS)
    with database(database_path) as connection:
        connection.execute(
            "DELETE FROM auth_sessions WHERE expires_at <= ?",
            (created_at.isoformat(),),
        )
        connection.execute(
            """
            INSERT INTO auth_sessions (token_hash, user_id, expires_at, created_at)
            VALUES (?, ?, ?, ?)
            """,
            (
                _token_hash(token),
                user_id,
                expires_at.isoformat(),
                created_at.isoformat(),
            ),
        )
    return token, SESSION_HOURS * 60 * 60


def get_user_by_token(database_path: Path, token: str | None) -> dict[str, Any] | None:
    if not token:
        return None
    now = _now().isoformat()
    with database(database_path) as connection:
        row = connection.execute(
            """
            SELECT u.* FROM auth_sessions AS s
            JOIN users AS u ON u.user_id = s.user_id
            WHERE s.token_hash = ? AND s.expires_at > ? AND u.active = 1
            """,
            (_token_hash(token), now),
        ).fetchone()
    return public_user(row) if row else None


def revoke_session(database_path: Path, token: str | None) -> None:
    if not token:
        return
    with database(database_path) as connection:
        connection.execute(
            "DELETE FROM auth_sessions WHERE token_hash = ?", (_token_hash(token),)
        )
