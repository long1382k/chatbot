from app.utils.model_loader import find_model
from app.services.local_llm import run_local_llm, stream_local_llm
from app.services.remote_llm import run_remote_llm, stream_remote_llm

async def generate_response(req):
    # Tìm cấu hình model dựa trên model_name từ request
    model_cfg = find_model(req.model)

    if not model_cfg:
        return {
            "error": {
                "message": f"Model '{req.model}' not found in models.yaml"
            }
        }

    model_type = model_cfg["type"]
    model_name = model_cfg["model_name"]

    # Phân luồng xử lý theo loại model
    if model_type == "local":
        return run_local_llm(req, model_name)

    elif model_type == "remote":
        return await run_remote_llm(req)

    else:
        return {
            "error": {
                "message": f"Unknown model type: {model_type}"
            }
        }

# 🔥 Hàm mới cho stream
async def generate_streaming_response(req):
    model_cfg = find_model(req.model)
    if not model_cfg:
        yield "[DONE]"
        return

    if model_cfg["type"] == "local":
        
        async for chunk in stream_local_llm(req, model_cfg["model_name"]):
            yield chunk
    else:
        async for chunk in stream_remote_llm(req, model_cfg["model_name"]):
            yield chunk