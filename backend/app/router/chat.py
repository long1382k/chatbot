# app/routes/chat.py

from turtle import title
from typing_extensions import Optional
from fastapi import APIRouter, Request, Query, Depends, HTTPException
from fastapi.responses import StreamingResponse, JSONResponse
from starlette.background import BackgroundTask
from typing import List, Literal
from pydantic import BaseModel
import redis
import json

from app.services.llm_router import generate_streaming_response
from app.db import SessionLocal, Conversation, Message as DBMessage

router = APIRouter()
r = redis.Redis(host="localhost", port=6379, db=0, decode_responses=True)

# ----- Pydantic schemas -----
class Message(BaseModel):
    role: Literal["user", "assistant", "system"]
    content: str

class ChatRequest(BaseModel):
    model: str
    messages: List[Message]
    temperature: float = 0.7

# ----- Redis helpers -----
def get_redis_history(session_id: str, limit: int = 5) -> List[Message]:
    raw = r.lrange(f"chat_history:{session_id}", -limit, -1)
    return [Message.parse_raw(item) for item in raw]

def append_redis(session_id: str, msg: Message, trim: bool = True, max_len: int = 5):
    key = f"chat_history:{session_id}"
    r.rpush(key, msg.json())
    if trim:
        r.ltrim(key, -max_len, -1)

# ----- SQLite (SQLAlchemy) helpers -----
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def get_or_create_conversation(db, session_id: str, user_id: str, title: Optional[str] = None) -> Conversation:
    conv = db.query(Conversation).filter_by(session_id=session_id).first()
    if not conv:
        conv = Conversation(session_id=session_id, user_id=user_id,title=title)
        db.add(conv)
        db.commit()
        db.refresh(conv)
    elif conv.user_id != user_id:
        # Nếu session_id đã tồn tại nhưng user khác, cập nhật cho thống nhất
        conv.user_id = user_id
        db.commit()
    return conv

def save_message_db(db, conv_id: int, msg: Message):
    m = DBMessage(conversation_id=conv_id, role=msg.role, content=msg.content)
    db.add(m)
    db.commit()

# ----- Streaming endpoint -----
@router.post("/chat/stream")
async def chat_stream(
    req: ChatRequest,
    request: Request,
    db = Depends(get_db),
):
    user_id = request.headers.get("X-User-ID", "anonymous")
    session_id = request.headers.get("X-Session-ID")
    if not session_id:
        raise HTTPException(status_code=400, detail="X-Session-ID header missing")
    if not req.messages:
        raise HTTPException(status_code=400, detail="No message provided")
    user_msg = req.messages[-1]

    # 1️⃣ Lấy hoặc tạo Conversation trong SQLite
    title_length = min(5, len(user_msg.content.split()))
    title = " ".join(user_msg.content.split()[:title_length])
    conv = get_or_create_conversation(db, session_id, user_id, title=title)

    # 2️⃣ Lấy context ngắn hạn từ Redis, nếu có thì ghép vào đầu messages
    history = get_redis_history(session_id)
    

    # 4️⃣ Nếu không có context cũ, thêm system prompt vào đầu
    if not history:
        system_prompt = Message(
            role="system",
            content="You are a helpful assistant, always answer in Vietnamese."
        )
        full_messages = [system_prompt, user_msg]
    else:
        full_messages = history + [user_msg]
    

    full_reply = ""

    # 3️⃣ Generator cho streaming SSE
    async def event_generator():
        nonlocal full_reply
        streaming_req = ChatRequest(
            model=req.model,
            temperature=req.temperature,
            messages=full_messages
        )
        async for chunk in generate_streaming_response(streaming_req):
            if chunk.strip() == "[DONE]":
                break
            try:
                parsed = json.loads(chunk)
                delta = parsed["choices"][0]["delta"].get("content", "")
                full_reply += delta
            except:
                pass
            yield f"data: {chunk}\n\n"

    response = StreamingResponse(event_generator(), media_type="text/event-stream")

    # 4️⃣ Sau khi stream xong, lưu cả vào Redis và SQLite
    def save_history():
        append_redis(session_id, user_msg, trim=True)
        save_message_db(db, conv.id, user_msg)

        assistant_msg = Message(role="assistant", content=full_reply)
        append_redis(session_id, assistant_msg, trim=True)
        save_message_db(db, conv.id, assistant_msg)

    response.background = BackgroundTask(save_history)
    return response

# ----- List tất cả sessions của user -----
@router.get("/chat/conversations")
def list_conversations(
    user_id: str = Query(..., description="ID của user"),
    db = Depends(get_db),
):
    convs = (
        db.query(Conversation)
          .filter_by(user_id=user_id)
          .order_by(Conversation.created_at.desc())
          .all()
    )
    return [
        {
            "session_id": c.session_id,
            "title": c.title,
            "created_at": c.created_at,
            "message_count": len(c.messages),
        }
        for c in convs
    ]

# ----- Lấy đầy đủ lịch sử của một session -----
@router.get("/chat/conversations/{session_id}/history")
def get_conversation_history(
    session_id: str,
    user_id: str = Query(..., description="ID của user"),
    db = Depends(get_db),
):
    conv = db.query(Conversation).filter_by(session_id=session_id).first()
    if not conv or conv.user_id != user_id:
        raise HTTPException(status_code=404, detail="Conversation not found or forbidden")

    return [
        {"role": m.role, "content": m.content, "timestamp": m.timestamp}
        for m in conv.messages
    ]
