from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse
from typing import List, Literal
from pydantic import BaseModel
from app.services.llm_router import generate_streaming_response
import redis
import json

router = APIRouter()

class Message(BaseModel):
    role: Literal["user", "assistant", "system"]
    content: str

class ChatRequest(BaseModel):
    model: str
    messages: List[Message]
    temperature: float = 0.7

@router.post("/chat/completions")
async def chat(req: ChatRequest):
    return await generate_response(req)

# @router.post("/chat/stream")
# async def chat_stream(req: ChatRequest):
#     async def event_generator():
#         async for chunk in generate_streaming_response(req):
#             yield f"data: {chunk}\n\n"
#     return StreamingResponse(event_generator(), media_type="text/event-stream")
@router.post("/chat/stream")
async def chat_stream(req: ChatRequest, request: Request):
    session_id = request.headers.get("X-Session-ID", "anonymous")

    # 1️⃣ Lấy lịch sử và thêm vào đầu vào
    history = get_chat_history(session_id)
    print("Reqest messages",req.messages)
    all_messages = history + req.messages
    req.messages = all_messages

    full_reply = ""

    async def event_generator():
        nonlocal full_reply
        async for chunk in generate_streaming_response(req):
            # 2️⃣ Thu thập nội dung stream để lưu sau
            try:
                data = chunk.strip()
                if data == "[DONE]":
                    break
                parsed = json.loads(data)
                delta = (
                    parsed.get("choices", [{}])[0]
                          .get("delta", {})
                          .get("content", "")
                )
                full_reply += delta
            except Exception:
                pass  # ignore parse errors
            yield f"data: {chunk}\n\n"

    # 3️⃣ Stream phản hồi về FE
    response = StreamingResponse(event_generator(), media_type="text/event-stream")

    # 4️⃣ Sau khi gửi xong, lưu messages + reply
    async def save_history():
        for msg in req.messages:
            append_chat_message(session_id, msg.role, msg.content)
        append_chat_message(session_id, "assistant", full_reply)

    # Dùng background task vì StreamingResponse đã trả về
    from starlette.background import BackgroundTask
    response.background = BackgroundTask(save_history)

    return response


r = redis.Redis(host="localhost", port=6379, db=0, decode_responses=True)

def get_chat_history(session_id: str, limit: int = 10) -> list:
    key = f"chat_history:{session_id}"
    raw = r.lrange(key, -limit, -1)
    return [Message(**json.loads(item)) for item in raw]

def append_chat_message(session_id: str, role: str, content: str, max_len: int = 10):
    key = f"chat_history:{session_id}"
    r.rpush(key, json.dumps({"role": role, "content": content}))
    r.ltrim(key, -max_len, -1)  # giữ lại max N dòng gần nhất