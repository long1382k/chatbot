import httpx
import os
from app.config import API_KEY

async def run_remote_llm(req):
    if API_KEY is None:
        return {
            "error": {
                "message": "API Key not found"
            }
        }
    
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        # "HTTP-Referer": "https://yourdomain.com",  # Optional
        # "X-Title": "Your App",                     # Optional
    }

    try:
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers=headers,
                json={
                    "model": req.model,
                    "messages": [m.dict() for m in req.messages],
                    "temperature": req.temperature
                }
            )

        if response.status_code == 200:
            return response.json()
        else:
            return {
                "error": {
                    "code": response.status_code,
                    "message": response.text
                }
            }
    except httpx.RequestError as e:
        return {
            "error": {
                "code": "network_error",
                "message": str(e)
            }
        }

async def stream_remote_llm(req, model_name: str):
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Accept": "text/event-stream",
    }

    async with httpx.AsyncClient(timeout=None) as client:
        async with client.stream(
            "POST",
            "https://openrouter.ai/api/v1/chat/completions",
            headers=headers,
            json={
                "model": model_name,
                "messages": [m.dict() for m in req.messages],
                "temperature": req.temperature,
                "stream": True
            },
        ) as response:
            async for line in response.aiter_lines():
                if line.startswith("data: "):
                    yield line[6:]
                    
def serialize_message(m):
    return m.dict() if hasattr(m, "dict") else m
