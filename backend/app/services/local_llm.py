def run_local_llm(req):
    return {
        "model": req.model,
        "choices": [{"message": {"role": "assistant", "content": "Local model reply"}}]
    }

async def stream_local_llm(req, model_name: str):
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