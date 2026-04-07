import hashlib
import hmac
import os
import secrets
from dataclasses import dataclass
from datetime import datetime, timedelta

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from models import models
from utils.database import get_db
from utils.llm_user_context import build_user_llm_overrides, set_llm_runtime_overrides


TOKEN_TTL_HOURS = 24 * 7  # 7天
_bearer = HTTPBearer(auto_error=False)


def _utcnow() -> datetime:
    return datetime.utcnow()


def hash_password(password: str, salt: str | None = None) -> str:
    if salt is None:
        salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt.encode("utf-8"),
        200_000,
    ).hex()
    return f"{salt}${digest}"


def verify_password(password: str, password_hash: str) -> bool:
    try:
        salt, stored_digest = password_hash.split("$", 1)
    except ValueError:
        return False
    computed = hash_password(password, salt).split("$", 1)[1]
    return hmac.compare_digest(computed, stored_digest)


def hash_token(raw_token: str) -> str:
    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()


def issue_user_token(db: Session, user_id: int, ttl_hours: int = TOKEN_TTL_HOURS) -> tuple[str, datetime]:
    raw_token = secrets.token_urlsafe(48)
    expires_at = _utcnow() + timedelta(hours=ttl_hours)
    token_row = models.UserToken(
        user_id=user_id,
        token_hash=hash_token(raw_token),
        expires_at=expires_at,
    )
    db.add(token_row)
    db.commit()
    return raw_token, expires_at


@dataclass
class AuthContext:
    user: models.User
    token: models.UserToken


def get_auth_context(
    credentials: HTTPAuthorizationCredentials = Depends(_bearer),
    db: Session = Depends(get_db),
) -> AuthContext:
    if not credentials or credentials.scheme.lower() != "bearer":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="未登录或token缺失")

    token_hash_value = hash_token(credentials.credentials)
    token_row = (
        db.query(models.UserToken)
        .filter(models.UserToken.token_hash == token_hash_value)
        .filter(models.UserToken.revoked_at.is_(None))
        .first()
    )

    if not token_row:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="无效token")

    if token_row.expires_at <= _utcnow():
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="token已过期")

    user = db.query(models.User).filter(models.User.id == token_row.user_id).first()
    if not user or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="用户不可用")

    return AuthContext(user=user, token=token_row)


def get_current_user(context: AuthContext = Depends(get_auth_context)) -> models.User:
    set_llm_runtime_overrides(build_user_llm_overrides(context.user))
    return context.user


def revoke_token(db: Session, token_row: models.UserToken) -> None:
    token_row.revoked_at = _utcnow()
    db.add(token_row)
    db.commit()


def normalize_username(username: str) -> str:
    return (username or "").strip()


def validate_credentials(username: str, password: str) -> tuple[str, str]:
    normalized_username = normalize_username(username)
    normalized_password = (password or "").strip()

    if len(normalized_username) < 2:
        raise HTTPException(status_code=400, detail="账号至少2个字符")
    if len(normalized_password) < 4:
        raise HTTPException(status_code=400, detail="密码至少4个字符")
    if len(normalized_username) > 64:
        raise HTTPException(status_code=400, detail="账号长度不能超过64")

    return normalized_username, normalized_password