import psycopg
from psycopg.rows import dict_row
from backend.app.config import DATABASE_URL


def get_db_conn():
    return psycopg.connect(DATABASE_URL, row_factory=dict_row)


def init_chat_schema():
    with psycopg.connect(DATABASE_URL, autocommit=True, row_factory=dict_row) as conn, conn.cursor() as cur:
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS chat_sessions (
                session_pk BIGSERIAL PRIMARY KEY,
                user_id BIGINT NOT NULL REFERENCES auth_users(user_id) ON DELETE CASCADE,
                session_id VARCHAR(64) NOT NULL,
                qa_count INTEGER NOT NULL DEFAULT 0,
                message_count INTEGER NOT NULL DEFAULT 0,
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                last_message_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                UNIQUE (user_id, session_id)
            )
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS chat_messages (
                message_id BIGSERIAL PRIMARY KEY,
                session_pk BIGINT NOT NULL REFERENCES chat_sessions(session_pk) ON DELETE CASCADE,
                message_index INTEGER NOT NULL,
                role VARCHAR(16) NOT NULL,
                content TEXT NOT NULL,
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                UNIQUE (session_pk, message_index)
            )
            """
        )
        cur.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_chat_sessions_user_last_message
            ON chat_sessions (user_id, last_message_at DESC)
            """
        )
        cur.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_chat_messages_session_message_index
            ON chat_messages (session_pk, message_index)
            """
        )


def ensure_session(cur, user_id: int, session_id: str) -> dict:
    cur.execute(
        """
        INSERT INTO chat_sessions (user_id, session_id)
        VALUES (%s, %s)
        ON CONFLICT (user_id, session_id)
        DO UPDATE SET last_message_at = NOW()
        RETURNING session_pk, qa_count, message_count
        """,
        (user_id, session_id),
    )
    row = cur.fetchone()
    if row:
        return row
    cur.execute(
        """
        SELECT session_pk, qa_count, message_count
        FROM chat_sessions
        WHERE user_id = %s AND session_id = %s
        """,
        (user_id, session_id),
    )
    session_row = cur.fetchone()
    if not session_row:
        raise ValueError("session_not_found")
    return session_row


def get_session_history(user_id: int, session_id: str, max_messages: int) -> list[dict[str, str]]:
    with get_db_conn() as conn, conn.cursor() as cur:
        session_row = ensure_session(cur, user_id, session_id)
        session_pk = int(session_row["session_pk"])
        cur.execute(
            """
            SELECT role, content
            FROM chat_messages
            WHERE session_pk = %s
            ORDER BY message_index DESC
            LIMIT %s
            """,
            (session_pk, max_messages),
        )
        rows = cur.fetchall()
    ordered_rows = list(reversed(rows))
    return [{"role": str(item["role"]), "content": str(item["content"])} for item in ordered_rows]


def append_chat_pair(user_id: int, session_id: str, user_prompt: str, assistant_reply: str):
    user_cleaned = user_prompt.strip()
    assistant_cleaned = assistant_reply.strip()
    if not user_cleaned and not assistant_cleaned:
        return
    with get_db_conn() as conn, conn.cursor() as cur:
        session_row = ensure_session(cur, user_id, session_id)
        session_pk = int(session_row["session_pk"])
        current_message_count = int(session_row["message_count"])
        next_index = current_message_count + 1
        if user_cleaned:
            cur.execute(
                """
                INSERT INTO chat_messages (session_pk, message_index, role, content)
                VALUES (%s, %s, %s, %s)
                """,
                (session_pk, next_index, "user", user_cleaned),
            )
            next_index += 1
        if assistant_cleaned:
            cur.execute(
                """
                INSERT INTO chat_messages (session_pk, message_index, role, content)
                VALUES (%s, %s, %s, %s)
                """,
                (session_pk, next_index, "assistant", assistant_cleaned),
            )
            next_index += 1
        added_count = next_index - (current_message_count + 1)
        qa_increment = 1 if user_cleaned or assistant_cleaned else 0
        cur.execute(
            """
            UPDATE chat_sessions
            SET
                qa_count = qa_count + %s,
                message_count = message_count + %s,
                last_message_at = NOW()
            WHERE session_pk = %s
            """,
            (qa_increment, added_count, session_pk),
        )
        conn.commit()


def list_user_sessions(user_id: int, limit: int = 50) -> list[dict]:
    with get_db_conn() as conn, conn.cursor() as cur:
        cur.execute(
            """
            SELECT
                s.session_id,
                s.qa_count,
                s.message_count,
                s.last_message_at,
                (
                    SELECT m.content
                    FROM chat_messages m
                    WHERE m.session_pk = s.session_pk AND m.role = 'user'
                    ORDER BY m.message_index ASC
                    LIMIT 1
                ) AS title_content
            FROM chat_sessions s
            WHERE s.user_id = %s
            ORDER BY s.last_message_at DESC
            LIMIT %s
            """,
            (user_id, limit),
        )
        rows = cur.fetchall()
    results: list[dict] = []
    for row in rows:
        raw_title = str(row.get("title_content") or "").strip()
        title = (raw_title[:32] + "...") if len(raw_title) > 32 else (raw_title or "新会话")
        results.append(
            {
                "sessionId": str(row["session_id"]),
                "title": title,
                "qaCount": int(row["qa_count"]),
                "messageCount": int(row["message_count"]),
                "lastMessageAt": str(row["last_message_at"]),
            }
        )
    return results


def get_session_messages(user_id: int, session_id: str, limit: int = 200) -> list[dict[str, str]]:
    with get_db_conn() as conn, conn.cursor() as cur:
        cur.execute(
            """
            SELECT session_pk
            FROM chat_sessions
            WHERE user_id = %s AND session_id = %s
            """,
            (user_id, session_id),
        )
        session_row = cur.fetchone()
        if not session_row:
            return []
        session_pk = int(session_row["session_pk"])
        cur.execute(
            """
            SELECT role, content
            FROM chat_messages
            WHERE session_pk = %s
            ORDER BY message_index ASC
            LIMIT %s
            """,
            (session_pk, limit),
        )
        rows = cur.fetchall()
    return [{"role": str(item["role"]), "content": str(item["content"])} for item in rows]
