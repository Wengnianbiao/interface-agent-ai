"""聊天路由层 - 仅负责请求接收、参数校验、响应包装"""

import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from backend.app.auth import AuthUser, require_permission
from backend.app.chat import get_session_messages, list_user_sessions
from backend.app.chat.service import execute_chat_stream, resolve_session_id

logger = logging.getLogger("interface-agent-api")

router = APIRouter(prefix="/api/chat", tags=["chat"])


class ChatRequest(BaseModel):
    prompt: str
    sessionId: str | None = None


@router.post("")
async def chat(
    request: ChatRequest,
    current_user: AuthUser = Depends(require_permission("chat:use")),
):
    """处理用户聊天请求 - 流式输出"""
    request_id = str(uuid.uuid4())[:8]
    session_id = resolve_session_id(request.sessionId)

    logger.info("request_id=%s 收到请求", request_id)
    logger.info("request_id=%s session_id=%s 输入预览=%s",
                request_id, session_id, request.prompt[:1000])

    try:
        stream = execute_chat_stream(request_id, request.prompt, session_id, current_user)
        response = StreamingResponse(stream, media_type="text/event-stream")
        response.headers["X-Session-Id"] = session_id
        response.headers["Cache-Control"] = "no-cache"
        response.headers["X-Accel-Buffering"] = "no"
        return response
    except Exception as e:
        logger.exception("request_id=%s 请求处理失败", request_id)
        raise HTTPException(status_code=500, detail=f"大模型有点累了，请稍后重试：{str(e)}")


@router.get("/sessions")
async def chat_sessions(current_user: AuthUser = Depends(require_permission("chat:use"))):
    sessions = list_user_sessions(current_user.userId, limit=50)
    return {"sessions": sessions}


@router.get("/sessions/{session_id}/messages")
async def chat_session_messages(
    session_id: str,
    current_user: AuthUser = Depends(require_permission("chat:use")),
):
    messages = get_session_messages(current_user.userId, session_id, limit=300)
    return {"sessionId": session_id, "messages": messages}
