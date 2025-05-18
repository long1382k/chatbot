from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from app.utils.auth import check_api_key
from app.utils.rate_limit import rate_limiter
from app.router import chat, models

app = FastAPI()

# ✅ Cấu hình CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Cho phép tất cả origin — có thể thay bằng ["http://localhost:3000"] nếu cần cụ thể
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ✅ Gắn router
app.include_router(chat.router, prefix="/v1", dependencies=[Depends(check_api_key), Depends(rate_limiter)])
app.include_router(models.router, prefix="/v1")

@app.get("/")
def root():
    return {"message": "OpenAI-Compatible Chatbot API running"}
