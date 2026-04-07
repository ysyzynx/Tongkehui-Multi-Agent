from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from models import models, schemas
from utils.auth import (
    get_auth_context,
    hash_password,
    issue_user_token,
    normalize_username,
    revoke_token,
    validate_credentials,
    verify_password,
    AuthContext,
)
from utils.database import get_db
from utils.response import success


router = APIRouter(tags=["Auth"])


@router.post("/auth/register")
def register(payload: schemas.AuthRegisterRequest, db: Session = Depends(get_db)):
    username, password = validate_credentials(payload.username, payload.password)

    existing = db.query(models.User).filter(models.User.username == username).first()
    if existing:
        raise HTTPException(status_code=400, detail="该账号已存在，请直接登录")

    user = models.User(
        username=username,
        password_hash=hash_password(password),
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    raw_token, expires_at = issue_user_token(db, user.id)
    data = schemas.AuthTokenData(
        access_token=raw_token,
        expires_at=expires_at,
        user=schemas.AuthUserInfo(id=user.id, username=user.username),
    )
    return success(data=data.model_dump(), msg="注册成功")


@router.post("/auth/login")
def login(payload: schemas.AuthLoginRequest, db: Session = Depends(get_db)):
    username = normalize_username(payload.username)
    password = (payload.password or "").strip()
    if not username or not password:
        raise HTTPException(status_code=400, detail="请输入账号和密码")

    user = db.query(models.User).filter(models.User.username == username).first()
    if not user or not verify_password(password, user.password_hash):
        raise HTTPException(status_code=401, detail="账号或密码错误")
    if not user.is_active:
        raise HTTPException(status_code=403, detail="账号已禁用")

    raw_token, expires_at = issue_user_token(db, user.id)
    data = schemas.AuthTokenData(
        access_token=raw_token,
        expires_at=expires_at,
        user=schemas.AuthUserInfo(id=user.id, username=user.username),
    )
    return success(data=data.model_dump(), msg="登录成功")


@router.get("/auth/me")
def me(context: AuthContext = Depends(get_auth_context)):
    return success(
        data=schemas.AuthUserInfo(id=context.user.id, username=context.user.username).model_dump(),
        msg="获取成功",
    )


@router.post("/auth/logout")
def logout(db: Session = Depends(get_db), context: AuthContext = Depends(get_auth_context)):
    revoke_token(db, context.token)
    return success(data={"ok": True}, msg="已退出登录")