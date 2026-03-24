from backend.app.auth.schemas import (
    AuthUser,
    BootstrapAdminRequest,
    CreateUserRequest,
    LoginRequest,
    LoginResponse,
    RegisterRequest,
)
from backend.app.auth.security import AUTH_ENABLED, get_current_user, login_with_password, require_permission
from backend.app.auth.service import VALID_ROLES, count_users, create_user, get_user_by_username, init_auth_schema

__all__ = [
    "AUTH_ENABLED",
    "AuthUser",
    "BootstrapAdminRequest",
    "CreateUserRequest",
    "LoginRequest",
    "LoginResponse",
    "RegisterRequest",
    "VALID_ROLES",
    "count_users",
    "create_user",
    "get_current_user",
    "get_user_by_username",
    "init_auth_schema",
    "login_with_password",
    "require_permission",
]
