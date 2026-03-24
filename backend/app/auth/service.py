import base64
import hashlib
import hmac
import secrets
from typing import Optional
import psycopg
from psycopg.rows import dict_row
from backend.app.config import DATABASE_URL


ROLE_PERMISSIONS_MAP: dict[str, set[str]] = {
    "admin": {"chat:use", "user:manage"},
    "operator": {"chat:use"},
    "viewer": set(),
}
VALID_ROLES = tuple(ROLE_PERMISSIONS_MAP.keys())


def get_db_conn():
    return psycopg.connect(DATABASE_URL, autocommit=True, row_factory=dict_row)


def init_auth_schema():
    with get_db_conn() as conn, conn.cursor() as cur:
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS auth_roles (
                role_id BIGSERIAL PRIMARY KEY,
                role_code VARCHAR(32) NOT NULL UNIQUE,
                role_name VARCHAR(64) NOT NULL,
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS auth_role_permissions (
                role_id BIGINT NOT NULL REFERENCES auth_roles(role_id) ON DELETE CASCADE,
                permission_code VARCHAR(64) NOT NULL,
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                PRIMARY KEY (role_id, permission_code)
            )
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS auth_users (
                user_id BIGSERIAL PRIMARY KEY,
                username VARCHAR(64) NOT NULL UNIQUE,
                password_hash TEXT NOT NULL,
                is_active BOOLEAN NOT NULL DEFAULT TRUE,
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS auth_user_roles (
                user_id BIGINT NOT NULL REFERENCES auth_users(user_id) ON DELETE CASCADE,
                role_id BIGINT NOT NULL REFERENCES auth_roles(role_id) ON DELETE RESTRICT,
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                PRIMARY KEY (user_id, role_id)
            )
            """
        )
        for role_code in VALID_ROLES:
            role_name = role_code
            cur.execute(
                """
                INSERT INTO auth_roles (role_code, role_name)
                VALUES (%s, %s)
                ON CONFLICT (role_code) DO UPDATE SET role_name = EXCLUDED.role_name
                """,
                (role_code, role_name),
            )
        for role_code, permissions in ROLE_PERMISSIONS_MAP.items():
            role_id = get_role_id(cur, role_code)
            if not role_id:
                continue
            for permission in permissions:
                cur.execute(
                    """
                    INSERT INTO auth_role_permissions (role_id, permission_code)
                    VALUES (%s, %s)
                    ON CONFLICT (role_id, permission_code) DO NOTHING
                    """,
                    (role_id, permission),
                )
        migrate_legacy_app_users(cur)


def migrate_legacy_app_users(cur):
    cur.execute("SELECT to_regclass('public.app_users') AS legacy_table")
    legacy_table = cur.fetchone()
    if not legacy_table or not legacy_table.get("legacy_table"):
        return
    cur.execute("SELECT COUNT(1) AS count FROM auth_users")
    row = cur.fetchone()
    if row and int(row["count"]) > 0:
        return
    cur.execute("SELECT user_id, username, password_hash, role, is_active FROM app_users")
    legacy_users = cur.fetchall()
    for legacy_user in legacy_users:
        cur.execute(
            """
            INSERT INTO auth_users (username, password_hash, is_active)
            VALUES (%s, %s, %s)
            RETURNING user_id
            """,
            (
                legacy_user["username"],
                legacy_user["password_hash"],
                bool(legacy_user["is_active"]),
            ),
        )
        inserted = cur.fetchone()
        if not inserted:
            continue
        user_id = int(inserted["user_id"])
        role_code = str(legacy_user["role"])
        if role_code not in VALID_ROLES:
            role_code = "viewer"
        role_id = get_role_id(cur, role_code)
        if not role_id:
            continue
        cur.execute(
            """
            INSERT INTO auth_user_roles (user_id, role_id)
            VALUES (%s, %s)
            ON CONFLICT (user_id, role_id) DO NOTHING
            """,
            (user_id, role_id),
        )


def get_role_id(cur, role_code: str) -> Optional[int]:
    cur.execute("SELECT role_id FROM auth_roles WHERE role_code = %s", (role_code,))
    role = cur.fetchone()
    return int(role["role_id"]) if role else None


def get_user_by_username(username: str) -> dict | None:
    with get_db_conn() as conn, conn.cursor() as cur:
        cur.execute(
            """
            SELECT
                u.user_id,
                u.username,
                u.password_hash,
                u.is_active,
                r.role_code,
                rp.permission_code
            FROM auth_users u
            LEFT JOIN auth_user_roles ur ON ur.user_id = u.user_id
            LEFT JOIN auth_roles r ON r.role_id = ur.role_id
            LEFT JOIN auth_role_permissions rp ON rp.role_id = r.role_id
            WHERE u.username = %s
            """,
            (username,),
        )
        rows = cur.fetchall()
    return pack_user_rows(rows)


def get_user_by_id(user_id: int) -> dict | None:
    with get_db_conn() as conn, conn.cursor() as cur:
        cur.execute(
            """
            SELECT
                u.user_id,
                u.username,
                u.password_hash,
                u.is_active,
                r.role_code,
                rp.permission_code
            FROM auth_users u
            LEFT JOIN auth_user_roles ur ON ur.user_id = u.user_id
            LEFT JOIN auth_roles r ON r.role_id = ur.role_id
            LEFT JOIN auth_role_permissions rp ON rp.role_id = r.role_id
            WHERE u.user_id = %s
            """,
            (user_id,),
        )
        rows = cur.fetchall()
    return pack_user_rows(rows)


def pack_user_rows(rows: list[dict]) -> dict | None:
    if not rows:
        return None
    first = rows[0]
    role_set: set[str] = set()
    permission_set: set[str] = set()
    for row in rows:
        role_code = row.get("role_code")
        permission_code = row.get("permission_code")
        if role_code:
            role_set.add(str(role_code))
        if permission_code:
            permission_set.add(str(permission_code))
    roles = sorted(list(role_set))
    permissions = sorted(list(permission_set))
    primary_role = roles[0] if roles else "viewer"
    return {
        "user_id": int(first["user_id"]),
        "username": str(first["username"]),
        "password_hash": str(first["password_hash"]),
        "is_active": bool(first["is_active"]),
        "role": primary_role,
        "roles": roles,
        "permissions": permissions,
    }


def create_user(username: str, password: str, role_code: str) -> dict:
    if role_code not in VALID_ROLES:
        raise ValueError("invalid_role")
    password_hash = hash_password(password)
    with get_db_conn() as conn, conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO auth_users (username, password_hash)
            VALUES (%s, %s)
            RETURNING user_id, username, is_active
            """,
            (username, password_hash),
        )
        created = cur.fetchone()
        if not created:
            raise ValueError("create_user_failed")
        role_id = get_role_id(cur, role_code)
        if not role_id:
            raise ValueError("role_not_found")
        cur.execute(
            """
            INSERT INTO auth_user_roles (user_id, role_id)
            VALUES (%s, %s)
            ON CONFLICT (user_id, role_id) DO NOTHING
            """,
            (int(created["user_id"]), role_id),
        )
        return {
            "user_id": int(created["user_id"]),
            "username": str(created["username"]),
            "is_active": bool(created["is_active"]),
            "role": role_code,
        }


def count_users() -> int:
    with get_db_conn() as conn, conn.cursor() as cur:
        cur.execute("SELECT COUNT(1) AS count FROM auth_users")
        row = cur.fetchone()
        return int(row["count"]) if row else 0


def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    iterations = 150000
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), iterations)
    return f"pbkdf2_sha256${iterations}${salt}${base64.b64encode(digest).decode('utf-8')}"


def verify_password(password: str, password_hash: str) -> bool:
    try:
        algo, raw_iterations, salt, expected_hash = password_hash.split("$", 3)
        if algo != "pbkdf2_sha256":
            return False
        iterations = int(raw_iterations)
        digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), iterations)
        actual_hash = base64.b64encode(digest).decode("utf-8")
        return hmac.compare_digest(actual_hash, expected_hash)
    except Exception:
        return False
