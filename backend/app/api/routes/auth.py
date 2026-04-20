"""认证相关路由"""

from fastapi import APIRouter, Depends, HTTPException

from backend.app.auth import (
    AUTH_ENABLED,
    AuthUser,
    BootstrapAdminRequest,
    CreateUserRequest,
    LoginRequest,
    RegisterRequest,
    VALID_ROLES,
    count_users,
    create_user,
    get_user_by_username,
    get_current_user,
    login_with_password,
    require_permission,
)

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/bootstrap-admin")
async def bootstrap_admin(request: BootstrapAdminRequest):
    if count_users() > 0:
        raise HTTPException(status_code=400, detail="系统已初始化用户，不能重复引导")
    if request.username.strip() == "" or request.password.strip() == "":
        raise HTTPException(status_code=400, detail="用户名和密码不能为空")
    created = create_user(request.username.strip(), request.password, "admin")
    return {
        "success": True,
        "userId": created["user_id"],
        "username": created["username"],
        "role": created["role"],
    }


@router.post("/login")
async def login(request: LoginRequest):
    return login_with_password(request.username.strip(), request.password)


@router.post("/register")
async def register(request: RegisterRequest):
    username = request.username.strip()
    password = request.password.strip()
    if username == "" or password == "":
        raise HTTPException(status_code=400, detail="用户名和密码不能为空")
    if len(password) < 6:
        raise HTTPException(status_code=400, detail="密码长度至少6位")
    existing = get_user_by_username(username)
    if existing:
        raise HTTPException(status_code=409, detail="用户名已存在")
    create_user(username, request.password, "operator")
    return login_with_password(username, request.password)


@router.get("/me")
async def me(current_user: AuthUser = Depends(get_current_user)):
    return current_user


@router.post("/users")
async def create_user_api(
    request: CreateUserRequest,
    _current_user: AuthUser = Depends(require_permission("user:manage")),
):
    role = request.role.strip()
    if role not in set(VALID_ROLES):
        raise HTTPException(status_code=400, detail="角色不合法")
    username = request.username.strip()
    if username == "" or request.password.strip() == "":
        raise HTTPException(status_code=400, detail="用户名和密码不能为空")
    existing = get_user_by_username(username)
    if existing:
        raise HTTPException(status_code=409, detail="用户名已存在")
    created = create_user(username, request.password, role)
    return {
        "success": True,
        "userId": created["user_id"],
        "username": created["username"],
        "role": created["role"],
    }
