from pydantic import BaseModel


class AuthUser(BaseModel):
    userId: int
    username: str
    role: str
    roles: list[str]
    permissions: list[str]


class LoginRequest(BaseModel):
    username: str
    password: str


class RegisterRequest(BaseModel):
    username: str
    password: str


class LoginResponse(BaseModel):
    accessToken: str
    tokenType: str
    expiresIn: int
    user: AuthUser


class CreateUserRequest(BaseModel):
    username: str
    password: str
    role: str


class BootstrapAdminRequest(BaseModel):
    username: str
    password: str
