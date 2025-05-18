from fastapi import APIRouter, Query
from typing import Optional
from app.utils.model_loader import load_models_by_type, get_model_list

router = APIRouter()

@router.get("/models")
def get_models(type: Optional[str] = Query(None, regex="^(remote|local)$")):
    """
    Trả về danh sách models (dùng cho dropdown frontend).
    Nếu có tham số ?type=remote|local thì lọc theo loại.
    """
    if type:
        models = load_models_by_type(type)
        return {
            "type": type,
            "models": [
                {"model_name": m["model_name"], "description": m["description"]}
                for m in models
            ]
        }
    else:
        # Trả toàn bộ model gộp
        all_models = get_model_list()
        return {
            "models": [
                {"type": t, "model_name": m["model_name"], "description": m["description"]}
                for t, models in all_models.items()
                for m in models
            ]
        }
