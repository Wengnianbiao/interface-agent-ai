import base64
import hashlib
import hmac
import json
import time
from typing import Callable
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from backend.app.config import ACCESS_TOKEN_EXPIRE_SECONDS, AUTH_ENABLED, AUTH_SECRET_KEY
from backend.app.auth.schemas import AuthUser, LoginResponse
from backend.app.auth.service import get_user_by_id, get_user_by_username, verify_password


auth_scheme = HTTPBearer(auto_error=False)


def b64url_encode(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).decode("utf-8").rstrip("=")


def b64url_decode(raw: str) -> bytes:
    pad = "=" * ((4 - len(raw) % 4) % 4)
    return base64.urlsafe_b64decode(raw + pad)


def create_access_token(user: dict) -> str:
    header = {"alg": "HS256", "typ": "JWT"}
    now = int(time.time())
    payload = {
        "sub": str(user["user_id"]),
        "username": user["username"],
        "roles": user.get("roles", []),
        "iat": now,
        "exp": now + ACCESS_TOKEN_EXPIRE_SECONDS,
    }
    header_segment = b64url_encode(json.dumps(header, separators=(",", ":"), ensure_ascii=False).encode("utf-8"))
    payload_segment = b64url_encode(json.dumps(payload, separators=(",", ":"), ensure_ascii=False).encode("utf-8"))
    sign_input = f"{header_segment}.{payload_segment}".encode("utf-8")
    signature = hmac.new(AUTH_SECRET_KEY.encode("utf-8"), sign_input, hashlib.sha256).digest()
    signature_segment = b64url_encode(signature)
    return f"{header_segment}.{payload_segment}.{signature_segment}"


def decode_access_token(token: str) -> dict:
    try:
        segments = token.split(".")
        if len(segments) != 3:
            raise ValueError("invalid_token")
        header_segment, payload_segment, signature_segment = segments
        sign_input = f"{header_segment}.{payload_segment}".encode("utf-8")
        expected_signature = hmac.new(AUTH_SECRET_KEY.encode("utf-8"), sign_input, hashlib.sha256).digest()
        actual_signature = b64url_decode(signature_segment)
        if not hmac.compare_digest(expected_signature, actual_signature):
            raise ValueError("invalid_signature")
        payload = json.loads(b64url_decode(payload_segment).decode("utf-8"))
        if int(payload.get("exp", 0)) < int(time.time()):
            raise ValueError("token_expired")
        return payload
    except Exception as exc:
        raise HTTPException(status_code=401, detail=f"无效令牌: {str(exc)}")


def build_auth_user(user_row: dict) -> AuthUser:
    roles = list(user_row.get("roles", []))
    permissions = sorted(list(set(user_row.get("permissions", []))))
    primary_role = str(user_row.get("role") or (roles[0] if roles else "viewer"))
    return AuthUser(
        userId=int(user_row["user_id"]),
        username=str(user_row["username"]),
        role=primary_role,
        roles=sorted(roles),
        permissions=permissions,
    )


def get_current_user(credentials: HTTPAuthorizationCredentials | None = Depends(auth_scheme)) -> AuthUser:
    if not AUTH_ENABLED:
        return AuthUser(
            userId=0,
            username="dev",
            role="admin",
            roles=["admin"],
            permissions=["chat:use", "user:manage"],
        )
    if not credentials:
        raise HTTPException(status_code=401, detail="缺少认证信息")
    if credentials.scheme.lower() != "bearer":
        raise HTTPException(status_code=401, detail="认证类型不支持")
    payload = decode_access_token(credentials.credentials)
    user_id = int(payload.get("sub"))
    user_row = get_user_by_id(user_id)
    if not user_row or not bool(user_row.get("is_active")):
        raise HTTPException(status_code=401, detail="用户不存在或已禁用")
    return build_auth_user(user_row)


def require_permission(permission: str) -> Callable:
    def dependency(current_user: AuthUser = Depends(get_current_user)) -> AuthUser:
        if permission not in set(current_user.permissions):
            raise HTTPException(status_code=403, detail=f"缺少权限: {permission}")
        return current_user

    return dependency


def login_with_password(username: str, password: str) -> LoginResponse:
    user_row = get_user_by_username(username)
    if not user_row or not bool(user_row.get("is_active")):
        raise HTTPException(status_code=401, detail="用户名或密码错误")
    if not verify_password(password, str(user_row.get("password_hash", ""))):
        raise HTTPException(status_code=401, detail="用户名或密码错误")
    token = create_access_token(user_row)
    auth_user = build_auth_user(user_row)
    return LoginResponse(
        accessToken=token,
        tokenType="Bearer",
        expiresIn=ACCESS_TOKEN_EXPIRE_SECONDS,
        user=auth_user,
    )
